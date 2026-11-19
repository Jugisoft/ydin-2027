"""Otteluennuste: ristiinlaskenta, logistinen regressio ja jälkitesti tallessa olevasta ottelupohjasta."""
import math
from ydin import ennuste as en


def test_risti_keskitaso_on_neutraali():
    en_lg = {"t3": 12.0, "kot": 0.45}
    import types
    vanha = dict(en.TIL)
    try:
        # sarjan keskiarvo vs. keskiarvo = keskiarvo
        assert abs(en.risti("t3", 12.0, 12.0, 12.0) - 12.0) < 1e-9
        assert abs(en.risti("kot", 0.45, 0.45, 0.45) - 0.45) < 1e-9
        # hyvä hyökkäys vs. heikko puolustus > kumpikin yksin
        assert en.risti("kot", 0.5, 0.5, 0.45) > 0.5
    finally:
        en.TIL.update(vanha)


def test_logreg_loytaa_suunnan():
    X = [[x / 10] for x in range(-20, 21)] * 3
    y = [1 if x[0] + (0.3 if i % 3 == 0 else -0.3) > 0 else 0 for i, x in enumerate(X)]
    w = en.logreg(X, y)
    assert w[1] > 0


def test_jalkitesti_ja_rakenne():
    d = en.laske()
    j = d["jalkitesti"]
    assert j["malli"]["n"] > 1000
    assert j["malli"]["osuma"] > j["koti"]["osuma"]          # parempi kuin pelkkä kotijoukkue
    assert j["malli"]["logloss"] < j["koti"]["logloss"]
    assert 10 <= len(d["joukkueet"]) <= 14
    for r in d["joukkueet"]:
        assert 0 < r["vahvuus"] < 1
    assert d["malli"]["kertoimet"]["t3"] > 0                  # 3-tilanteet: enemmän = parempi
    # kalibrointi: ryhmien toteuma lähellä ennustetta
    for k in j["kalibrointi"]:
        assert abs(k["ennuste"] - k["toteutui"]) < 0.08


def test_saa_lampo_lisaa_juoksuja():
    d = en.laske()["saa"]
    assert d and d["n"] > 1000
    assert d["per_aste"] - d["per_aste_luottamus"] > 0          # lämpö lisää juoksuja (merkitsevästi)
    L = {l["avain"]: l for l in d["luokat"]}
    assert L["helle"]["havaittu"] > L["hyva"]["havaittu"] > L["kylma"]["havaittu"]


def test_myotatuuli_suunta():
    from ydin.kentat import myota
    # Vimpeli: kotipesä -> takaraja 120°, tuuli luoteesta (300°) puhaltaa kohti 120° = täysi myötätuuli
    assert abs(myota(300, 5, "Vimpeli") - 5) < 1e-9
    assert abs(myota(120, 5, "Vimpeli") + 5) < 1e-9      # kaakosta = vastatuuli
    assert abs(myota(30, 5, "Vimpeli")) < 1e-9           # sivutuuli


def test_tuuli_lisaa_juoksuja():
    t = en.laske()["saa"]["myotatuuli"]
    assert t and t["n"] > 1000 and t["per_ms"] - t["per_ms_luottamus"] > 0
