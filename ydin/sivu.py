"""Rakentaa julkaistavan sivuston (site/): index.html = Koti, pelaajat.html = Pelaajat.
Lähteet: data/out (pesistulokset.fi stats-tool + otteluluettelo) ja data/seuranta/seuranta.json
(Jarvis-seurannan vienti: siirrot, pelinjohtajat, huhut, tilannekatsaus).
Ajo: python -m ydin.sivu
Sarjapisteet: 2–0-voitto 3 p, 1–0-voitto 2 p, kotiutuskilpailu- tai supervuoroparivoitto 2 p ja -tappio 1 p
(täsmää pesistulokset.fi:n viralliseen runkosarjataulukkoon 2026)."""
import collections, json, re, sys, os

JUURI = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(JUURI, "data", "out")
SEURANTA = os.path.join(JUURI, "data", "seuranta", "seuranta.json")
WEB = os.path.join(JUURI, "web")
SITE = os.path.join(JUURI, "site")
KAUSI = 2026

def lue(n):
    with open(os.path.join(OUT, n), encoding="utf-8") as f:
        return json.load(f)

def tulos(t):
    """'1-2k (…)' -> (koti_jaksot, vieras_jaksot, lisä) ; lisä '' / 's' / 'k'"""
    h = t.split()[0].lower()
    lisa = h[-1] if h[-1] in "sk" else ""
    a, b = map(int, re.sub("[sk]", "", h).split("-"))
    return a, b, lisa

def pisteet(a, b, lisa):
    """-> (voittajan pisteet, häviäjän pisteet)"""
    if lisa:
        return 2, 1
    return (3, 0) if max(a, b) == 2 else (2, 0)

def koti_data(vientipolku=SEURANTA):
    tiimit = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        for t in lue(f"joukkueet_{KAUSI}_{ph}.json"):
            tiimit[t["id"]] = {"lyh": t["lyhenne"], "nimi": t["nimi"]}
    ott = sorted(lue(f"ottelut_{KAUSI}.json"), key=lambda m: m["pvm"])

    # sarjataulukko ja vire (runkosarja)
    S = collections.defaultdict(lambda: {"O": 0, "V": 0, "H": 0, "P": 0, "vire": []})
    for m in ott:
        if m["vaihe"] != 1 or not m["tulos"]:
            continue
        a, b, lisa = tulos(m["tulos"])
        w, l = (m["koti"], m["vieras"]) if a > b else (m["vieras"], m["koti"])
        pw, pl = pisteet(a, b, lisa)
        for t, v, p in ((w, 1, pw), (l, 0, pl)):
            s = S[t]; s["O"] += 1; s["V"] += v; s["H"] += 1 - v; s["P"] += p
            vast = l if t == w else w
            s["vire"].append({"v": v, "p": p, "vs": tiimit[vast]["lyh"], "t": m["tulos"].split()[0], "pvm": m["pvm"][:10],
                              "koti": t == m["koti"]})
    jr = {t["id"]: t for t in lue(f"joukkueet_{KAUSI}_runko.json")}
    taulukko = []
    for t, s in S.items():
        j = jr[t]
        taulukko.append({"id": t, **tiimit[t], "O": s["O"], "V": s["V"], "H": s["H"], "P": s["P"],
                         "vire": s["vire"][-5:], "pistekulku": [x["p"] for x in s["vire"]],
                         "juoksut": j["runs"], "paastetyt": j["runs_opponent"],
                         "kotiutus": j["kotiutus%"], "torjunta": j["torjunta%"], "KL%": j["KL%"],
                         "j1": [j["runs_p0"], j["runs_p0_opponent"]], "j2": [j["runs_p1"], j["runs_p1_opponent"]],
                         "vapaat": j["walks"], "harhaheitot": j["wild_throws"],
                         "vapaat_v": j["walks_opponent"], "KLpesat": [j.get(f"KL%{n}") for n in range(4)]})
    taulukko.sort(key=lambda x: (-x["P"], -x["V"]))

    # pudotuspelit ja karsinnat
    pudotus = []
    for nimi, ms, w in kierrokset(ott):
        x, y = sorted({ms[0]["koti"], ms[0]["vieras"]}, key=lambda t: -w[t])
        pudotus.append({"kierros": nimi, "a": tiimit[x]["lyh"], "b": tiimit[y]["lyh"], "wa": w[x], "wb": w[y],
                        "ottelut": [{"pvm": m["pvm"][:10], "koti": tiimit[m["koti"]]["lyh"], "vieras": tiimit[m["vieras"]]["lyh"], "t": m["tulos"]} for m in ms]})

    # pelaajat (runkosarja + koko kausi)
    def pel(ph):
        return [{k: p[k] for k in ("id", "nimi", "joukkue", "O", "K", "L", "T", "YHT", "KL", "KLY", "KL%")} for p in lue(f"pelaajat_{KAUSI}_{ph}.json")]
    pelaajat = pel("runko")
    for p in pelaajat:
        p["jk"] = tiimit.get(p.pop("joukkue"), {}).get("lyh", "?")

    with open(vientipolku, encoding="utf-8") as f:
        V = json.load(f)
    meta = lue(f"meta_{KAUSI}.json")
    kuvat = lue_kuvat()
    return {"kausi": KAUSI, "paivitetty": meta["paivitetty"], "taulukko": taulukko, "pudotus": pudotus,
            "pelaajat": pelaajat, "vault": V,
            "kuvat": {str(p["id"]): kuvat["pelaajat"].get(str(p["id"])) for p in pelaajat if kuvat["pelaajat"].get(str(p["id"]))},
            "logot": kuvat["logot"], "jhist": joukkuehistoria()}

