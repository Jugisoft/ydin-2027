from ydin.talvi import muodosta

def _m(i, h, a, tulos=None, ryhma=1):
    r = None
    if tulos:
        r = {"result_string": tulos, "runs_home_first_period": 5, "runs_away_first_period": 2,
             "runs_home_second_period": 3, "runs_away_second_period": 3}
    return {"id": i, "home": h, "away": a, "date": f"2027-01-0{i}T15:00:00.000000Z", "result": r,
            "series": {"group": ryhma, "phase": 14}, "stadium": {"name": "Halli"}}

def test_taulukko_ja_ohjelma():
    maps = {"team": [{"id": 1, "value": {"shorthand": "KPL"}}, {"id": 2, "value": {"shorthand": "IPV"}},
                     {"id": 3, "value": {"shorthand": "ViVe"}}],
            "group": [{"id": 1, "value": {"name": "Lohko B"}}], "phase": [{"id": 14, "value": {"name": "Alkulohkot"}}]}
    d = muodosta([_m(1, 2, 1, "0-2 (2-5, 3-3)"), _m(2, 1, 3)], maps, 2027, 3745)
    assert [o["koti"] for o in d["ottelut"]] == ["IPV", "KPL"]
    t = {r["jk"]: r for r in d["taulukot"]["Lohko B"]}
    assert t["KPL"]["V"] == 1 and t["IPV"]["H"] == 1 and t["ViVe"]["O"] == 0
    assert d["taulukot"]["Lohko B"][0]["jk"] == "KPL"
