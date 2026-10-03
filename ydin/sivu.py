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
                         "vapaat": j["walks"], "harhaheitot": j["wild_throws"]})
    taulukko.sort(key=lambda x: (-x["P"], -x["V"]))

    # pudotuspelit ja karsinnat
    g = collections.defaultdict(list)
    for m in ott:
        if m["vaihe"] in (2, 3) and m["tulos"]:
            g[(m["vaihe"], frozenset([m["koti"], m["vieras"]]))].append(m)
    sarjat = sorted(g.items(), key=lambda x: x[1][0]["pvm"])
    nimet = {2: ["Puolivälierä"] * 4 + ["Välierä"] * 2 + ["Pronssiottelu", "Loppuottelu"], 3: ["Putoamiskarsinta", "Superpesis-karsinta"]}
    laskuri = collections.Counter(); pudotus = []
    for (v, pari), ms in sarjat:
        w = collections.Counter()
        for m in ms:
            a, b, _ = tulos(m["tulos"]); w[m["koti"] if a > b else m["vieras"]] += 1
        i = laskuri[v]; laskuri[v] += 1
        nimi = nimet[v][i] if i < len(nimet[v]) else f"Vaihe {v}"
        x, y = sorted(pari, key=lambda t: -w[t])
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
    return {"kausi": KAUSI, "paivitetty": meta["paivitetty"], "taulukko": taulukko, "pudotus": pudotus,
            "pelaajat": pelaajat, "vault": V}

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
    return {"kausi": KAUSI, "paivitetty": lue(f"meta_{KAUSI}.json")["paivitetty"], "kentat": ["id", "nimi", "jk"] + keys, "vaiheet": vaiheet}

KEHYS = """<!doctype html>
<html lang="fi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>
%s
</body></html>
"""

def rakenna(pohja, data, kohde):
    with open(os.path.join(WEB, pohja), encoding="utf-8") as f:
        t = f.read()
    html = t.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, kohde), "w", encoding="utf-8") as f:
        f.write(KEHYS.replace("%s", html, 1))
    return len(html)

def main():
    k = koti_data()
    print("index.html", rakenna("koti.template.html", k, "index.html"))
    print("pelaajat.html", rakenna("pelaajat.template.html", pelaajat_data(), "pelaajat.html"))
    print([(t["lyh"], t["P"]) for t in k["taulukko"]])

if __name__ == "__main__":
    main()
