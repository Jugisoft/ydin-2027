"""pesistulokset.fi seasonSeries -tunnisteet."""
MSU = {2023: 916, 2024: 1292, 2025: 1955, 2026: 2945}   # miesten Superpesis
TALVI = {2025: 1957, 2026: 2963}                      # miesten Talvisuper
YP_MIEHET = {2026: 2954}                              # miesten Ykköspesis
# Superpesis 1990–2022: ks. Jarvis-vault 05 Jarvis/Työkalut/siirtomarkkinat.py (MSU-taulu)
# Otteluennusteen pohja (ydin/ennuste.py): stats-toolin ottelukohtaiset joukkuerivit löytyvät kaudesta 2010 alkaen.
# Erillinen taulu, jotta muut moduulit (historia, lukkarit) eivät ala hakea vanhoja kausia.
MSU_HISTORIA = {2010: 111, 2011: 119, 2012: 127, 2013: 136, 2014: 147, 2015: 156, 2016: 165, 2017: 174,
                2018: 182, 2019: 193, 2020: 324, 2021: 208, 2022: 347, **MSU}


def uusin():
    """Uusin kausi, jolle on Superpesis-tunniste. Kun kauden 2027 sarja julkaistaan, lisää sen tunniste MSU-tauluun."""
    return max(MSU)
