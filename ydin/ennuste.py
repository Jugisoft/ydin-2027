"""Otteluennuste (19.11.2026): vastustajakorjatut hyökkäys- ja puolustusluvut ristiin.

python -m ydin.ennuste  ->  data/out/ennuste.json  (sivu: ennuste.html)

Ajatus: juoksut ≈ 3. pesältä lähteneet kärkiyritykset (3-til.) × kotiutus% (korrelaatio 0,99 otteluittain).
Joukkueelle lasketaan jokaisesta tilanteesta hyökkäysluku (oma) ja puolustusluku (vastustajien luku sitä vastaan):
  t3   3-tilanteet / ottelu            kot  kotiutus% 3. pesältä
  kl0  KL% nollatilanteessa            kl1  KL% 1. pesältä         kl2  KL% 2. pesältä
Ottelun odotusarvo = joukkueen hyökkäys ristiin vastustajan puolustuksen kanssa:
  määrät: hyökkäys × puolustus / sarjan keskiarvo,  prosentit: kerroinsuhde (odds ratio, log5).
Luvut kutistetaan sarjan keskiarvoon (K ottelua), vanhat ottelut painuvat (LAMBDA / ottelu) ja kauden
vaihtuessa edellinen kausi kantaa CARRY-painolla. Nousijan lähtötaso on sarjan keskiarvoa heikompi (NOUSIJA).
Voittotodennäköisyys = logistinen regressio lukujen eroista (logaritmit / logit) + kotietu (vakio).

Kaikki ennusteet lasketaan vain ottelua edeltävästä datasta. Parametrit viritettiin kausilla 2011–2019
ja niitä testataan kausilla 2020– (jälkitesti, tulokset tiedostossa ja sivulla).

Data: stats-tool/teams ottelittain kaudesta 2010 (data/ottelupohja/<kausi>.json.gz). Päättyneet kaudet haetaan
kerran; kuluva kausi joka ajolla (3 pyyntöä + otteluluettelo). Joukkueen tunniste vaihtuu kausittain, joten
joukkueet yhdistetään seuratunnisteella (sport_club_id).
"""
import collections, gzip, json, math, os

from . import kaudet

JUURI = os.path.join(os.path.dirname(__file__), "..")
POHJA = os.path.join(JUURI, "data", "ottelupohja")
OUT = os.path.join(JUURI, "data", "out")
SEURANTA = os.path.join(JUURI, "data", "seuranta", "seuranta.json")

CARRY, K, LAMBDA, NOUSIJA = 0.6, 4, 0.97, 0.2
VIRITYS_LOPPU = 2019          # parametrit viritetty kausiin 2011–2019; 2020– = testi
TIL = {  # avain: (osoittaja, nimittäjä tai None = per ottelu, nimi)
    "t3": ("pe_tries_b3", None, "3-tilanteet / O"),
    "kot": ("pe_total_b3", "pe_tries_b3", "Kotiutus%"),
    "kl0": ("pe_total_b0", "pe_tries_b0", "KL%0"),
    "kl1": ("pe_total_b1", "pe_tries_b1", "KL%1"),
    "kl2": ("pe_total_b2", "pe_tries_b2", "KL%2"),
    "jk": ("runs", None, "Juoksut / O"),
}
MALLI = ["t3", "kot", "kl0", "kl1", "kl2"]      # voittomallin piirteet
VERTAILU = ["jk"]                                # vertailumalli: pelkät juoksut
KENTAT = ["match_id", "team_id", "opponent_team_id", "is_home", "won", "series_phase_id", "runs", "runs_opponent",
          "rab3", "rab3_opponent", "homeruns", "homeruns_opponent", "pe_tries_total"] + \
         [f"pe_{a}_b{n}{s}" for a in ("tries", "total") for n in range(4) for s in ("", "_opponent")]


# ---------- data ----------
def _polku(kausi):
    return os.path.join(POHJA, f"{kausi}.json.gz")

