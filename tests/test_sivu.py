"""Ottelut- ja Tulostaulut-sivujen data (käyttää repossa olevaa data/out-aineistoa)."""
import re
from ydin import sivu

def test_kierrokset_nimet_ja_voittajat():
    ott = [{"id": 1, "pvm": "2026-08-20", "vaihe": 2, "koti": 10, "vieras": 20, "tulos": "2-0 (3-1, 2-0)"},
           {"id": 2, "pvm": "2026-08-22", "vaihe": 2, "koti": 20, "vieras": 10, "tulos": "1-2k (1-0, 0-1, 0-1, 1-2)"}]
    (nimi, ms, w), = sivu.kierrokset(ott)
    assert nimi == "Puolivälierä" and [m["id"] for m in ms] == [1, 2] and w[10] == 2 and w[20] == 0

def test_ottelujen_juoksut_tasmaavat_tulokseen():
    """Joukkueen ottelukohtaiset juoksut = jaksojen juoksut ilman kotiutuskilpailua."""
    d = sivu.ottelut_data()
    assert d["ottelut"]
    for oid, _pvm, _v, koti, vieras, tulos, _k in d["ottelut"]:
        osat = re.search(r"\((.*)\)", tulos).group(1).split(",")
        per = [tuple(map(int, re.sub(r"[^\d-]", "", x).split("-"))) for x in osat]
        if tulos.split()[0].endswith("k"):
            per = per[:-1]
        j = d["joukkueet"][str(oid)]
        assert (j[str(koti)][0], j[str(vieras)][0]) == (sum(a for a, _ in per), sum(b for _, b in per)), tulos

def test_tulostaulujen_karjet():
    t = sivu.tulostaulut_data(set())
    for nimi, k in t["yksi_karjet"].items():
        assert 0 < len(k["rivit"]) <= 15, nimi
