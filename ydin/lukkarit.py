"""Lukkaritilastot ottelutason datasta (stats-tool, ei lyöntikohtaista tapahtumadataa).

Pelaajarivien `defensive_position` kertoo, kuka pelasi ottelussa lukkarina ("L", tasan yksi per joukkue per ottelu,
ottelun kokoonpanon mukaan). Lukkarille kohdistetaan hänen joukkueensa ottelukohtaiset puolustusluvut eli vastustajan
kotiutusluvut (`*_opponent`). Kesken ottelun tehdyt lukkarivaihdot eivät näy datassa.

Ei saatavilla ilman tapahtumadataa: lukkarin vapaat (väärät syötöt) ja kärpäset. Huom: stats-toolin `walks`-kenttä
EI ole vapaat (koko kaudella vain 0–3 per joukkue).

python -m ydin.lukkarit  -> data/out/lukkarit_{kausi}.json (päättyneet kaudet haetaan vain kerran)
Rivi: ks. KENTAT."""
import json, os
from . import haku, kaudet

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")
KULUVA = max(kaudet.MSU)
KENTAT = ["ottelu", "pvm", "vaihe", "lukkari", "jk", "vs", "koti", "voitto", "jaksot", "jaksot_v",
          "juoksut_v", "j1_v", "j2_v", "juoksut",
          "KL_v", "KLY_v", "KL0_v", "KLY0_v", "KL1_v", "KLY1_v", "KL2_v", "KLY2_v", "KL3_v", "KLY3_v",
          "kolmos_v", "K_v"]

def _i(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0

def rivit_kaudelta(ottelut, lyh, pelaajarivit, joukkuerivit):
    """ottelut: {match_id: {"pvm", "vaihe"}} ; pelaajarivit/joukkuerivit: stats-tool otteluittain (ei summattu)."""
    L = {}
    for r in pelaajarivit:
        if r.get("defensive_position") == "L":
            L[(r["match_id"], r["team_id"])] = r["player_id"]
    out = []
    for r in joukkuerivit:
        m = ottelut.get(r["match_id"]); lk = L.get((r["match_id"], r["team_id"]))
        if not m or lk is None:
            continue
        out.append([r["match_id"], m["pvm"][:10], m["vaihe"], lk, lyh.get(r["team_id"], "?"), lyh.get(r["opponent_team_id"], "?"),
                    _i(r.get("is_home")), _i(r.get("won")), _i(r.get("periods")), _i(r.get("periods_opponent")),
                    _i(r.get("runs_opponent")), _i(r.get("runs_p0_opponent")), _i(r.get("runs_p1_opponent")), _i(r.get("runs")),
                    _i(r.get("pe_total_opponent")), _i(r.get("pe_tries_total_opponent"))] +
                   [_i(r.get(f"pe_{x}_b{n}_opponent")) for n in range(4) for x in ("total", "tries")] +
                   [_i(r.get("rab3_opponent")), _i(r.get("homeruns_opponent"))])
    out.sort(key=lambda x: (x[1], x[0]))
    return out

def hae_kausi(kausi):
    ss = kaudet.MSU[kausi]
    ott, maps = haku.ottelut(ss)
    lyh = {t["id"]: t["value"].get("shorthand") for t in maps.get("team", [])}
    ottelut = {o["id"]: {"pvm": o["date"], "vaihe": o["series"]["phase"]} for o in ott
               if not o.get("canceled") and o["series"]["phase"] in (1, 2, 3)}
    P, J, nimet = [], [], {}
    for ph in (1, 2, 3):
        if not any(o["vaihe"] == ph for o in ottelut.values()):
            continue
        pr = haku.pelaajat_otteluittain(ss, ph)
        if not pr.get("data"):
            continue
        P += pr["data"]; J += haku.joukkueet_otteluittain(ss, ph).get("data", [])
        for p in (pr.get("maps") or {}).get("player", []):
            v = p["value"]; nimet[p["id"]] = v.get("name") or f"{v.get('first_name','')} {v.get('last_name','')}".strip()
    rivit = rivit_kaudelta(ottelut, lyh, P, J)
    return {"kausi": kausi, "kentat": KENTAT, "rivit": rivit, "nimet": {str(r[3]): nimet.get(r[3], "?") for r in rivit}}

def main():
    os.makedirs(OUT, exist_ok=True)
    for kausi in sorted(k for k in kaudet.MSU if k >= 2023):
        tied = os.path.join(OUT, f"lukkarit_{kausi}.json")
        if kausi != KULUVA and os.path.exists(tied):
            continue
        d = hae_kausi(kausi)
        with open(tied, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        print(kausi, "lukkaririvejä", len(d["rivit"]), "lukkareita", len(d["nimet"]))

if __name__ == "__main__":
    main()