def hae_kausi(kausi):
    from . import haku
    ss = kaudet.MSU_HISTORIA[kausi]
    ott, maps = haku.ottelut(ss)
    tiimit = {}
    for t in maps.get("team", []):
        v = t["value"]; tiimit[t["id"]] = [v.get("sport_club_id") or t["id"], v.get("shorthand"), v.get("name")]
    rivit, saa = [], {}
    for ph in (1, 2, 3):
        rivit += haku.joukkueet_otteluittain(ss, ph).get("data", [])
        for x in haku.pelaajat_otteluittain(ss, ph).get("data", []):   # sää kirjataan ottelun pelaajariveille
            saa[str(x["match_id"])] = [x.get("temperature"), x.get("windy"), x.get("rainy"), x.get("spectators")]
    d = {"kausi": kausi, "tiimit": {str(k): v for k, v in tiimit.items()},
         "ottelut": [{"id": o["id"], "pvm": o["date"], "koti": o["home"], "vieras": o["away"], "vaihe": o["series"]["phase"],
                      "tulos": (o.get("result") or {}).get("result_string"), "stadion": (o.get("stadium") or {}).get("name"),
                      "peruttu": bool(o.get("canceled"))} for o in ott],
         "rivit": [[r.get(k) or 0 for k in KENTAT] for r in rivit], "kentat": KENTAT,
         "saa": saa, "saa_kentat": ["lampo", "tuuli", "sade", "yleiso"]}
    # tuuli (Ilmatieteen laitos) kotikentän otteluille; aiemmin haetut säilytetään
    from . import kentat
    vanha = lue_kausi(kausi).get("tuuli", {}) if os.path.exists(_polku(kausi)) else {}
    tu = {}
    for o in d["ottelut"]:
        if o["peruttu"] or not o["tulos"]:
            continue
        k = kentat.kentta((tiimit.get(o["koti"]) or [None, None])[1], o["stadion"])
        if not k:
            continue
        w = vanha.get(str(o["id"]))
        if not w:
            try:
                w = kentat.tuuli(k, o["pvm"]); w = [k] + w if w else None
            except Exception:
                w = None
        if w:
            tu[str(o["id"])] = w
    d["tuuli"] = tu; d["tuuli_kentat"] = ["kentta", "tulosuunta", "nopeus", "fmisid"]
    os.makedirs(POHJA, exist_ok=True)
    with gzip.open(_polku(kausi), "wt", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    return d

def lue_kausi(kausi):
    with gzip.open(_polku(kausi), "rt", encoding="utf-8") as f:
        return json.load(f)

def paivita_pohja(kuluva=None):
    """Päättyneet kaudet vain jos puuttuvat, kuluva aina."""
    kuluva = kuluva or max(kaudet.MSU_HISTORIA)
    for k in sorted(kaudet.MSU_HISTORIA):
        if k == kuluva or not os.path.exists(_polku(k)):
            hae_kausi(k)

def lataa(kaudet_lista=None):
    """Ottelut aikajärjestyksessä: lista (ottelu, rivi_koti, rivi_vieras); rivit dict, team_id = seura."""
    kaudet_lista = kaudet_lista or sorted(k for k in kaudet.MSU_HISTORIA if os.path.exists(_polku(k)))
    ottelut, seurat = [], {}
    for k in kaudet_lista:
        d = lue_kausi(k); T = {int(a): b for a, b in d["tiimit"].items()}
        for tid, (seura, lyh, nimi) in T.items():
            seurat[seura] = {"lyh": lyh, "nimi": nimi}
        om = {o["id"]: o for o in d["ottelut"]}
        for mid, w in (d.get("saa") or {}).items():
            if int(mid) in om:
                om[int(mid)]["saa"] = w
        for mid, w in (d.get("tuuli") or {}).items():
            if int(mid) in om:
                from .kentat import myota
                om[int(mid)]["myota"] = myota(w[1], w[2], w[0])
        per = collections.defaultdict(list)
        for r in d["rivit"]:
            r = dict(zip(d["kentat"], r))
            if not r["pe_tries_total"]:
                continue
            r["team_id"] = T.get(r["team_id"], [r["team_id"]])[0]; r["opponent_team_id"] = T.get(r["opponent_team_id"], [r["opponent_team_id"]])[0]
            per[r["match_id"]].append(r)
        for mid, rr in per.items():
            o = om.get(mid)
            if len(rr) != 2 or not o:
                continue
            rr.sort(key=lambda r: -r["is_home"])
            ottelut.append(({**o, "kausi": k}, rr[0], rr[1]))
    ottelut.sort(key=lambda x: (x[0]["pvm"], x[0]["id"]))
    return ottelut, seurat


# ---------- arviot ----------
class Arviot:
    def __init__(self, carry=CARRY, k=K, lam=LAMBDA, nousija=NOUSIJA):
        self.carry, self.k, self.lam, self.nousija = carry, k, lam, nousija
        self.S = collections.defaultdict(lambda: collections.defaultdict(float))
        self.lg, self.den = {}, {}                  # sarjan keskiarvo ja nimittäjä / ottelu (edellinen kausi)
        self.kerty = collections.defaultdict(float)  # kuluvan kauden sarjasummat
        self.kausi, self.edelliset, self.nyt = None, set(), set()

    def uusi_kausi(self, kausi):
        if self.kerty:
            n = self.kerty[("jk", "d")] or 1
            self.lg = {s: self.kerty[(s, "n")] / self.kerty[(s, "d")] for s in TIL if self.kerty[(s, "d")]}
            self.den = {s: self.kerty[(s, "d")] / n for s in TIL}
        self.kerty = collections.defaultdict(float)
        gap = (kausi - self.kausi) if self.kausi else 1
        for t in self.S:
            for key in self.S[t]:
                self.S[t][key] *= self.carry ** max(1, gap)
        self.edelliset, self.nyt, self.kausi = self.nyt, set(), kausi

    def arvo(self, t, s, side):
        lg = self.lg.get(s)
        if lg is None:
            return None
        S = self.S.get(t); n = S[(s, side, "n")] if S else 0.0; d = S[(s, side, "d")] if S else 0.0
        prior = lg
        if self.nousija and t not in self.edelliset:   # ei pelannut edellisellä kaudella = nousija / uusi
            prior = lg * (1 - self.nousija) if side == "o" else lg * (1 + self.nousija)
        kk = self.k * (self.den.get(s, 1.0) if TIL[s][1] else 1.0)
        return (n + prior * kk) / (d + kk)

    def lisaa(self, r, vaihe=1):
        t = r["team_id"]; S = self.S[t]
        if vaihe == 1:  # nousija = ei pelannut edellisen kauden runkosarjaa (karsinnat eivät riitä)
            self.nyt.add(t)
        for s, (num, den, _) in TIL.items():
            for side, suf in (("o", ""), ("d", "_opponent")):
                S[(s, side, "n")] = S[(s, side, "n")] * self.lam + r[num + suf]
                S[(s, side, "d")] = S[(s, side, "d")] * self.lam + (r[den + suf] if den else 1.0)
            self.kerty[(s, "n")] += r[num]; self.kerty[(s, "d")] += r[den] if den else 1.0


def _logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6); return math.log(p / (1 - p))

