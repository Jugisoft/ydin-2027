"""Pelaajien kausihistoria (Superpesis 2023–), pelaajakuvat ja seuralogot.
python -m ydin.historia  -> data/out/historia_{kausi}.json + data/out/kuvat.json
Päättyneet kaudet haetaan vain kerran (tiedosto jää välimuistiksi); kuluva kausi päivitetään joka ajolla.
Kuvat ja logot ovat pesistulokset.fi:n palvelimella; sivu näyttää ne sieltä lähteen kanssa."""
import json, os
from . import haku, kaudet
from .mittarit import pelaajat

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

if __name__ == "__main__":
    main()
