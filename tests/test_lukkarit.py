"""Lukkarin vapaat ja kärpäset keinotekoisesta ottelusta (ei verkkoa)."""
from ydin.lukkarit import tapahtumaluvut, rikasta, KENTAT, TKENTAT

def _e(team, *texts, period=0):
    return {"period": period, "inning": 0, "team": team, "events": [{"texts": list(texts), "runnersAtBases": [None] * 5}]}

def _ev(t):
    return {"type": "event", "text": t}

D = {"events": [
    _e(1, {"type": "player", "id": 9}, _ev("sai vapaataipaleen väärien syöttöjen johdosta"), "ykköspesälle"),
    _e(1, {"type": "player", "id": 9}, _ev("sai vapaataipaleen väärien syöttöjen johdosta"), "kotipesään"),
    _e(1, {"type": "player", "id": 8}, _ev("paloi kärpäsenä lukkarin toimesta"), {"type": "stat", "out": 1}),
    _e(2, {"type": "player", "id": 3}, _ev("sai vapaataipaleen väärien syöttöjen johdosta"), "kolmospesälle"),
    _e(2, {"type": "player", "id": 4}, _ev("paloi kärpäsenä"), {"type": "stat", "out": 1}),
    _e(2, _ev("sai vapaataipaleen väärien syöttöjen johdosta"), "ykköspesälle", period=2),   # supervuoro pois
]}

def test_vapaat_ja_karpaset_puolustavalle_joukkueelle():
    t = tapahtumaluvut(D)
    # joukkue 1 lyö -> joukkue 2 puolustaa: 2 vapaata (1. pesälle ja kotiin), 1 kärpänen lukkarilta
    assert t[2] == [2, 1, 0, 1, 1, 1]
    assert t[1] == [1, 0, 1, 0, 0, 1]

def test_rikasta_ilman_tapahtumia_null(tmp_path, monkeypatch):
    import ydin.lukkarit as L
    monkeypatch.setattr(L, "TAPAHTUMAT", str(tmp_path))
    r = [[1, "2026-05-01", 1, 7, "KPL", "IPV"] + [0] * (len(KENTAT) - len(TKENTAT) - 6)]
    assert rikasta(r, 2026, {"KPL": 2}) == 0
    assert len(r[0]) == len(KENTAT) and r[0][-1] is None