def risti(s, o, d, lg):
    if TIL[s][1]:
        x = math.exp(_logit(o) + _logit(d) - _logit(lg)); return x / (1 + x)
    return o * d / lg

def odotus(A, a, b):
    """Joukkueen a odotusarvot vastustajaa b vastaan."""
    return {s: risti(s, A.arvo(a, s, "o"), A.arvo(b, s, "d"), A.lg[s]) for s in TIL}

def erot(ea, eb):
    """Piirteet: log-ero määrille, logit-ero prosenteille."""
    return {s: (math.log(ea[s] / eb[s]) if not TIL[s][1] else _logit(ea[s]) - _logit(eb[s])) for s in TIL}


def kulje(ottelut, **par):
    """Walk-forward: jokaiselle ottelulle ennustepiirteet ennen ottelua. Palauttaa (rivit, Arviot lopussa)."""
    A = Arviot(**par); out = []
    for o, h, v in ottelut:
        if o["kausi"] != A.kausi:
            A.uusi_kausi(o["kausi"])
        if A.lg:
            eh, ev = odotus(A, h["team_id"], v["team_id"]), odotus(A, v["team_id"], h["team_id"])
            out.append({"id": o["id"], "kausi": o["kausi"], "vaihe": o["vaihe"], "koti": h["team_id"], "vieras": v["team_id"],
                        "won": h["won"], "runs_h": h["runs"], "runs_v": v["runs"], "eh": eh, "ev": ev, "x": erot(eh, ev),
                        "saa": o.get("saa"), "myota": o.get("myota"), "kk": int(o["pvm"][5:7])})
        A.lisaa(h, o["vaihe"]); A.lisaa(v, o["vaihe"])
    return out, A