KIERROSNIMET = {2: ["Puolivälierä"] * 4 + ["Välierä"] * 2 + ["Pronssiottelu", "Loppuottelu"], 3: ["Putoamiskarsinta", "Superpesis-karsinta"]}

def kierrokset(ott):
    """Pudotuspeli- ja karsintasarjat aikajärjestyksessä: [(kierroksen nimi, ottelut, voittolaskuri joukkueittain)]."""
    g = collections.defaultdict(list)
    for m in sorted(ott, key=lambda m: m["pvm"]):
        if m["vaihe"] in (2, 3) and m["tulos"]:
            g[(m["vaihe"], frozenset([m["koti"], m["vieras"]]))].append(m)
    laskuri, sarjat = collections.Counter(), []
    for (v, _), ms in sorted(g.items(), key=lambda x: x[1][0]["pvm"]):
        w = collections.Counter({ms[0]["koti"]: 0, ms[0]["vieras"]: 0})
        for m in ms:
            a, b, _l = tulos(m["tulos"]); w[m["koti"] if a > b else m["vieras"]] += 1
        i = laskuri[v]; laskuri[v] += 1
        sarjat.append((KIERROSNIMET[v][i] if i < len(KIERROSNIMET[v]) else f"Vaihe {v}", ms, w))
    return sarjat

def joukkuehistoria():
    h = {}
    for kausi in range(KAUSI - 10, KAUSI + 1):
        try:
            h[kausi] = lue(f"joukkuehistoria_{kausi}.json")["joukkueet"]
        except FileNotFoundError:
            pass
    return h

def pelaajat_data():
    tm = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        for t in lue(f"joukkueet_{KAUSI}_{ph}.json"):
            tm[t["id"]] = t["lyhenne"]
    keys = ["O", "K", "L", "T", "KL", "KLY", "KL0", "KLY0", "KL1", "KLY1", "KL2", "KLY2", "KL3", "KLY3", "LV"]
    vaiheet = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        try:
            rivit = lue(f"pelaajat_{KAUSI}_{ph}.json")
        except FileNotFoundError:
            continue
        vaiheet[ph] = [[p["id"], p["nimi"], tm.get(p["joukkue"], "?")] + [p[k] for k in keys] for p in rivit]
    nykyiset = {str(r[0]) for v in vaiheet.values() for r in v}
    kuvat = lue_kuvat()
    historia = {}
    for kausi in range(KAUSI - 10, KAUSI + 1):
        try:
            h = lue(f"historia_{kausi}.json")
        except FileNotFoundError:
            continue
        historia[kausi] = {laji: {pid: r for pid, r in h[laji].items() if pid in nykyiset} for laji in ("runko", "kaikki")}
    return {"kausi": KAUSI, "paivitetty": lue(f"meta_{KAUSI}.json")["paivitetty"], "kentat": ["id", "nimi", "jk"] + keys, "vaiheet": vaiheet,
            "historia": historia, "hkentat": ["jk"] + HKENTAT,
            "kuvat": {pid: u for pid, u in kuvat["pelaajat"].items() if pid in nykyiset}, "logot": kuvat["logot"]}

