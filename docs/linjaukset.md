# Linjaukset

| Pvm | Linjaus |
| --- | --- |
| 3.10.2026 | **Vain julkisesti tarjottu ottelu- ja lyöntivuorotason tilastodata** (stats-tool, otteluluettelo). Lyöntikohtaista tapahtumadataa (`/online/{id}/events`) ei käytetä automaattisessa putkessa, jotta rajapinnan kanssa ei tule käyttöongelmia. Tapahtumista lukenut portti on tallessa: `arkisto/lyonnit_tapahtumista.py`. |
| 16.10.2026 | **Tarkennus (Jugi):** ottelutapahtumat (`/online/{id}/events`) haetaan **kerran per päättynyt ottelu** iltaajossa klo 21.30. Raakadata tallennetaan pakattuna (`data/tapahtumat/<kausi>/<id>.json.gz`), eikä samaa ottelua haeta uudelleen. Käyttö: lyöntikartat (`data/out/lyonnit_<kausi>/`) ja juoksuodotus. Perustelu: julkista dataa (mm. medialle), yksi haku per ottelu ≈ 230 hakua kaudessa. Jos rajapinta suljetaan tai muuttuu, linjaus mietitään uudelleen. |
| 3.10.2026 | Koko kausi haetaan muutamalla pyynnöllä (≈8/ajo), viive 1 s, uudelleenyritys. |
| 3.10.2026 | Termit pesistulokset.fi-standardin mukaan. KL0–KL3 = kärkietenijän lähtöpesä. |
| 3.10.2026 | Toimivaan YDIN 2026:een (Jugisoft/ydin) ei kosketa ennen kuin YDIN 2027 on todistetusti valmis. |
