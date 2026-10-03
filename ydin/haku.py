"""Rajapintahaku. Linjaus (Jugi 3.10.2026): käytetään vain julkisesti tarjottua ottelu- ja
lyöntivuorotason tilastodataa (stats-tool) ja otteluluetteloa – EI lyöntikohtaista tapahtumadataa.
Koko kausi = muutama pyyntö. Kohtelias: viive ja uudelleenyritys."""
import time
import requests

API = "https://api.pesistulokset.fi/api/v1"
API_V1 = "https://v1.pesistulokset.fi/api/v1"
H = {"Accept": "application/json", "Referer": "https://www.pesistulokset.fi/", "User-Agent": "YDIN2027 (+https://github.com/Jugisoft)"}
VIIVE = 1.0

def _get(url, yrityksia=4):
    for k in range(yrityksia):
        try:
            r = requests.get(url, headers=H, timeout=90)
            if r.status_code == 200:
                time.sleep(VIIVE); return r.json()
            if r.status_code in (429, 502, 503, 504):
                time.sleep(5 * (k + 1)); continue
            r.raise_for_status()
        except requests.RequestException:
            if k == yrityksia - 1: raise
            time.sleep(5 * (k + 1))
    raise RuntimeError(f"Haku epäonnistui: {url}")

def ottelut(season_series):
    """Otteluluettelo ja tulokset (sivutettu)."""
    url, rivit, maps = f"{API}/matches?type=all&seasonSeries={season_series}", [], {}
    while url:
        d = _get(url); rivit += d.get("data", [])
        for k, v in (d.get("maps") or {}).items(): maps.setdefault(k, []).extend(v)
        url = d.get("next_page") if d.get("has_more") else None
    return rivit, maps

def pelaajat_otteluittain(season_series, phase):
    """Yksi rivi per pelaaja per ottelu (ei summattu). phase: 1 runkosarja, 2 ylempi jatko, 3 alempi jatko."""
    return _get(f"{API_V1}/stats-tool/players?organizer=1&level=1&seasonSeries={season_series}&limit=20000&phase={phase}")

def joukkueet_otteluittain(season_series, phase):
    """Yksi rivi per joukkue per ottelu, mukana vastustajan luvut (_opponent)."""
    return _get(f"{API_V1}/stats-tool/teams?organizer=1&level=1&seasonSeries={season_series}&limit=20000&phase={phase}")
