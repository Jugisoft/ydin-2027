"""Siirtovaikutus: juoksuosuus täsmää joukkueiden juoksuihin, jälkitesti ja selostuksen parametrit syntyvät."""
from ydin import kaudet, siirtovaikutus as sv


def test_kerroin_lahella_yhta():
    D = sv.Data(max(kaudet.MSU))
    C = D.kerroin(max(kaudet.MSU))
    assert 0.95 < C < 1.15  # YHT/2 kattaa valtaosan juoksuista


def test_laske_rakenne():
    d = sv.laske(max(kaudet.MSU))
    assert d["kausi"] == max(kaudet.MSU) + 1
    assert len(d["joukkueet"]) >= 10
    for r in d["joukkueet"]:
        assert len(r["kokoonpano"]) <= sv.KOKOONPANO
        if r["superpesis_edellinen"]:
            assert abs(r["muutos"] - (r["hyokkays_muutos"] + (r["lukkari_muutos"] or 0))) < 0.02
    j = d["jalkitesti"]
    assert j and j["n"] >= 20 and -1 <= j["muutos_korrelaatio"] <= 1
