"""Pelaajien kausihistoria (Superpesis 2023–), pelaajakuvat ja seuralogot.
python -m ydin.historia  -> data/out/historia_{kausi}.json + data/out/kuvat.json
Päättyneet kaudet haetaan vain kerran (tiedosto jää välimuistiksi); kuluva kausi päivitetään joka ajolla.
Kuvat ja logot ovat pesistulokset.fi:n palvelimella; sivu näyttää ne sieltä lähteen kanssa."""
import json, os
from . import haku, kaudet
from .mittarit import pelaajat, joukkueet

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")
KENTAT = ["O", "K", "L", "T", "KL", "KLY", "KL0", "KLY0", "KL1", "KLY1", "KL2", "KLY2", "KL3", "KLY3"]
KULUVA = max(kaudet.MSU)

def _polku(n):
    return os.path.join(OUT, n)

def hae_kausi(kausi):
    ss = kaudet.MSU[kausi]
    _, maps = haku.ottelut(ss)
    lyh = {t["id"]: t["value"].get("shorthand") for t in maps.get("team", [])}
    logot = {t["value"].get("shorthand"): (t["value"].get("sport_club") or {}).get("icon") for t in maps.get("team", [])}
    rivit_kaikki, kuvat, nimet = [], {}, {}
    vaiheet = {}
    for ph in (1, 2, 3):
        d = haku.pelaajat_otteluittain(ss, ph)
        if not d.get("data"):
            continue
        for p in (d.get("maps") or {}).get("player", []):
            v = p["value"]; nimet[p["id"]] = v.get("name") or f"{v.get('first_name','')} {v.get('last_name','')}".strip()
            img = (v.get("image") or {}).get("medium")
            if img: kuvat[p["id"]] = img
        vaiheet[ph] = pelaajat(d["data"])
        rivit_kaikki += d["data"]
    tulos = {"kausi": kausi, "nimet": {}, "runko": {}, "kaikki": {}}
    for nimi, P in (("runko", vaiheet.get(1, {})), ("kaikki", pelaajat(rivit_kaikki))):
        for pid, s in P.items():
            tulos[nimi][pid] = [lyh.get(s["joukkue"], "?")] + [s[k] for k in KENTAT]
            tulos["nimet"][pid] = nimet.get(pid, "")
    return tulos, kuvat, {k: v for k, v in logot.items() if k and v}

def _tulos(t):
    import re
    h = t.split()[0].lower(); lisa = h[-1] if h[-1] in "sk" else ""
    a, b = map(int, re.sub("[sk]", "", h).split("-")); return a, b, lisa

def _pisteet(a, b, lisa):
    return (2, 1) if lisa else ((3, 0) if max(a, b) == 2 else (2, 0))

def sijoitukset(ott, lyh):
    """Pudotuspelien sijoitus joukkueittain: Mestari, Hopea, Pronssi, 4., Puolivälierä, 1. kierros; vaihe 3 = Karsinnat."""
    import collections
    g = collections.defaultdict(list)
    for m in ott:
        if m.get("vaihe") in (2, 3) and m.get("tulos"):
            g[(m["vaihe"], frozenset([m["koti"], m["vieras"]]))].append(m)
    sarjat = []
    for (v, pari), ms in g.items():
        w = collections.Counter()
        for m in ms:
            a, b, _ = _tulos(m["tulos"]); w[m["koti"] if a > b else m["vieras"]] += 1
        x, y = sorted(pari, key=lambda t: -w[t])
        sarjat.append({"v": v, "voittaja": x, "haviaja": y, "alku": min(m["pvm"] for m in ms), "loppu": max(m["pvm"] for m in ms)})
    tulos = {}
    for s in sarjat:
        if s["v"] == 3:
            for t in (s["voittaja"], s["haviaja"]): tulos.setdefault(lyh.get(t), "Karsinnat")
    po = [s for s in sarjat if s["v"] == 2]
    if not po:
        return tulos
    for s in po:
        for t in (s["voittaja"], s["haviaja"]): tulos[lyh.get(t)] = "1. kierros"
    fin = max(po, key=lambda s: s["loppu"])
    def edellinen(t, ennen):
        c = [s for s in po if s["voittaja"] == t and s["loppu"] < ennen["alku"]]
        return max(c, key=lambda s: s["loppu"]) if c else None
    tulos[lyh.get(fin["voittaja"])] = "Mestari"; tulos[lyh.get(fin["haviaja"])] = "Hopea"
    semit = [x for x in (edellinen(fin["voittaja"], fin), edellinen(fin["haviaja"], fin)) if x]
    semihav = {s["haviaja"] for s in semit}
    pr = [s for s in po if {s["voittaja"], s["haviaja"]} == semihav]
    if pr:
        tulos[lyh.get(pr[0]["voittaja"])] = "Pronssi"; tulos[lyh.get(pr[0]["haviaja"])] = "4."
    else:
        for t in semihav: tulos[lyh.get(t)] = "Välierä"
    for s in semit:
        for t in (s["voittaja"], s["haviaja"]):
            q = edellinen(t, s)
            if q and tulos.get(lyh.get(q["haviaja"])) == "1. kierros":
                tulos[lyh.get(q["haviaja"])] = "Puolivälierä"
    return tulos