# ---------- logistinen regressio (Newton, ei riippuvuuksia) ----------
def logreg(X, y, iters=30, l2=1e-4):
    m = len(X[0]) + 1; w = [0.0] * m
    for _ in range(iters):
        g = [0.0] * m; H = [[0.0] * m for _ in range(m)]
        for xi, yi in zip(X, y):
            z = [1.0] + xi; p = 1 / (1 + math.exp(-max(-30, min(30, sum(a * b for a, b in zip(w, z))))))
            for i in range(m):
                g[i] += (p - yi) * z[i]
                for j in range(m):
                    H[i][j] += p * (1 - p) * z[i] * z[j]
        for i in range(1, m):
            g[i] += l2 * w[i]; H[i][i] += l2
        w = [a - b for a, b in zip(w, _ratkaise(H, g))]
    return w

def _ratkaise(A, b):
    n = len(b); M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]; M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] if M[i][i] else 0.0 for i in range(n)]

def ennusta(w, xi):
    z = w[0] + sum(a * b for a, b in zip(w[1:], xi)); return 1 / (1 + math.exp(-z))


# ---------- arviointi ----------
def _mitat(p, y):
    n = len(y)
    ll = -sum(yi * math.log(max(pi, 1e-9)) + (1 - yi) * math.log(max(1 - pi, 1e-9)) for pi, yi in zip(p, y)) / n
    br = sum((pi - yi) ** 2 for pi, yi in zip(p, y)) / n
    acc = sum((pi > .5) == (yi == 1) for pi, yi in zip(p, y)) / n
    return {"logloss": round(ll, 4), "brier": round(br, 4), "osuma": round(acc, 4), "n": n}

def jalkitesti(rivit):
    tr = [r for r in rivit if r["kausi"] <= VIRITYS_LOPPU]; te = [r for r in rivit if r["kausi"] > VIRITYS_LOPPU]
    y_tr = [r["won"] for r in tr]; y_te = [r["won"] for r in te]
    tulos = {"opetus": f"{min(r['kausi'] for r in tr)}–{VIRITYS_LOPPU}", "testi": f"{VIRITYS_LOPPU + 1}–{max(r['kausi'] for r in te)}"}
    koti = sum(y_tr) / len(y_tr)
    tulos["koti"] = _mitat([koti] * len(te), y_te)
    for nimi, pi in (("juoksut", VERTAILU), ("malli", MALLI)):
        w = logreg([[r["x"][s] for s in pi] for r in tr], y_tr)
        p = [ennusta(w, [r["x"][s] for s in pi]) for r in te]
        tulos[nimi] = _mitat(p, y_te)
        if nimi == "malli":
            pm = p
    # kalibrointi ja kausittain
    rajat = [0, .2, .35, .5, .65, .8, 1.0001]; kal = []
    for a, b in zip(rajat, rajat[1:]):
        g = [(pi, yi) for pi, yi in zip(pm, y_te) if a <= pi < b]
        if g:
            kal.append({"vali": f"{round(a*100)}–{min(100, round(b*100))} %", "n": len(g), "ennuste": round(sum(x for x, _ in g) / len(g), 3),
                        "toteutui": round(sum(y for _, y in g) / len(g), 3)})
    tulos["kalibrointi"] = kal
    kk = collections.defaultdict(list)
    for r, pi in zip(te, pm):
        kk[r["kausi"]].append((pi > .5) == (r["won"] == 1))
    tulos["kausittain"] = {k: round(sum(v) / len(v), 3) for k, v in sorted(kk.items())}
    # juoksuennusteen virhe (joukkue per ottelu): 3-til. × kotiutus% skaalattuna vs. pelkkä keskiarvo
    sk = sum(r["runs_h"] + r["runs_v"] for r in tr) / sum(r["eh"]["t3"] * r["eh"]["kot"] + r["ev"]["t3"] * r["ev"]["kot"] for r in tr)
    ka = sum(r["runs_h"] + r["runs_v"] for r in tr) / (2 * len(tr))
    e1 = [(sk * r[e]["t3"] * r[e]["kot"] - r[j]) ** 2 for r in te for e, j in (("eh", "runs_h"), ("ev", "runs_v"))]
    e0 = [(ka - r[j]) ** 2 for r in te for j in ("runs_h", "runs_v")]
    tulos["juoksut_rmse"] = {"malli": round(math.sqrt(sum(e1) / len(e1)), 2), "keskiarvo": round(math.sqrt(sum(e0) / len(e0)), 2)}
    return tulos


