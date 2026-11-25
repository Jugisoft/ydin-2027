"""Miesten Talvisuper: otteluohjelma, tulokset ja lohkotaulukot → data/out/talvi_<kausi>.json.
Yksi hakupyyntö (otteluluettelo). Jugi 25.11.2026: talvisuperin aikataulu YDINiin ja KPL Keskukseen.
Ajo: python -m ydin.talvi [--kausi 2027]"""
import argparse, collections, datetime, json, os
from . import haku, kaudet

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")


def _jaksot(r):
    """-> (koti_jaksot, vieras_jaksot, lisä '' / 's' / 'k', koti_juoksut, vieras_juoksut) tai None."""
    if not r or not r.get("result_string"):
        return None
    h = r["result_string"].split()[0].lower()
    lisa = h[-1] if h[-1] in "sk" else ""
    a, b = map(int, h.rstrip("sk").split("-"))
    jk = sum(r.get(k) or 0 for k in ("runs_home_first_period", "runs_home_second_period"))
    jv = sum(r.get(k) or 0 for k in ("runs_away_first_period", "runs_away_second_period"))
    return a, b, lisa, jk, jv


def muodosta(rivit, maps, kausi, ss):
    tiimit = {t["id"]: t["value"] for t in maps.get("team", [])}
    lohkot = {g["id"]: g["value"]["name"] for g in maps.get("group", [])}
    vaiheet = {p["id"]: p["value"]["name"] for p in maps.get("phase", [])}
    lyh = lambda i: (tiimit.get(i) or {}).get("shorthand") or "?"
    ottelut, taulu = [], collections.defaultdict(lambda: collections.defaultdict(lambda: {"O": 0, "V": 0, "H": 0, "JV": 0, "JH": 0, "J": 0}))
    for m in sorted(rivit, key=lambda m: (m["date"] or "", m["id"])):
        if m.get("canceled") or m.get("invalidated"):
            continue
        s = m.get("series") or {}
        lohko = lohkot.get(s.get("group"), "")
        t = _jaksot(m.get("result"))
        ottelut.append({"id": m["id"], "pvm": m["date"], "tba": bool(m.get("date_tba")), "vaihe": vaiheet.get(s.get("phase"), ""),
                        "lohko": lohko, "koti": lyh(m["home"]), "vieras": lyh(m["away"]),
                        "halli": (m.get("stadium") or {}).get("name"), "tulos": (m.get("result") or {}).get("result_string")})
        if lohko.lower().startswith("lohko"):
            for jkid in (m["home"], m["away"]):
                taulu[lohko][lyh(jkid)]  # joukkue taulukkoon jo ennen ensimmäistä ottelua
        if t and lohko.lower().startswith("lohko"):  # taulukkoon vain alkulohkojen ottelut
            a, b, lisa, jk, jv = t
            for jkid, omat_j, vast_j, omat_r, vast_r in ((m["home"], a, b, jk, jv), (m["away"], b, a, jv, jk)):
                x = taulu[lohko][lyh(jkid)]
                x["O"] += 1; x["JV"] += omat_j; x["JH"] += vast_j; x["J"] += omat_r - vast_r
                # Talvisuperin pistelaskua ei ole varmistettu, joten taulukko järjestetään voittojen mukaan (ei pisteitä).
                x["V" if omat_j > vast_j else "H"] += 1
    taulukot = {l: sorted(({"jk": k, **v} for k, v in d.items()), key=lambda r: (-r["V"], -(r["JV"] - r["JH"]), -r["J"], r["jk"]))
                for l, d in sorted(taulu.items()) if l}
    logot = {lyh(i): v.get("icon") or (v.get("sport_club") or {}).get("icon") for i, v in tiimit.items()}
    return {"kausi": kausi, "seasonSeries": ss, "paivitetty": datetime.datetime.now().isoformat(timespec="minutes"),
            "ottelut": ottelut, "taulukot": taulukot, "logot": {k: v for k, v in logot.items() if v}}


def uusin():
    return max(kaudet.TALVI)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kausi", type=int, default=uusin()); a = ap.parse_args()
    ss = kaudet.TALVI[a.kausi]
    rivit, maps = haku.ottelut(ss)
    d = muodosta(rivit, maps, a.kausi, ss)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"talvi_{a.kausi}.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Talvisuper {a.kausi}: {len(d['ottelut'])} ottelua, pelattu {sum(1 for o in d['ottelut'] if o['tulos'])}")


if __name__ == "__main__":
    main()
