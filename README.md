# YDIN 2027

Superpesis-analytiikka ilman käsityötä. Seuraaja YDIN 2026:lle (Jugisoft/ydin).

```
GitHub Actions (ajastus) → ydin/haku.py → ydin/mittarit.py → data/out/*.json → web/ → GitHub Pages
```

- **Ei Exceliä eikä Power Queryä.**
- **Julkista dataa:** tilastot stats-toolista (koko kausi ≈ 8 pyyntöä) ja ottelutapahtumat kerran per päättynyt ottelu (lyöntikartat). Ks. `docs/linjaukset.md`.
- **Iltaajo klo 21.30** Suomen aikaa.
- **Termit pesistulokset.fi-standardin mukaan** (K, L, T, YHT, KL, KLY, KL%, KL0–KL3 = lähtöpesä).

## Ajo paikallisesti
```
pip install -r requirements.txt
python -m ydin.paivita --kausi 2026          # hakee, laskee, kirjoittaa data/out/
python -m pytest
```

## Rakenne
| Polku | Sisältö |
| --- | --- |
| `ydin/kaudet.py` | Sarjatunnisteet (seasonSeries) |
| `ydin/haku.py` | Rajapintahaku (otteluluettelo, stats-tool otteluittain) |
| `ydin/mittarit.py` | Tunnusluvut lyöntiriveistä ja stats-toolista |
| `ydin/paivita.py` | Koko putki yhdellä komennolla |
| `ydin/tapahtumat.py` | Uusien päättyneiden otteluiden tapahtumat → `data/tapahtumat/<kausi>/<id>.json.gz` |
| `ydin/lyonnit.py` | Lyöntikartat → `data/out/lyonnit_<kausi>/` (KPL Keskus lukee) |
| `.github/workflows/paivita.yml` | Ajastettu päivitys + julkaisu |
| `docs/` | `mittarit.md`, `linjaukset.md` |
| `arkisto/` | Vanha tapahtumapohjainen portti (ei käytössä) |
| `web/` | Käyttöliittymä (vaihe 3) |
