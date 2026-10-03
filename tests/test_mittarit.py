"""Mittarilogiikan testit keinotekoisella ottelulla (ei verkkoa)."""
from ydin.mittarit import pelaajat, joukkueet

def _p(pid, tid, **kw):
    r = {"player_id": pid, "team_id": tid, "match_id": 1, "matches": 1}
    r.update(kw); return r

def test_pelaajasummat():
    rivit = [
        _p(10, 1, homeruns=1, scorings=3, runs=2, batpe_succeeded_0=1, batpe_tries_0=2, batpe_succeeded_3=2, batpe_tries_3=3,
           batpe_total_succeeded=3, batpe_total_tries=5, turns_at_bat=6),
        dict(_p(10, 1, scorings=1, batpe_succeeded_2=1, batpe_tries_2=1, batpe_total_succeeded=1, batpe_total_tries=1), match_id=2),
    ]
    p = pelaajat(rivit)[10]
    assert (p["O"], p["K"], p["L"], p["T"], p["YHT"]) == (2, 1, 4, 2, 7)
    assert (p["KL"], p["KLY"], p["KL%"]) == (4, 6, 66.7)
    assert p["KLY"] == sum(p[f"KLY{n}"] for n in range(4))
    assert p["KL%3"] == 66.7 and p["joukkue"] == 1

def test_joukkueet_kotiutus_ja_torjunta():
    a = {"team_id": 1, "won": 1, "pe_total_b3": 3, "pe_tries_b3": 6, "pe_total_b3_opponent": 2, "pe_tries_b3_opponent": 8,
         "pe_total": 10, "pe_tries_total": 20}
    b = {"team_id": 2, "won": 0, "pe_total_b3": 2, "pe_tries_b3": 8, "pe_total_b3_opponent": 3, "pe_tries_b3_opponent": 6}
    J = joukkueet([a, b])
    assert J[1]["kotiutus%"] == 50.0
    assert J[1]["torjunta%"] == 75.0          # vastustaja onnistui 2/8
    assert J[2]["kotiutus%"] == 25.0 and J[2]["torjunta%"] == 50.0
    assert J[1]["KL%"] == 50.0 and J[1]["voitot"] == 1

def test_sarjapisteet():
    from ydin.sivu import tulos, pisteet
    assert pisteet(*tulos("2-0 (3-1, 2-0)")) == (3, 0)
    assert pisteet(*tulos("1-0 (2-2, 1-0)")) == (2, 0)
    assert pisteet(*tulos("1-2k (5-3, 5-6, 0-0, 2-4)")) == (2, 1)
    assert pisteet(*tulos("2-1S (2-3, 7-1, 1-2)")) == (2, 1)
