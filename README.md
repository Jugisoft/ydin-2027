# YDIN 2027

Superpesis-analytiikka ilman käsityötä. Seuraaja YDIN 2026:lle (Jugisoft/ydin).

```
GitHub Actions (ajastus) → ydin/haku.py → ydin/mittarit.py → data/out/*.json → web/ → GitHub Pages
```

- **Ei Exceliä eikä Power Queryä.**
- **Vain julkista ottelu- ja lyöntivuorotason tilastodataa** (pesistulokset.fi stats-tool). Koko kausi ≈ 8 pyyntöä. Ks. `docs/linjaukset.md`.
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
| `.github/workflows/paivita.yml` | Ajastettu päivitys + julkaisu |
| `docs/` | `mittarit.md`, `linjaukset.md` |
| `arkisto/` | Vanha tapahtumapohjainen portti (ei käytössä) |
| `web/` | Käyttöliittymä (vaihe 3) |
