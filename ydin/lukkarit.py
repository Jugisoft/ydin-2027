"""Lukkaritilastot ottelutason datasta (stats-tool, ei lyöntikohtaista tapahtumadataa).

Pelaajarivien `defensive_position` kertoo, kuka pelasi ottelussa lukkarina ("L", tasan yksi per joukkue per ottelu,
ottelun kokoonpanon mukaan). Lukkarille kohdistetaan hänen joukkueensa ottelukohtaiset puolustusluvut eli vastustajan
kotiutusluvut (`*_opponent`). Kesken ottelun tehdyt lukkarivaihdot eivät näy datassa.

Tapahtumadatasta (6.11.2026, data/tapahtumat/<kausi>/, ei uusia hakuja) lasketaan lisäksi lukkarin joukkueen
puolustusvuorojen vapaat (väärien syöttöjen vapaataipaleet, kohdepesän mukaan) ja kärpäset. Vain varsinaiset jaksot
(1. ja 2. jakso), ei supervuoroa eikä kotiutuslyöntikilpailua. Kaudet ilman tapahtumadataa: kentät null.
Huom: stats-toolin `walks`-kenttä EI ole vapaat (koko kaudella vain 0–3 per joukkue).

python -m ydin.lukkarit  -> data/out/lukkarit_{kausi}.json (päättyneet kaudet haetaan vain kerran)
Rivi: ks. KENTAT."""
import glob, gzip, json, os
from . import haku, kaudet

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")
KULUVA = max(kaudet.MSU)
KENTAT = ["ottelu", "pvm", "vaihe", "lukkari", "jk", "vs", "koti", "voitto", "jaksot", "jaksot_v",
          "juoksut_v", "j1_v", "j2_v", "juoksut",
          "KL_v", "KLY_v", "KL0_v", "KLY0_v", "KL1_v", "KLY1_v", "KL2_v", "KLY2_v", "KL3_v", "KLY3_v",
          "kolmos_v", "K_v",
          "vapaat", "vapaat1", "vapaat23", "vapaatK", "karpaset_l", "karpaset",
          "P0_v", "P1_v", "P2_v", "P3_v", "H0_v", "H1_v", "H2_v", "H3_v"]
TKENTAT = KENTAT[-14:-8]   # tapahtumadatasta; null jos ottelun tapahtumia ei ole
# Vastustajan kärkietenijän palot (P) ja haavat (H) lähtöpesän mukaan: stats-toolin pelaajarivit (batpe_outs_n,
# batpe_caughts_n) summattuna vastustajan lyöjiltä (6.11.2026). Null, jos kauden ottelurivejä ei ole tallessa.
VKENTAT = KENTAT[-8:]
TAPAHTUMAT = os.path.join(os.path.dirname(__file__), "..", "data", "tapahtumat")
KOHDE = {"ykköspesälle": 1, "kakkospesälle": 23, "kolmospesälle": 23, "kotipesään": "K"}

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

def tapahtumaluvut(d):
    """Yhden ottelun tapahtumista: {puolustava team_id: [vapaat, vapaat1, vapaat23, vapaatK, karpaset_l, karpaset]}.
    Vapaa = "sai vapaataipaleen väärien syöttöjen johdosta" (kohde = pesä, jolle etenijä sai vapaan; kotipesään = juoksu).
    Kärpänen = "paloi kärpäsenä…", lukkarin kärpäset erikseen ("…lukkarin toimesta")."""
    joukkueet = {g["team"] for g in d.get("events") or [] if g.get("team")}
    out = {t: [0] * 6 for t in joukkueet}
    for g in d.get("events") or []:
        if g.get("period") not in (0, 1) or g.get("team") not in joukkueet:
            continue
        puol = next((t for t in joukkueet if t != g["team"]), None)
        if puol is None:
            continue
        for e in g.get("events") or []:
            tx = e.get("texts") or []
            for t in tx:
                if not (isinstance(t, dict) and t.get("type") == "event"):
                    continue
                teksti = t.get("text") or ""
                if teksti.startswith("sai vapaataipaleen väärien"):
                    r = out[puol]; r[0] += 1
                    k = next((KOHDE[x] for x in tx if isinstance(x, str) and x in KOHDE), None)
                    if k == 1: r[1] += 1
                    elif k == 23: r[2] += 1
                    elif k == "K": r[3] += 1
                elif teksti.startswith("paloi kärpäsenä"):
                    out[puol][5] += 1
                    if "lukkarin" in teksti:
                        out[puol][4] += 1
    return out

def rikasta(rivit, kausi, lyh_id):
    """Lisää tapahtumakentät riveihin (ottelu + lukkarin joukkue). lyh_id: {lyhenne: team_id}."""
    kansio = os.path.join(TAPAHTUMAT, str(kausi))
    luvut = {}
    for f in glob.glob(os.path.join(kansio, "*.json.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as h:
            luvut[int(os.path.basename(f).split(".")[0])] = tapahtumaluvut(json.load(h))
    n = len(KENTAT) - len(TKENTAT) - len(VKENTAT)
    vir = viralliset(kausi)
    for r in rivit:
        del r[n:]
        t = luvut.get(r[0], {}).get(lyh_id.get(r[4]))
        r.extend(t if t is not None else [None] * len(TKENTAT))
        v = vir.get((r[0], lyh_id.get(r[5])))   # vastustajan lyöjät
        r.extend(v if v is not None else [None] * len(VKENTAT))
    return sum(1 for r in rivit if r[n] is not None)

def viralliset(kausi):
    """{(ottelu, lyövä team_id): [palot0–3, haavat0–3]} stats-toolin ottelukohtaisista pelaajariveistä."""
    out = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        p = os.path.join(OUT, f"otteluittain_{kausi}_{ph}.json")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for r in json.load(f)["pelaajat"]:
                a = out.setdefault((r["match_id"], r["team_id"]), [0] * 8)
                for n in range(4):
                    a[n] += _i(r.get(f"batpe_outs_{n}")); a[4 + n] += _i(r.get(f"batpe_caughts_{n}"))
    return out

def _lyh_id(kausi):
    m = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        p = os.path.join(OUT, f"joukkueet_{kausi}_{ph}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                m.update({t["lyhenne"]: t["id"] for t in json.load(f)})
    return m

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
            with open(tied, encoding="utf-8") as f:
                d = json.load(f)   # päättynyttä kautta ei haeta uudelleen; tapahtumakentät lasketaan tallessa olevista tapahtumista
        else:
            d = hae_kausi(kausi)
        d["kentat"] = KENTAT
        tap = rikasta(d["rivit"], kausi, _lyh_id(kausi))
        with open(tied, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        print(kausi, "lukkaririvejä", len(d["rivit"]), "lukkareita", len(d["nimet"]), "tapahtumista", tap)

if __name__ == "__main__":
    main()