def luokat(ottelut, seurat, kausi):
    """Vastustajan luokka: kauden runkosarjassa 3-tilanteet, kotiutus% ja KL%0–1 vastustajan luokan mukaan.
    Luokka = vastustajan runkosarjasijoitus juoksueron mukaan: kärki (1–4), keski (5–8), häntä (9–)."""
    rs = [(o, h, v) for o, h, v in ottelut if o["kausi"] == kausi and o["vaihe"] == 1]
    if not rs:
        return None
    je = collections.Counter()
    for _, h, v in rs:
        je[h["team_id"]] += h["runs"] - v["runs"]; je[v["team_id"]] += v["runs"] - h["runs"]
    jarj = [t for t, _ in je.most_common()]; n = len(jarj)
    luokka = {t: ("karki" if i < 4 else "keski" if i < 8 else "hanta") for i, t in enumerate(jarj)}
    S = collections.defaultdict(lambda: collections.defaultdict(float))
    for _, h, v in rs:
        for r in (h, v):
            L = luokka[r["opponent_team_id"]]
            for k in (L, "kaikki"):
                s = S[(r["team_id"], k)]
                s["O"] += 1; s["t3"] += r["pe_tries_b3"]; s["t3v"] += r["pe_tries_b3_opponent"]
                s["kn"] += r["pe_total_b3"]; s["kd"] += r["pe_tries_b3"]; s["tn"] += r["pe_total_b3_opponent"]; s["td"] += r["pe_tries_b3_opponent"]
                s["k0n"] += r["pe_total_b0"]; s["k0d"] += r["pe_tries_b0"]; s["k1n"] += r["pe_total_b1"]; s["k1d"] += r["pe_tries_b1"]
                s["j"] += r["runs"]; s["jv"] += r["runs_opponent"]
    out = []
    for i, t in enumerate(jarj):
        rivi = {"seura": t, "lyh": seurat.get(t, {}).get("lyh"), "sija": i + 1, "luokka": luokka[t]}
        for k in ("karki", "keski", "hanta", "kaikki"):
            s = S.get((t, k))
            if not s or not s["O"]:
                rivi[k] = None; continue
            pc = lambda a, b: round(100 * a / b, 1) if b else None
            rivi[k] = {"O": int(s["O"]), "t3": round(s["t3"] / s["O"], 2), "t3v": round(s["t3v"] / s["O"], 2),
                       "kot": pc(s["kn"], s["kd"]), "torj": pc(s["td"] - s["tn"], s["td"]),
                       "kl0": pc(s["k0n"], s["k0d"]), "kl1": pc(s["k1n"], s["k1d"]),
                       "j": round(s["j"] / s["O"], 2), "jv": round(s["jv"] / s["O"], 2)}
        out.append(rivi)
    return {"kausi": kausi, "joukkueita": n, "rivit": out}


SAA_LUOKAT = [  # Keliluokat (19.11.2026). Järjestys = tarkistusjärjestys.
    ("karmea", "Karmea keli", "sade ja kylmä (≤ 12 °C) tai sade ja tuuli", lambda t, tu, sa: sa and (t <= 12 or tu)),
    ("sade", "Sadekeli", "sataa", lambda t, tu, sa: sa),
    ("helle", "Helle", "≥ 26 °C, pouta", lambda t, tu, sa: t >= 26),
    ("kylma", "Kylmä keli", "≤ 13 °C, pouta", lambda t, tu, sa: t <= 13),
    ("hyva", "Hyvä keli", "14–25 °C, pouta", lambda t, tu, sa: True),
]

