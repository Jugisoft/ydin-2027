"""Ottelun kulku (6.11.2026): juoksut vuoroittain ja ottelun ratkeamistapa → data/out/kulku_<kausi>.json (+ .csv).
python -m ydin.kulku [--kausi 2026]

Lähde: tallessa olevat ottelutapahtumat (data/tapahtumat/<kausi>/, ei uusia hakuja) ja otteluluettelon tulos.
Juoksu = tilastomerkintä score / homerun / wtscore / walkscore (1 kpl); kotiutuslyöntikilpailussa oscscore (arvo = juoksut).
Jakso 0 = 1. jakso, 1 = 2. jakso, 2 = supervuoro, 3 = kotiutuslyöntikilpailu; vuoro (inning) 0–3 jakson sisällä.
Tarkistus: jaksojen summat täsmäävät stats-toolin runs_p0–runs_p3-kenttiin joka ottelussa (ks. tarkista())."""
import argparse, collections, csv, gzip, json, os, re
from . import kaudet
from .tapahtumat import JUURI

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")
JUOKSU = ("score", "homerun", "wtscore", "walkscore")
TAVAT = ["2–0", "1–0", "supervuoro", "kotiutus"]   # ratkeamistapa
KENTAT = ["ottelu", "pvm", "vaihe", "koti", "vieras", "tulos", "tapa", "voittaja",
          "koti_vuorot", "vieras_vuorot", "koti_sv", "vieras_sv", "koti_klk", "vieras_klk"]

def juoksut(d):
    """{team_id: {"v": [8 vuoroa: jakso1 v1–4, jakso2 v1–4], "sv": supervuoro, "klk": kotiutuskilpailu}}"""
    out = collections.defaultdict(lambda: {"v": [0] * 8, "sv": 0, "klk": 0})
    for g in d.get("events") or []:
        t, p, i = g.get("team"), g.get("period"), g.get("inning")
        if t is None or p is None:
            continue
        o = out[t]
        for e in g.get("events") or []:
            for x in e.get("texts") or []:
                if not (isinstance(x, dict) and x.get("type") == "stat"):
                    continue
                if p == 3:
                    o["klk"] += int(x.get("oscscore") or 0)
                    continue
                n = sum(1 for k in JUOKSU if k in x)
                if not n:
                    continue
                if p in (0, 1) and i is not None and 0 <= i <= 3:
                    o["v"][p * 4 + i] += n
                elif p == 2:
                    o["sv"] += n
    return out

def tapa(tulos):
    """'1-2k (7-2, 3-4, 1-2k)' -> ('kotiutus', voittaja 'k'/'v')"""
    h = tulos.split()[0].lower()
    a, b = map(int, re.sub("[sk]", "", h).split("-"))
    w = "k" if a > b else "v"
    if h.endswith("k"): return "kotiutus", w
    if h.endswith("s"): return "supervuoro", w
    return ("2–0" if max(a, b) == 2 else "1–0"), w

def rivit(kausi):
    ott = json.load(open(os.path.join(OUT, f"ottelut_{kausi}.json"), encoding="utf-8"))
    kansio = os.path.join(JUURI, str(kausi))
    R = []
    for m in sorted(ott, key=lambda m: m["pvm"]):
        p = os.path.join(kansio, f"{m['id']}.json.gz")
        if not m.get("tulos") or m.get("vaihe") not in (1, 2, 3) or not os.path.exists(p):
            continue
        with gzip.open(p, "rt", encoding="utf-8") as f:
            j = juoksut(json.load(f))
        k, v = j[m["koti"]], j[m["vieras"]]
        tp, w = tapa(m["tulos"])
        R.append([m["id"], m["pvm"][:10], m["vaihe"], m["koti"], m["vieras"], m["tulos"], tp, w,
                  k["v"], v["v"], k["sv"], v["sv"], k["klk"], v["klk"]])
    return R

def tarkista(R, kausi):
    """Vertaa jaksojen juoksuja stats-toolin otteluriveihin. -> (täsmää, verrattu)"""
    vir = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        p = os.path.join(OUT, f"otteluittain_{kausi}_{ph}.json")
        if os.path.exists(p):
            for r in json.load(open(p, encoding="utf-8"))["joukkueet"]:
                vir[(r["match_id"], r["team_id"])] = [int(r.get(f"runs_p{n}") or 0) for n in range(4)]
    ok = n = 0
    for r in R:
        for t, vv, sv, klk in ((r[3], r[8], r[10], r[12]), (r[4], r[9], r[11], r[13])):
            if (r[0], t) not in vir:
                continue
            n += 1; ok += [sum(vv[:4]), sum(vv[4:]), sv, klk] == vir[(r[0], t)]
    return ok, n

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kausi", type=int); a = ap.parse_args()
    kausi = a.kausi or kaudet.uusin()
    if not os.path.isdir(os.path.join(JUURI, str(kausi))):
        print(f"Ei tapahtumia kaudelta {kausi}"); return
    R = rivit(kausi)
    ok, n = tarkista(R, kausi)
    with open(os.path.join(OUT, f"kulku_{kausi}.json"), "w", encoding="utf-8") as f:
        json.dump({"kausi": kausi, "kentat": KENTAT, "tavat": TAVAT, "tarkistus": {"tasmaa": ok, "verrattu": n},
                   "rivit": R}, f, ensure_ascii=False, separators=(",", ":"))
    lyh = {}
    for ph in ("runko", "jatko_ylempi", "jatko_alempi"):
        p = os.path.join(OUT, f"joukkueet_{kausi}_{ph}.json")
        if os.path.exists(p):
            lyh.update({t["id"]: t["lyhenne"] for t in json.load(open(p, encoding="utf-8"))})
    with open(os.path.join(OUT, f"kulku_{kausi}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ottelu", "pvm", "vaihe", "joukkue", "vastustaja", "koti", "tulos", "ratkeamistapa", "voitto"] +
                   [f"j{j}v{v}" for j in (1, 2) for v in range(1, 5)] + ["jakso1", "jakso2", "supervuoro", "kotiutuskilpailu",
                   "paastetyt_jakso1", "paastetyt_jakso2"] + [f"paastetyt_j{j}v{v}" for j in (1, 2) for v in range(1, 5)])
        for r in R:
            for koti in (1, 0):
                o, v = (8, 9) if koti else (9, 8)
                t, vs = (r[3], r[4]) if koti else (r[4], r[3])
                voitto = int((r[7] == "k") == bool(koti))
                w.writerow([r[0], r[1], r[2], lyh.get(t, t), lyh.get(vs, vs), koti, r[5], r[6], voitto] + r[o] +
                           [sum(r[o][:4]), sum(r[o][4:]), r[10 if koti else 11], r[12 if koti else 13],
                            sum(r[v][:4]), sum(r[v][4:])] + r[v])
    print(json.dumps({"kausi": kausi, "otteluita": len(R), "jaksojen_juoksut_tasmaa": f"{ok}/{n}"}))

if __name__ == "__main__":
    main()