def _tiimit():
    tm = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        try:
            for t in lue(f"joukkueet_{KAUSI}_{ph}.json"):
                tm[t["id"]] = t["lyhenne"]
        except FileNotFoundError:
            pass
    return tm

def _otteluittain():
    """Kaikkien vaiheiden ottelukohtaiset rivit: (pelaajarivit, joukkuerivit)."""
    P, J = [], []
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        try:
            d = lue(f"otteluittain_{KAUSI}_{ph}.json")
        except FileNotFoundError:
            continue
        P += d["pelaajat"]; J += d["joukkueet"]
    return P, J

def _nimet():
    n = {}
    for kausi in range(KAUSI - 10, KAUSI + 1):
        try:
            n.update({int(k): v for k, v in lue(f"historia_{kausi}.json")["nimet"].items() if v})
        except FileNotFoundError:
            pass
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        try:
            n.update({p["id"]: p["nimi"] for p in lue(f"pelaajat_{KAUSI}_{ph}.json") if p.get("nimi")})
        except FileNotFoundError:
            pass
    return n

def _i(v):
    return int(v or 0)

def ottelut_data():
    """Ottelut-sivu: kaikki runkosarjan, pudotuspelien ja karsintojen ottelut + ottelukohtaiset joukkue- ja pelaajaluvut.
    Joukkue per ottelu: [juoksut, KL, KLY, KL3, KLY3, K, vapaat, harhaheitot].
    Pelaaja per ottelu: [id, joukkue, K, L, T, KL, KLY, lyöntivuorot]."""
    tm = _tiimit(); tn = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        try:
            tn.update({t["lyhenne"]: t["nimi"] for t in lue(f"joukkueet_{KAUSI}_{ph}.json")})
        except FileNotFoundError:
            pass
    ott = [m for m in lue(f"ottelut_{KAUSI}.json") if m["vaihe"] in (1, 2, 3) and m["tulos"]]
    kier = {}
    for nimi, ms, _w in kierrokset(ott):
        for n, m in enumerate(ms, 1):
            kier[m["id"]] = f"{nimi} · {n}. ottelu"
    P, J = _otteluittain()
    jo = collections.defaultdict(dict)
    for r in J:
        jo[r["match_id"]][r["team_id"]] = [_i(r.get(k)) for k in ("runs", "pe_total", "pe_tries_total", "pe_total_b3", "pe_tries_b3", "homeruns", "walks", "wild_throws")]
    pe = collections.defaultdict(list); kaytetyt = set()
    for r in P:
        rivi = [r["player_id"], r["team_id"]] + [_i(r.get(k)) for k in ("homeruns", "scorings", "runs", "batpe_total_succeeded", "batpe_total_tries", "turns_at_bat")]
        if any(rivi[2:]):
            pe[r["match_id"]].append(rivi); kaytetyt.add(r["player_id"])
    nimet = _nimet(); kuvat = lue_kuvat()
    ottelut = [[m["id"], m["pvm"], m["vaihe"], m["koti"], m["vieras"], m["tulos"], kier.get(m["id"], "")] for m in sorted(ott, key=lambda m: m["pvm"])]
    return {"kausi": KAUSI, "paivitetty": lue(f"meta_{KAUSI}.json")["paivitetty"], "tiimit": {str(k): v for k, v in tm.items()}, "tnimet": tn,
            "ottelut": ottelut, "joukkueet": {str(k): {str(t): v for t, v in d.items()} for k, d in jo.items()},
            "pelaajat": {str(k): v for k, v in pe.items()}, "nimet": {str(p): nimet.get(p, "?") for p in kaytetyt},
            "kuvat": {str(p): kuvat["pelaajat"][str(p)] for p in kaytetyt if str(p) in kuvat["pelaajat"]}, "logot": kuvat["logot"]}