def saavaikutus(rivit, sk):
    """Sään vaikutus ottelun yhteisjuoksuihin mallin odotukseen nähden.
    Lämpötilan kulmakerroin lasketaan kuukauden sisältä (kauden ajankohta vakioitu). Sade ja tuuli testataan
    samassa mallissa; niiden omaa vaikutusta ei löytynyt (19.11.2026), joten luokan vaikutus = lämpötila."""
    R = []
    for r in rivit:
        w = r.get("saa")
        if not w or w[0] is None or w[0] < -5:
            continue
        t = max(5, min(32, w[0])); odo = sk * (r["eh"]["t3"] * r["eh"]["kot"] + r["ev"]["t3"] * r["ev"]["kot"])
        R.append({"t": t, "tu": bool(w[1]), "sa": bool(w[2]), "kk": r["kk"], "ero": r["runs_h"] + r["runs_v"] - odo,
                  "jk": r["runs_h"] + r["runs_v"], "odo": odo})
    if len(R) < 200:
        return None
    # kuukauden sisäinen OLS: ero ~ lämpö + sade + tuuli
    kk = collections.defaultdict(list)
    for x in R:
        kk[x["kk"]].append(x)
    X, Y = [], []
    for g in kk.values():
        m = [sum(x[k] for x in g) / len(g) for k in ("t", "sa", "tu", "ero")]
        for x in g:
            X.append([x["t"] - m[0], x["sa"] - m[1], x["tu"] - m[2]]); Y.append(x["ero"] - m[3])
    XtX = [[sum(a[i] * a[j] for a in X) for j in range(3)] for i in range(3)]
    Xty = [sum(a[i] * y for a, y in zip(X, Y)) for i in range(3)]
    b = _ratkaise(XtX, Xty)
    e = [y - sum(bi * ai for bi, ai in zip(b, a)) for a, y in zip(X, Y)]
    s2 = sum(v * v for v in e) / (len(e) - 3 - len(kk))
    inv = [_ratkaise(XtX, [1.0 if i == j else 0.0 for i in range(3)]) for j in range(3)]
    se = [math.sqrt(s2 * inv[i][i]) for i in range(3)]
    ka_t = sum(x["t"] for x in R) / len(R); ka_jk = sum(x["jk"] for x in R) / len(R)
    luokat = []
    for avain, nimi, ehto, f in SAA_LUOKAT:
        g = [x for x in R if f(x["t"], x["tu"], x["sa"]) and not any(ff(x["t"], x["tu"], x["sa"]) for a2, _, _, ff in SAA_LUOKAT[:[l[0] for l in SAA_LUOKAT].index(avain)])]
        if not g:
            continue
        gt = sum(x["t"] for x in g) / len(g); havaittu = sum(x["ero"] for x in g) / len(g)
        sd = math.sqrt(sum((x["ero"] - havaittu) ** 2 for x in g) / max(1, len(g) - 1))
        luokat.append({"avain": avain, "nimi": nimi, "ehto": ehto, "n": len(g), "lampo": round(gt, 1),
                       "juoksut": round(sum(x["jk"] for x in g) / len(g), 2), "odotus": round(sum(x["odo"] for x in g) / len(g), 2),
                       "havaittu": round(havaittu, 2), "luottamus": round(1.96 * sd / math.sqrt(len(g)), 2),
                       "vaikutus": round(b[0] * (gt - ka_t), 2)})
    lampo = []
    for a in range(6, 31, 3):
        g = [x for x in R if a <= x["t"] < a + 3]
        if len(g) >= 20:
            m = sum(x["ero"] for x in g) / len(g); sd = math.sqrt(sum((x["ero"] - m) ** 2 for x in g) / (len(g) - 1))
            lampo.append({"vali": f"{a}–{a + 2}", "keski": a + 1, "n": len(g), "ero": round(m, 2), "luottamus": round(1.96 * sd / math.sqrt(len(g)), 2)})
    # tuuli: myötätuulikomponentti (kotikentät, joiden suunta tiedetään), sama kuukauden sisäinen OLS lämmön kanssa
    tuuli = None
    W = []
    for r in rivit:
        w = r.get("saa")
        if r.get("myota") is None or not w or w[0] is None or w[0] < -5:
            continue
        odo = sk * (r["eh"]["t3"] * r["eh"]["kot"] + r["ev"]["t3"] * r["ev"]["kot"])
        W.append({"t": max(5, min(32, w[0])), "m": r["myota"], "kk": r["kk"], "ero": r["runs_h"] + r["runs_v"] - odo})
    if len(W) >= 300:
        g2 = collections.defaultdict(list)
        for x in W:
            g2[x["kk"]].append(x)
        X2, Y2 = [], []
        for g in g2.values():
            m = [sum(x[k] for x in g) / len(g) for k in ("t", "m", "ero")]
            for x in g:
                X2.append([x["t"] - m[0], x["m"] - m[1]]); Y2.append(x["ero"] - m[2])
        A2 = [[sum(a[i] * a[j] for a in X2) for j in range(2)] for i in range(2)]
        b2 = _ratkaise(A2, [sum(a[i] * y for a, y in zip(X2, Y2)) for i in range(2)])
        e2 = [y - b2[0] * a[0] - b2[1] * a[1] for a, y in zip(X2, Y2)]
        s22 = sum(v * v for v in e2) / (len(e2) - 2 - len(g2))
        inv2 = [_ratkaise(A2, [1.0 if i == j else 0.0 for i in range(2)]) for j in range(2)]
        ka_m = sum(x["m"] for x in W) / len(W)
        TL = [("vahva_vasta", "Vahva vastatuuli", "≤ −3 m/s", lambda v: v <= -3), ("vasta", "Vastatuuli", "−3…−1 m/s", lambda v: -3 < v < -1),
              ("normi", "Normituuli", "−1…+1 m/s", lambda v: -1 <= v <= 1), ("myota", "Myötätuuli", "+1…+3 m/s", lambda v: 1 < v < 3),
              ("vahva_myota", "Vahva myötätuuli", "≥ +3 m/s", lambda v: v >= 3)]
        luokat_t = []
        for avain, nimi, ehto, f in TL:
            g = [x for x in W if f(x["m"])]
            if not g:
                continue
            mm = sum(x["m"] for x in g) / len(g); hv = sum(x["ero"] for x in g) / len(g)
            sd = math.sqrt(sum((x["ero"] - hv) ** 2 for x in g) / max(1, len(g) - 1))
            luokat_t.append({"avain": avain, "nimi": nimi, "ehto": ehto, "n": len(g), "myota_ka": round(mm, 2),
                             "havaittu": round(hv, 2), "luottamus": round(1.96 * sd / math.sqrt(len(g)), 2), "vaikutus": round(b2[1] * mm, 2)})
        from .kentat import KENTAT, SEURA
        tuuli = {"n": len(W), "per_ms": round(b2[1], 4), "per_ms_luottamus": round(1.96 * math.sqrt(s22 * inv2[1][1]), 4),
                 "myota_ka": round(ka_m, 2), "luokat": luokat_t, "kentat": KENTAT, "seurat": SEURA}
    return {"n": len(R), "lampo_ka": round(ka_t, 1), "juoksut_ka": round(ka_jk, 2), "myotatuuli": tuuli,
            "per_aste": round(b[0], 4), "per_aste_luottamus": round(1.96 * se[0], 4),
            "sade": round(b[1], 2), "sade_luottamus": round(1.96 * se[1], 2), "tuuli": round(b[2], 2), "tuuli_luottamus": round(1.96 * se[2], 2),
            "luokat": luokat, "lampo": lampo}