def hae_joukkueet(kausi):
    ss = kaudet.MSU[kausi]
    ott, maps = haku.ottelut(ss)
    lyh = {t["id"]: t["value"].get("shorthand") for t in maps.get("team", [])}
    ott = [{"koti": o["home"], "vieras": o["away"], "vaihe": o["series"]["phase"], "pvm": o["date"],
            "tulos": (o.get("result") or {}).get("result_string")} for o in ott if not o.get("canceled")]
    import collections
    S = collections.defaultdict(lambda: {"O": 0, "V": 0, "H": 0, "P": 0})
    for m in ott:
        if m["vaihe"] != 1 or not m["tulos"]:
            continue
        a, b, lisa = _tulos(m["tulos"])
        w, l = (m["koti"], m["vieras"]) if a > b else (m["vieras"], m["koti"])
        pw, pl = _pisteet(a, b, lisa)
        for t, v, p in ((w, 1, pw), (l, 0, pl)):
            S[t]["O"] += 1; S[t]["V"] += v; S[t]["H"] += 1 - v; S[t]["P"] += p
    J = joukkueet(haku.joukkueet_otteluittain(ss, 1).get("data", []))
    jarj = sorted(S, key=lambda t: (-S[t]["P"], -S[t]["V"]))
    po = sijoitukset(ott, lyh)
    tulos = {}
    for i, t in enumerate(jarj):
        j = J.get(t, {})
        tulos[lyh.get(t)] = {"sija": i + 1, **S[t], "juoksut": j.get("runs"), "paastetyt": j.get("runs_opponent"),
                             "kotiutus": j.get("kotiutus%"), "torjunta": j.get("torjunta%"), "KL%": j.get("KL%"),
                             "pudotus": po.get(lyh.get(t), "–")}
    for k, v in po.items():
        if k and k not in tulos:
            tulos[k] = {"sija": None, "pudotus": v}
    return {"kausi": kausi, "joukkueet": tulos}

def main():
    os.makedirs(OUT, exist_ok=True)
    kp = _polku("kuvat.json")
    kaikki_kuvat = json.load(open(kp, encoding="utf-8")) if os.path.exists(kp) else {"pelaajat": {}, "logot": {}}
    for kausi in sorted(kaudet.MSU):
        tied = _polku(f"historia_{kausi}.json")
        if kausi != KULUVA and os.path.exists(tied):
            continue
        tulos, kuvat, logot = hae_kausi(kausi)
        json.dump(tulos, open(tied, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        # uudemman kauden kuva/logo voittaa
        kaikki_kuvat["pelaajat"].update({str(k): v for k, v in kuvat.items()})
        kaikki_kuvat["logot"].update(logot)
        print(kausi, "runko", len(tulos["runko"]), "kaikki", len(tulos["kaikki"]), "kuvia", len(kuvat))
    json.dump(kaikki_kuvat, open(kp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    for kausi in sorted(kaudet.MSU):
        tied = _polku(f"joukkuehistoria_{kausi}.json")
        if kausi != KULUVA and os.path.exists(tied):
            continue
        d = hae_joukkueet(kausi)
        json.dump(d, open(tied, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(kausi, "joukkueet", {k: (v.get("sija"), v.get("pudotus")) for k, v in d["joukkueet"].items()})

if __name__ == "__main__":
    main()
