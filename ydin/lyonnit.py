"""Lyöntikartat ottelutapahtumista → data/out/lyonnit_<kausi>/ (KPL Keskus lukee nämä GitHubista).
python -m ydin.lyonnit [--kausi 2027]

Koordinaatit: pesistulokset antaa lyönnin kohdan prosentteina kenttäkuvasta (x 0–100 vasemmalta, y 0 = takana).
Kalibrointi kauden 2026 67 800 lyönnistä: sivurajat x≈10/90 (42 m), takaraja y≈4,5, kotipesä y≈95
→ x_m = (x − 50) · 0,525, y_m = (95 − y) · 1,06. (0,0) = kohta puuttuu → pois.
Tulos (prioriteetti): kunnari, juoksu, laiton, koppi, palo, haava, eteni (kärkilyönti onnistui), ei_edennyt, muu.
Tilanne = kenttäpesien etenijät lyöntihetkellä. Palot = vuoroparin palot ennen lyöntiä. Vaihe 0 = runkosarja, 1 = muut."""
import argparse, collections, json, os
from . import kaudet
from .tapahtumat import JUURI, lue

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "out")
TIL = ["0", "1", "2", "3", "1–2", "1–3", "2–3", "1–2–3"]
TUL = ["kunnari", "juoksu", "laiton", "koppi", "palo", "haava", "eteni", "ei_edennyt", "muu"]
RUN = ("score", "wtscore", "walkscore")

def tila(r):
    p = [str(i) for i in (1, 2, 3) if len(r) > i and r[i] is not None]
    return "0" if not p else "–".join(p)

def osat(g):
    tx = [t for s in g.get("events") or [] for t in s.get("texts") or []]
    ty = [t.get("type") for t in tx if isinstance(t, dict)]
    te = [t.get("text", "") for t in tx if isinstance(t, dict) and t.get("type") == "event"]
    st = [k for t in tx if isinstance(t, dict) and t.get("type") == "stat" for k in t if k != "type"]
    return ty, te, st

def tulos(ty, te, st):
    if "homerun" in st: return "kunnari"
    if any(k in st for k in RUN): return "juoksu"
    if "hit-out" in ty: return "laiton"
    if "hit-caught" in ty: return "koppi"
    if any(x.startswith("palo") for x in te): return "palo"
    if any(x.startswith("haav") for x in te): return "haava"
    if "pointhits" in st: return "eteni"
    if "pointhitf" in st: return "ei_edennyt"
    return "muu"

def ottelun_lyonnit(d, vaihe):
    """[(lyöjä, joukkue, [x, y, tilanne, palot, lyönti, tulos, vaihe])] – vain jaksot 1–2."""
    palot, out = collections.Counter(), []
    for g in d.get("events") or []:
        if g.get("period") not in (0, 1) or g.get("team") is None or g.get("inning") is None: continue
        k = (g["period"], g["inning"], g["team"])
        ty, te, st = osat(g)
        h = g.get("hit")
        if h and h.get("batter_player_id") and h.get("x") not in (None, ""):
            x, y = float(h["x"]), float(h["y"])
            if not (x == 0 and y == 0):
                r = ((g.get("events") or [{}])[0].get("runnersAtBases")) or []
                out.append((h["batter_player_id"], g["team"], [round((x - 50) * 0.525, 1), round((95 - y) * 1.06, 1),
                    TIL.index(tila(r)), min(palot[k], 2), g.get("hitNumber") or 0, TUL.index(tulos(ty, te, st)), vaihe]))
        palot[k] += sum(1 for s in st if s == "out")
    return out

def _lue_json(nimi, oletus):
    p = os.path.join(OUT, nimi)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else oletus

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kausi", type=int); a = ap.parse_args()
    kausi = a.kausi or kaudet.uusin()
    kansio = os.path.join(JUURI, str(kausi))
    if not os.path.isdir(kansio): print(f"Ei tapahtumia kaudelta {kausi}"); return
    vaiheet = {o["id"]: o.get("vaihe") for o in _lue_json(f"ottelut_{kausi}.json", [])}
    nimet, lyh = {}, {}
    for v in ("runko", "jatko_ylempi", "jatko_alempi"):
        for p in _lue_json(f"pelaajat_{kausi}_{v}.json", []): nimet.setdefault(p["id"], " ".join((p.get("nimi") or "").split()))
        for j in _lue_json(f"joukkueet_{kausi}_{v}.json", []): lyh[j["id"]] = j.get("lyhenne")
    P = collections.defaultdict(list); J = collections.defaultdict(collections.Counter)
    for f in sorted(os.listdir(kansio)):
        mid = int(f.split(".")[0])
        if vaiheet.get(mid) == 4: continue                      # Itä–Länsi
        vaihe = 0 if vaiheet.get(mid) in (None, 1) else 1
        for pid, tid, rivi in ottelun_lyonnit(lue(kausi, mid), vaihe):
            P[pid].append(rivi); J[pid][tid] += 1
    kohde = os.path.join(OUT, f"lyonnit_{kausi}"); os.makedirs(kohde, exist_ok=True)
    hakemisto = []
    for pid, l in P.items():
        if not nimet.get(pid): continue
        jl = lyh.get(J[pid].most_common(1)[0][0])
        hakemisto.append({"id": pid, "nimi": nimet[pid], "joukkue": jl, "n": len(l)})
        with open(os.path.join(kohde, f"p{pid}.json"), "w", encoding="utf-8") as fh:
            json.dump({"id": pid, "nimi": nimet[pid], "joukkue": jl, "kentat": ["x", "y", "tilanne", "palot", "lyonti", "tulos", "vaihe"], "l": l}, fh, ensure_ascii=False, separators=(",", ":"))
    hakemisto.sort(key=lambda r: (r["joukkue"] or "", r["nimi"]))
    meta = {"kausi": kausi, "tilanteet": TIL, "tulokset": TUL, "pelaajat": hakemisto, "otteluita": len(os.listdir(kansio)),
            "lahde": f"pesistulokset.fi ottelutapahtumat {kausi}", "kalibrointi": "x_m=(x-50)*0.525, y_m=(95-y)*1.06"}
    with open(os.path.join(kohde, "hakemisto.json"), "w", encoding="utf-8") as fh: json.dump(meta, fh, ensure_ascii=False, indent=0)
    print(json.dumps({"kausi": kausi, "pelaajia": len(hakemisto), "lyonteja": sum(r["n"] for r in hakemisto)}))

if __name__ == "__main__":
    main()