def kotietu(ottelut, seurat, rajaus=None):
    """Kotijoukkueen voitto% kausittain (kaikki vaiheet) ja joukkueittain kolmelta viimeiseltä kaudelta."""
    kk = collections.defaultdict(lambda: [0, 0, 0])
    for o, h, v in ottelut:
        x = kk[o["kausi"]]; x[0] += 1; x[1] += h["won"]; x[2] += h["runs"] - v["runs"]
    kausittain = {k: {"O": x[0], "voitto": round(x[1] / x[0], 3), "juoksuero": round(x[2] / x[0], 2)} for k, x in sorted(kk.items())}
    viim = sorted(kk)[-3:]
    J = collections.defaultdict(lambda: [0, 0, 0, 0])  # koti O, koti V, vieras O, vieras V
    for o, h, v in ottelut:
        if o["kausi"] in viim:
            J[h["team_id"]][0] += 1; J[h["team_id"]][1] += h["won"]; J[v["team_id"]][2] += 1; J[v["team_id"]][3] += v["won"]
    jj = [{"seura": t, "lyh": seurat.get(t, {}).get("lyh"), "kotiO": x[0], "koti": round(x[1] / x[0], 3) if x[0] else None,
           "vierasO": x[2], "vieras": round(x[3] / x[2], 3) if x[2] else None} for t, x in J.items() if x[0] + x[2] >= 20 and (rajaus is None or t in rajaus)]
    jj.sort(key=lambda r: -((r["koti"] or 0) - (r["vieras"] or 0)))
    return {"kausittain": kausittain, "joukkueittain": jj, "kaudet": f"{viim[0]}–{viim[-1]}"}


def sarja_seuraava(seurat, A):
    """Seuraavan kauden joukkueet: seurannan kokoonpanot (lyhenteet) → seurat. Varalla kuluvan kauden joukkueet."""
    lyh2seura = {}
    for s, v in seurat.items():
        if v.get("lyh"):
            lyh2seura[v["lyh"]] = s
    try:
        with open(SEURANTA, encoding="utf-8") as f:
            kok = json.load(f).get("kokoonpanot") or {}
        nimet = list(kok.keys()) if isinstance(kok, dict) else [k.get("joukkue") for k in kok]
    except (OSError, ValueError):
        nimet = []
    joukkueet = [(n, lyh2seura.get(n)) for n in nimet if n]
    if len([s for _, s in joukkueet if s]) < 8:
        joukkueet = [(seurat[s]["lyh"], s) for s in A.nyt]
    return joukkueet