def tulostaulut_data(haku_idt):
    """Tulostaulut: pelaajat (runkosarja, koko kausi, kaudet yhteensä), ottelukohtaiset ennätykset ja joukkueet."""
    tm = _tiimit(); nimet = _nimet(); kuvat = lue_kuvat()
    K = ["O", "K", "L", "T", "KL", "KLY", "KL0", "KLY0", "KL1", "KLY1", "KL2", "KLY2", "KL3", "KLY3"]
    def rivi(pid, jk, d):
        return [pid, nimet.get(pid, "?"), jk] + [d[k] for k in K]
    runko = [rivi(p["id"], tm.get(p["joukkue"], "?"), p) for p in lue(f"pelaajat_{KAUSI}_runko.json")]
    summa = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        try:
            rr = lue(f"pelaajat_{KAUSI}_{ph}.json")
        except FileNotFoundError:
            continue
        for p in rr:
            if p["id"] not in summa:
                summa[p["id"]] = {"jk": tm.get(p["joukkue"], "?"), **{k: 0 for k in K}}
            for k in K:
                summa[p["id"]][k] += p[k]
    kausi = [rivi(pid, d["jk"], d) for pid, d in summa.items()]
    kaudet, ura = [], {}
    for k in range(KAUSI - 10, KAUSI + 1):
        try:
            h = lue(f"historia_{k}.json")
        except FileNotFoundError:
            continue
        kaudet.append(k)
        for pid, r in h["kaikki"].items():
            pid = int(pid); u = ura.setdefault(pid, {"jk": r[0], "kaudet": 0, **{x: 0 for x in K}})
            u["jk"] = r[0]; u["kaudet"] += 1
            for x, v in zip(HKENTAT, r[1:]):
                u[x] += v
    ura_r = [rivi(pid, d["jk"], d) + [d["kaudet"]] for pid, d in ura.items()]
    P, J = _otteluittain()
    ott = {m["id"]: m for m in lue(f"ottelut_{KAUSI}.json")}
    yksi = []
    for r in P:
        m = ott.get(r["match_id"])
        if not m or m["vaihe"] not in (1, 2, 3):
            continue
        v = [_i(r.get(k)) for k in ("homeruns", "scorings", "runs", "batpe_total_succeeded", "batpe_total_tries")]
        yksi.append([r["player_id"], nimet.get(r["player_id"], "?"), tm.get(r["team_id"], "?"), tm.get(r["opponent_team_id"], "?"), r["match_id"], m["pvm"][:10], m["vaihe"]] + v)
    # Kunkin luokan kärki valmiiksi: 10 parasta + rajalla oleva tasapisteryhmä, jos se mahtuu (enintään 15 riviä).
    # Muuten ryhmä jätetään pois ja sivulle kerrotaan raja-arvo.
    avaimet = {"YHT": lambda x: x[7] + x[8] + x[9], "K": lambda x: x[7], "L": lambda x: x[8], "T": lambda x: x[9], "KL": lambda x: x[10]}
    valitut, karjet = [], {}
    for nimi, f in avaimet.items():
        jarj = sorted((x for x in yksi if f(x) > 0), key=lambda x: (-f(x), x[5]))
        if len(jarj) > 10:
            v = f(jarj[9]); yli = [x for x in jarj if f(x) > v]; ryhma = [x for x in jarj if f(x) == v]
            jarj, raja = (yli + ryhma, None) if len(yli) + len(ryhma) <= 15 else (yli, v)
        else:
            raja = None
        idx = []
        for x in jarj:
            if not any(x is y for y in valitut):
                valitut.append(x)
            idx.append(next(i for i, y in enumerate(valitut) if y is x))
        karjet[nimi] = {"rivit": idx, "raja": raja}
    yksi = valitut
    jr = [{"jk": t["lyhenne"], "O": t["O"], "KL": t["pe_total"], "KLY": t["pe_tries_total"], "KL3": t["pe_total_b3"], "KLY3": t["pe_tries_b3"],
           "torj": t["pe_tries_b3_opponent"] - t["pe_total_b3_opponent"], "torjY": t["pe_tries_b3_opponent"],
           "juoksut": t["runs"], "paastetyt": t["runs_opponent"], "K": t["homeruns"], "Kv": t["homeruns_opponent"],
           "vapaat": t["walks"], "vapaat_v": t["walks_opponent"], "hh": t["wild_throws"], "hh_v": t["wild_throws_opponent"]}
          for t in lue(f"joukkueet_{KAUSI}_runko.json")]
    kaikki_id = {r[0] for r in runko + kausi + ura_r + yksi}
    return {"kausi": KAUSI, "paivitetty": lue(f"meta_{KAUSI}.json")["paivitetty"], "kentat": ["id", "nimi", "jk"] + K,
            "runko": runko, "kausi_kaikki": kausi, "ura": ura_r, "kaudet": kaudet, "yksi": yksi, "yksi_karjet": karjet, "joukkueet": jr,
            "linkit": sorted(haku_idt & kaikki_id),
            "kuvat": {str(p): kuvat["pelaajat"][str(p)] for p in kaikki_id if str(p) in kuvat["pelaajat"]}, "logot": kuvat["logot"]}

