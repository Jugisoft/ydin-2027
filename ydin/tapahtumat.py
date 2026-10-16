"""Iltaajo (klo 21.30 Suomen aikaa): uusien päättyneiden otteluiden tapahtumat → data/tapahtumat/<kausi>/<id>.json.gz
python -m ydin.tapahtumat [--kausi 2027] [--ottelu 147298] [--vain-klo 21]
Linjaus 16.10.2026: yksi haku per päättynyt ottelu, jo haettua ei haeta uudelleen."""
import argparse, datetime, gzip, json, os, sys
from zoneinfo import ZoneInfo
from . import haku, kaudet

JUURI = os.path.join(os.path.dirname(__file__), "..", "data", "tapahtumat")
ENINTAAN = 60   # hakuja yhdellä ajolla (normaali pelipäivä 5–6)

def polku(kausi, mid): return os.path.join(JUURI, str(kausi), f"{mid}.json.gz")

def tallenna(kausi, mid, d):
    os.makedirs(os.path.dirname(polku(kausi, mid)), exist_ok=True)
    with gzip.open(polku(kausi, mid), "wt", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, separators=(",", ":"))

def lue(kausi, mid):
    with gzip.open(polku(kausi, mid), "rt", encoding="utf-8") as f: return json.load(f)

def paattyneet(ottelut, nyt):
    """Ottelut, joilla on tulos ja alkuaika on mennyt."""
    return [o for o in ottelut if o.get("tulos") and o.get("pvm") and datetime.datetime.fromisoformat(o["pvm"].replace("Z", "+00:00")) < nyt]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kausi", type=int); ap.add_argument("--ottelu", type=int, action="append"); ap.add_argument("--vain-klo", type=int)
    a = ap.parse_args()
    nyt = datetime.datetime.now(datetime.timezone.utc)
    if a.vain_klo is not None and nyt.astimezone(ZoneInfo("Europe/Helsinki")).hour != a.vain_klo:
        print(f"Ei ajoa: Suomen aika ei ole klo {a.vain_klo}"); return
    kausi = a.kausi or kaudet.uusin()
    if a.ottelu: ids = a.ottelu
    else:
        if kausi not in kaudet.MSU: print(f"Kaudelle {kausi} ei ole sarjatunnistetta"); return
        ott, _ = haku.ottelut(kaudet.MSU[kausi])
        rivit = [{"id": o["id"], "pvm": o["date"], "tulos": (o.get("result") or {}).get("result_string")} for o in ott if not o.get("canceled")]
        ids = [o["id"] for o in paattyneet(rivit, nyt)]
    uudet = [m for m in ids if not os.path.exists(polku(kausi, m))][:ENINTAAN]
    haettu = 0
    for mid in uudet:
        d = haku.tapahtumat(mid)
        if not d.get("finished"): print(f"{mid}: ei vielä päättynyt, haetaan seuraavana iltana"); continue
        tallenna(kausi, mid, d); haettu += 1
    print(json.dumps({"kausi": kausi, "paattyneita": len(ids), "haettu": haettu, "tallessa": len(os.listdir(os.path.join(JUURI, str(kausi)))) if os.path.isdir(os.path.join(JUURI, str(kausi))) else 0}))

if __name__ == "__main__":
    main()
