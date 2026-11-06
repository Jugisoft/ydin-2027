"""Lyöntikarttojen poiminta keinotekoisesta ottelusta (ei verkkoa)."""
from ydin.lyonnit import ottelun_lyonnit, TIL, TUL
from ydin.tapahtumat import paattyneet
import datetime

def _g(hit=None, texts=(), runners=(1, None, None, None, None), period=0, inning=0, team=5):
    return {"period": period, "inning": inning, "team": team, "hitNumber": hit and hit.get("hit_number"), "hit": hit,
            "events": [{"texts": list(texts), "runnersAtBases": list(runners)}]}

def test_tulos_tilanne_palot_ja_kalibrointi():
    d = {"events": [
        _g({"batter_player_id": 1, "x": "50", "y": "95", "hit_number": 1}, [{"type": "hit"}, {"type": "hit-out", "text": "laiton"}]),
        _g({"batter_player_id": 1, "x": "10", "y": "4.5", "hit_number": 2}, [{"type": "event", "text": "paloi"}, {"type": "stat", "out": 1}]),
        _g({"batter_player_id": 2, "x": "60", "y": "40", "hit_number": 1}, [{"type": "stat", "score": 1}], runners=(2, None, 7, 8, None)),
        _g({"batter_player_id": 2, "x": "0", "y": "0", "hit_number": 2}, []),   # kohta puuttuu
        _g({"batter_player_id": 3, "x": "50", "y": "50", "hit_number": 1}, [{"type": "hit-caught"}], period=2),  # supervuoro pois
    ]}
    l = ottelun_lyonnit(d, 0)
    assert len(l) == 3
    (p1, _, a), (_, _, b), (p3, _, c) = l
    assert a[:2] == [0.0, 0.0] and TUL[a[5]] == "laiton" and a[3] == 0
    assert b[:2] == [-21.0, 95.9] and TUL[b[5]] == "palo"
    assert TIL[c[2]] == "2–3" and c[3] == 1 and TUL[c[5]] == "juoksu" and p3 == 2

def test_paattyneet():
    nyt = datetime.datetime(2027, 6, 1, 19, tzinfo=datetime.timezone.utc)
    o = [{"id": 1, "pvm": "2027-06-01T15:00:00.000000Z", "tulos": "2-0"}, {"id": 2, "pvm": "2027-06-01T15:00:00.000000Z", "tulos": None},
         {"id": 3, "pvm": "2027-06-02T15:00:00.000000Z", "tulos": "1-1"}]
    assert [x["id"] for x in paattyneet(o, nyt)] == [1]

def _s(pl, *t):
    return {"texts": [{"type": "player", "id": pl}, *t], "runnersAtBases": [None] * 5}

def test_takapalo_on_onnistunut_karkilyonti():
    from ydin.lyonnit import takapalo
    hit = {"batter_player_id": 1, "x": "50", "y": "50", "hit_number": 1}
    g = {"period": 0, "inning": 0, "team": 5, "hit": hit, "events": [
        {"texts": ["1. lyönti", {"type": "hit"}], "runnersAtBases": [1, 2, 3, None, None]},
        _s(3, {"type": "event", "text": "eteni"}, "kolmospesälle", {"type": "stat", "pointhits": 2}),
        _s(2, {"type": "event", "text": "paloi"}, {"type": "stat", "out": 1}, "kakkospesälle")]}
    assert takapalo(g) == 1
    rivi = ottelun_lyonnit({"events": [g]}, 0)[0][2]
    assert TUL[rivi[5]] == "eteni" and rivi[7] == 1
    # kärki itse paloi -> ei takapaloa, tulos palo
    g["events"][1] = _s(3, {"type": "event", "text": "paloi"}, {"type": "stat", "out": 1}, {"type": "stat", "pointhitf": 2})
    assert takapalo(g) == 0 and TUL[ottelun_lyonnit({"events": [g]}, 0)[0][2][5]] == "palo"