def lukkarit_data(haku_idt):
    """Lukkarit-sivu: aloittavan lukkarin ottelurivit kausilta 2023– (ks. ydin/lukkarit.py) + lukkareiden omat lyöntitilastot."""
    kaudet, kentat, nimet, pids = {}, None, {}, set()
    for k in range(KAUSI - 10, KAUSI + 1):
        try:
            d = lue(f"lukkarit_{k}.json")
        except FileNotFoundError:
            continue
        kaudet[k] = d["rivit"]; kentat = d["kentat"]; nimet.update(d["nimet"])
        pids |= {r[3] for r in d["rivit"]}
    lyonti = {}
    for k in kaudet:
        try:
            h = lue(f"historia_{k}.json")
        except FileNotFoundError:
            continue
        lyonti[k] = {laji: {pid: r for pid, r in h[laji].items() if int(pid) in pids} for laji in ("runko", "kaikki")}
    kuvat = lue_kuvat()
    return {"kausi": KAUSI, "kentat": kentat, "kaudet": kaudet, "nimet": nimet, "lyonti": lyonti, "hkentat": ["jk"] + HKENTAT,
            "linkit": sorted(haku_idt & pids), "kuvat": {str(p): kuvat["pelaajat"][str(p)] for p in pids if str(p) in kuvat["pelaajat"]},
            "logot": kuvat["logot"]}

HKENTAT = ["O", "K", "L", "T", "KL", "KLY", "KL0", "KLY0", "KL1", "KLY1", "KL2", "KLY2", "KL3", "KLY3"]

def lue_kuvat():
    try:
        return lue("kuvat.json")
    except FileNotFoundError:
        return {"pelaajat": {}, "logot": {}}

IKONIT = {
    "koti": '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "kausi": '<path d="M4 6h16M4 12h16M4 18h10"/>',
    "pelaajat": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/>',
    "ottelut": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "joukkueet": '<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/>',
    "tulostaulut": '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4"/>',
    "lukkarit": '<circle cx="12" cy="6" r="3"/><path d="M12 9v6M8 21l4-6 4 6M6 12l6-2 6 2"/>',
    "sisalto": '<path d="M5 4h10l4 4v12H5z"/><path d="M9 12h6M9 16h6"/>',
}
# (avain, otsikko, tiedosto tai None = tulossa)
VALIKKO = [("koti", "Koti", "index.html"), ("kausi", "Kausi 2026", "kausi-2026.html"), ("joukkueet", "Joukkueet", "joukkueet.html"),
           ("pelaajat", "Pelaajat", "pelaajat.html"), ("ottelut", "Ottelut", "ottelut.html"),
           ("lukkarit", "Lukkarit", "lukkarit.html"), ("tulostaulut", "Tulostaulut", "tulostaulut.html"), None, ("sisalto", "Sisältö", None)]

