"""Koko putki: python -m ydin.paivita --kausi 2026
Hakee otteluluettelon + ottelukohtaiset pelaaja- ja joukkuetilastot (stats-tool) ja kirjoittaa data/out/."""
import argparse, datetime, json, os
from . import haku, kaudet
from .mittarit import pelaajat, joukkueet, PELAAJA_SUMMAT, JOUKKUE_SUMMAT

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")
VAIHEET = {1: "runko", 2: "jatko_ylempi", 3: "jatko_alempi"}

def _kirjoita(nimi, data):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, nimi), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":") if nimi.startswith("otteluittain") else None, indent=None if nimi.startswith("otteluittain") else 1, sort_keys=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kausi", type=int, default=2026); a = ap.parse_args()
    ss = kaudet.MSU[a.kausi]
    ott, maps = haku.ottelut(ss)
    tiimit = {t["id"]: {"nimi": t["value"].get("name"), "lyhenne": t["value"].get("shorthand")} for t in maps.get("team", [])}
    ottelut = [{"id": o["id"], "pvm": o["date"], "koti": o["home"], "vieras": o["away"], "vaihe": o["series"]["phase"],
                "tulos": (o.get("result") or {}).get("result_string")} for o in ott if not o.get("canceled")]
    pelaajanimet, yht = {}, {"kausi": a.kausi, "seasonSeries": ss, "paivitetty": datetime.datetime.now().isoformat(timespec="minutes")}
    for ph, nimi in VAIHEET.items():
        if not any(o["vaihe"] == ph and o["tulos"] for o in ottelut): continue
        pr = haku.pelaajat_otteluittain(ss, ph); tr = haku.joukkueet_otteluittain(ss, ph)
        for p in (pr.get("maps") or {}).get("player", []):
            v = p["value"]; pelaajanimet[p["id"]] = v.get("name") or f"{v.get('first_name','')} {v.get('last_name','')}".strip()
        P, J = pelaajat(pr["data"]), joukkueet(tr["data"])
        _kirjoita(f"pelaajat_{a.kausi}_{nimi}.json", [{"id": k, "nimi": pelaajanimet.get(k), **v} for k, v in P.items()])
        _kirjoita(f"joukkueet_{a.kausi}_{nimi}.json", [{"id": k, **tiimit.get(k, {}), **v} for k, v in J.items()])
        pk = ["match_id", "player_id", "team_id", "opponent_team_id", "is_home", "matches", "won"] + PELAAJA_SUMMAT
        jk = ["match_id", "team_id", "opponent_team_id", "is_home", "won"] + JOUKKUE_SUMMAT
        _kirjoita(f"otteluittain_{a.kausi}_{nimi}.json", {
            "pelaajat": [{k: r.get(k) for k in pk} for r in pr["data"]],
            "joukkueet": [{k: r.get(k) for k in jk} for r in tr["data"]]})
        yht[f"rivit_{nimi}"] = {"pelaaja_ottelut": len(pr["data"]), "joukkue_ottelut": len(tr["data"])}
    _kirjoita(f"ottelut_{a.kausi}.json", ottelut); _kirjoita(f"meta_{a.kausi}.json", yht)
    print(json.dumps(yht, ensure_ascii=False))

if __name__ == "__main__":
    main()
