"""Kenttien suunnat ja tuulihavainnot (19.11.2026).

Suunta = kotipesä → takarajan keskipiste asteina (0 = pohjoinen), Jugin taulukko 19.11.2026.
Meilahti (PuMu): ~10°, arvioitu Jugin karttakuvasta 19.11.2026 (kotipesä etelässä, takaraja pohjoisessa).
Puuttuu: Kannus (Ura) – lisää KENTAT-, SEURA-, NIMET- ja ASEMA-tauluihin, kun suunta tiedetään.

Tuuli: Ilmatieteen laitoksen avoin data (opendata.fmi.fi), lähimmän automaattiaseman tuntihavainnot
(WD_PT1H_AVG tulosuunta, WS_PT1H_AVG nopeus) ottelun alkutunnilta ja kahdelta seuraavalta, vektorikeskiarvona.
Myötätuuli = komponentti kotipesältä takarajalle päin (lyönnin suuntaan), m/s; negatiivinen = vastatuuli.
"""
import calendar, datetime, math, re, time, urllib.request

KENTAT = {"Sotkamo": 262, "Joensuu": 288, "Kempele": 300, "Kouvola": 295, "Koskenkorva": 295, "Kitee": 300,
          "Imatra": 315, "Pattijoki": 348, "Hyvinkää": 357, "Kauppi": 333, "Alajärvi": 75, "Vimpeli": 120, "Meilahti": 10}
SEURA = {"SoJy": "Sotkamo", "JoMa": "Joensuu", "KeKi": "Kempele", "KPL": "Kouvola", "KoU": "Koskenkorva", "KiPa": "Kitee",
         "IPV": "Imatra", "PattU": "Pattijoki", "Tahko": "Hyvinkää", "Manse": "Kauppi", "AA": "Alajärvi", "ViVe": "Vimpeli",
         "PuMu": "Meilahti"}
NIMET = {"Sotkamo": ["hiukka", "hiukan", "marjex", "terrafame", "sotkamo"],
         "Joensuu": ["joensuu", "mehtimä", "bolt", "telekarelia", "ilosaarirock"],
         "Kempele": ["kempele", "sarkkiranta", "autofix"], "Kouvola": ["kouvola", "kss energia"],
         "Koskenkorva": ["koskenkorva", "sähkökoje", "ilmajoki"], "Kitee": ["kitee", "rantakenttä"],
         "Imatra": ["imatra", "ukonniem", "tornator"], "Pattijoki": ["pattijoki", "rännäri"], "Hyvinkää": ["hyvinkää", "pihkala"],
         "Kauppi": ["kauppi", "kaupin", "tampere"], "Alajärvi": ["alajärvi", "kitro", "saltex"], "Vimpeli": ["vimpeli", "saarikenttä"], "Meilahti": ["meilahti", "good guy", "helsinki"]}
ASEMA = {"Sotkamo": [101756, 107113], "Joensuu": [101632, 101628], "Kempele": [108040, 101794, 101787],
         "Kouvola": [101191, 101194], "Koskenkorva": [101486, 101503], "Kitee": [101459, 101441],
         "Imatra": [101252, 101246, 101237], "Pattijoki": [101785, 101787, 101775], "Hyvinkää": [101130, 101149],
         "Kauppi": [101311, 101124], "Alajärvi": [101533, 101503], "Vimpeli": [101533, 101503], "Meilahti": [101004, 100971]}


def kentta(koti_lyh, stadion):
    """Ottelun kenttä: kotijoukkueen kenttä, jos stadionin nimi sopii (vieraskentät, hallit ja Fuengirola pois)."""
    k = SEURA.get(koti_lyh)
    if not k:
        return None
    st = (stadion or "").lower()
    return k if not st or any(n in st for n in NIMET[k]) else None


def myota(tulosuunta, nopeus, k):
    """Tuulen komponentti lyönnin suuntaan (m/s). Tulosuunta = mistä tuulee (0 = pohjoisesta)."""
    return nopeus * math.cos(math.radians((tulosuunta - (KENTAT[k] + 180)) % 360))


_KK = {}

def _kuukausi(fmisid, y, m):
    key = (fmisid, y, m)
    if key in _KK:
        return _KK[key]
    last = calendar.monthrange(y, m)[1]
    url = ("https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature"
           "&storedquery_id=fmi::observations::weather::hourly::simple"
           f"&fmisid={fmisid}&starttime={y}-{m:02d}-01T00:00:00Z&endtime={y}-{m:02d}-{last}T23:00:00Z"
           "&parameters=WD_PT1H_AVG,WS_PT1H_AVG")
    x = ""
    for k in range(3):
        try:
            x = urllib.request.urlopen(url, timeout=60).read().decode(); break
        except Exception:
            time.sleep(3 * (k + 1))
    D = {}
    for t, p, v in re.findall(r"<BsWfs:Time>([^<]+)</BsWfs:Time>\s*<BsWfs:ParameterName>([^<]+)</BsWfs:ParameterName>\s*<BsWfs:ParameterValue>([^<]+)", x):
        if v.strip() != "NaN":
            D.setdefault(t[:13], {})[p] = float(v)
    _KK[key] = D; time.sleep(0.4)
    return D


def tuuli(k, pvm):
    """[tulosuunta°, nopeus m/s, fmisid] ottelun ajalta (alkutunti + 2 h) tai None."""
    t = datetime.datetime.fromisoformat(pvm[:16])
    for fid in ASEMA[k]:
        D = _kuukausi(fid, t.year, t.month)
        hs = [D.get((t + datetime.timedelta(hours=h)).strftime("%Y-%m-%dT%H")) for h in (0, 1, 2)]
        hs = [h for h in hs if h and "WD_PT1H_AVG" in h and "WS_PT1H_AVG" in h]
        if hs:
            u = sum(h["WS_PT1H_AVG"] * math.sin(math.radians(h["WD_PT1H_AVG"])) for h in hs) / len(hs)
            v = sum(h["WS_PT1H_AVG"] * math.cos(math.radians(h["WD_PT1H_AVG"])) for h in hs) / len(hs)
            return [round(math.degrees(math.atan2(u, v)) % 360), round(sum(h["WS_PT1H_AVG"] for h in hs) / len(hs), 1), fid]
    return None