def nav(nykyinen):
    osat = []
    for v in VALIKKO:
        if v is None:
            osat.append('<span class="sep" role="separator"></span>'); continue
        avain, nimi, tied = v
        ikoni = f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">{IKONIT[avain]}</svg>'
        if tied is None:
            osat.append(f'<a aria-disabled="true" class="off">{ikoni}{nimi}<span class="soon">tulossa</span></a>')
        else:
            cur = ' aria-current="page"' if avain == nykyinen else ""
            osat.append(f'<a href="{tied}"{cur}>{ikoni}{nimi}</a>')
    return "".join(osat)

def osat(pohja):
    with open(os.path.join(WEB, pohja), encoding="utf-8") as f:
        t = f.read()
    a, b, c = t.index("<!--TYYLI-->"), t.index("<!--SISALTO-->"), t.index("<!--SKRIPTI-->")
    return t[a + 12:b].strip(), t[b + 14:c].rstrip(), t[c + 14:].strip()

def js(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def rakenna(pohja, data, kohde, otsikko, valikko, haku, paivitetty):
    with open(os.path.join(WEB, "runko.html"), encoding="utf-8") as f:
        runko = f.read()
    tyyli, sisalto, skripti = osat(pohja)
    korvaa = {"__OTSIKKO__": otsikko, "__TYYLI__": tyyli, "__NAV__": nav(valikko), "__PAIVITETTY__": paivitetty,
              "__HAKU__": js(haku), "__SISALTO__": sisalto, "__SKRIPTI__": skripti.replace("__DATA__", js(data))}
    html = runko
    for k, v in korvaa.items():
        html = html.replace(k, v, 1)
    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, kohde), "w", encoding="utf-8") as f:
        f.write(html)
    return len(html)

def main():
    k = koti_data()
    pd = pelaajat_data()
    haku, nahty = [], set()
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        for r in pd["vaiheet"].get(ph, []):
            if r[0] not in nahty:
                nahty.add(r[0]); haku.append([r[0], r[1], r[2]])
    haku.sort(key=lambda h: h[1])
    import datetime
    try:
        pv = datetime.datetime.fromisoformat(k["paivitetty"]).strftime("%-d.%-m.%Y")
    except Exception:
        pv = k["paivitetty"]
    yht = dict(haku=haku, paivitetty=pv)
    print("index.html", rakenna("koti.template.html", k, "index.html", "YDIN 2027 Koti", "koti", **yht))
    print("kausi-2026.html", rakenna("kausi2026.template.html", k, "kausi-2026.html", "YDIN 2027 Kausi 2026", "kausi", **yht))
    print("joukkueet.html", rakenna("joukkueet.template.html", k, "joukkueet.html", "YDIN 2027 Joukkueet", "joukkueet", **yht))
    print("pelaajat.html", rakenna("pelaajat.template.html", pd, "pelaajat.html", "YDIN 2027 Pelaajat", "pelaajat", **yht))
    print("ottelut.html", rakenna("ottelut.template.html", ottelut_data(), "ottelut.html", "YDIN 2027 Ottelut", "ottelut", **yht))
    print("tulostaulut.html", rakenna("tulostaulut.template.html", tulostaulut_data({h[0] for h in haku}), "tulostaulut.html", "YDIN 2027 Tulostaulut", "tulostaulut", **yht))
    print("lukkarit.html", rakenna("lukkarit.template.html", lukkarit_data({h[0] for h in haku}), "lukkarit.html", "YDIN 2027 Lukkarit", "lukkarit", **yht))
    print([(t["lyh"], t["P"]) for t in k["taulukko"]])

if __name__ == "__main__":
    main()