def laske():
    ottelut, seurat = lataa()
    rivit, A = kulje(ottelut)
    jt = jalkitesti(rivit)
    # lopullinen malli: kaikki kaudet
    w = logreg([[r["x"][s] for s in MALLI] for r in rivit], [r["won"] for r in rivit])
    viimeisin = max(o["kausi"] for o, _, _ in ottelut)
    kesken = any(o["kausi"] == viimeisin and not o.get("tulos") and not o.get("peruttu") for o, _, _ in ottelut)
    # tilanne seuraavan kauden alussa (jos kausi on päättynyt) tai nyt (kesken)
    seuraava = viimeisin if kesken else viimeisin + 1
    if not kesken:
        A.uusi_kausi(seuraava)
    joukkueet = sarja_seuraava(seurat, A)
    sk = sum(r["runs_h"] + r["runs_v"] for r in rivit) / sum(r["eh"]["t3"] * r["eh"]["kot"] + r["ev"]["t3"] * r["ev"]["kot"] for r in rivit)
    tj = []
    for lyh, s in joukkueet:
        sid = s if s is not None else f"uusi:{lyh}"
        rivi = {"lyh": lyh, "seura": s, "nousija": s not in A.edelliset if not kesken else s not in A.nyt and s not in A.edelliset}
        for st in TIL:
            rivi["o_" + st] = round(A.arvo(sid, st, "o"), 4); rivi["d_" + st] = round(A.arvo(sid, st, "d"), 4)
        tj.append(rivi)
    # vahvuus: voitto% keskitason vastustajaa vastaan neutraalilla kentällä (kotietu pois)
    for r in tj:
        x = [(math.log(risti(s, r["o_" + s], A.lg[s], A.lg[s]) / risti(s, A.lg[s], r["d_" + s], A.lg[s])) if not TIL[s][1]
              else _logit(risti(s, r["o_" + s], A.lg[s], A.lg[s])) - _logit(risti(s, A.lg[s], r["d_" + s], A.lg[s]))) for s in MALLI]
        r["vahvuus"] = round(1 / (1 + math.exp(-sum(a * b for a, b in zip(w[1:], x)))), 3)
    tj.sort(key=lambda r: -r["vahvuus"])
    # piirteiden painoarvo: kerroin × keskihajonta (vertailukelpoinen eri asteikoilla)
    sd = {}
    for s in MALLI:
        xs = [r["x"][s] for r in rivit]; m = sum(xs) / len(xs); sd[s] = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))
    kj = sum(r["runs_h"] for r in rivit) / len(rivit); vj = sum(r["runs_v"] for r in rivit) / len(rivit)
    d = {"paivitetty": __import__("datetime").datetime.now().isoformat(timespec="minutes"), "kausi": seuraava,
         "pohja": f"{min(o['kausi'] for o, _, _ in ottelut)}–{viimeisin}", "otteluita": len(rivit), "kesken": kesken,
         "parametrit": {"carry": CARRY, "k": K, "lambda": LAMBDA, "nousija": NOUSIJA, "viritys": f"2011–{VIRITYS_LOPPU}"},
         "malli": {"vakio": round(w[0], 4), "kertoimet": {s: round(c, 4) for s, c in zip(MALLI, w[1:])}, "skaala_juoksut": round(sk, 4),
                   "painoarvo": {s: round(c * sd[s], 4) for s, c in zip(MALLI, w[1:])},
                   "koti_juoksut": round(2 * kj / (kj + vj), 4), "vieras_juoksut": round(2 * vj / (kj + vj), 4)},
         "sarja": {s: round(v, 4) for s, v in A.lg.items()}, "tilastot": {s: TIL[s][2] for s in TIL},
         "joukkueet": tj, "jalkitesti": jt, "luokat": luokat(ottelut, seurat, viimeisin), "kotietu": kotietu(ottelut, seurat, {s for _, s in joukkueet}),
         "saa": saavaikutus(rivit, sk)}
    return d


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--ei-hakua", action="store_true"); a = ap.parse_args()
    if not a.ei_hakua:
        paivita_pohja()
    d = laske()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "ennuste.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    j = d["jalkitesti"]
    print(json.dumps({"kausi": d["kausi"], "otteluita": d["otteluita"], "testi": j["testi"], "malli": j["malli"], "juoksut": j["juoksut"],
                      "koti": j["koti"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
