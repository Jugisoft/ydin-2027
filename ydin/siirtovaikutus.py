"""Siirtojen vaikutus ennustettuna juoksuerona per ottelu (kokoonpanot <kausi+1> vs. <kausi>) + jälkitesti.

python -m ydin.siirtovaikutus  ->  data/out/siirtovaikutus_<kausi+1>.json  (sivu: siirtovaikutus.html)

Menetelmä (vain runkosarja). Sama selitys näkyy sivulla kohdassa "Miten luvut on laskettu".
1. Pelaajan juoksuosuus. Joukkueen jokainen juoksu kirjautuu tuojalle (T) ja lyöjälle (L, kunnarissa K),
   joten pelaajan osuus = YHT / 2. Liigatasolla summa jää hieman alle joukkueiden juoksujen (osa juoksuista
   syntyy ilman lyöjää, esim. vapaista); ero korjataan kertoimella C = juoksut / Σ(YHT/2).
2. Pelaajan ennuste per ottelu: neljän kauden painotettu keskiarvo (uusin 1, sitten 0,6, 0,35, 0,2; painotettu
   otteluilla) ja kutistus korvaustasoon: (Σ w·C·YHT/2 + k·korvaus) / (Σ w·O + k), k = 8 ottelua.
   Korvaustaso = 25. persentiili pelaajista, joilla ≥ 15 ottelua uusimmalla kaudella. Pelaaja ilman
   Superpesis-otteluita saa korvaustason.
3. Hyökkäys = 12 suurimman ennusteen summa (ottelukokoonpano 9 + 3 jokeria). Tyhjät paikat = korvaustaso.
   Muutos = uusi kokoonpano − sama laskenta edellisen kauden pelaajista, joten menetelmän taso kumoutuu.
4. Lukkari. Päästetyt juoksut per ottelu lukkarin aloittamissa runkosarjaotteluissa (samat kausipainot), kutistus
   sarjan keskiarvoon k = 15 ottelua. Uuden kauden lukkari = sopimuspelaaja, jolla eniten lukkariotteluita (≥ 3).
   Muu ulkopeli ei näy tilastoissa, eikä sen muutosta arvioida.
5. Juoksuero-ennuste = edellisen kauden juoksuero + hyökkäyksen muutos − lukkarin päästettyjen muutos.
   Nousijoille (ei edellisen kauden Superpesis-dataa): hyökkäys suhteessa sarjan keskimääräiseen joukkueeseen,
   päästetyt = lukkarin ennuste tai sarjan keskiarvo.
6. Jälkitesti: samat laskut jokaiselle aiemmalle kaudelle, jolle on vähintään yhden kauden pohja, käyttäen ennustettavan
   kauden toteutuneita kokoonpanoja (pelanneet pelaajat). Tulos kertoo, kuinka paljon muutosluvuista voi päätellä.
"""
import collections, json, os, re, statistics, unicodedata

JUURI = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(JUURI, "data", "out")
SEURANTA = os.path.join(JUURI, "data", "seuranta", "seuranta.json")
PAINOT = (1.0, 0.6, 0.35, 0.2)
K_PELAAJA, K_LUKKARI, KOKOONPANO, LK_MIN = 8, 15, 12, 3


def _lue(n):
    with open(os.path.join(OUT, n), encoding="utf-8") as f:
        return json.load(f)


def _on(n):
    return os.path.exists(os.path.join(OUT, n))


def _norm(s):
    s = unicodedata.normalize("NFC", s or "").lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-zåäöüé\- ]", " ", s))


def _osuus(r):  # historia-rivi: [jk, O, K, L, T, KL, KLY, ...]
    return (r[2] + r[3] + r[4]) / 2


class Data:
    def __init__(self, viimeisin):
        self.H, self.nimet, self.LK, self.JH = {}, {}, {}, {}
        for v in range(viimeisin - 10, viimeisin + 1):
            if _on(f"historia_{v}.json"):
                h = _lue(f"historia_{v}.json"); self.H[v] = h["runko"]; self.nimet.update(h["nimet"])
            if _on(f"lukkarit_{v}.json"):
                d = _lue(f"lukkarit_{v}.json"); i = {k: n for n, k in enumerate(d["kentat"])}
                self.LK[v] = [(str(r[i["lukkari"]]), r[i["jk"]], r[i["juoksut_v"]]) for r in d["rivit"] if r[i["vaihe"]] == 1]
            if _on(f"joukkuehistoria_{v}.json"):
                self.JH[v] = {t: x for t, x in _lue(f"joukkuehistoria_{v}.json")["joukkueet"].items() if "juoksut" in x}

    def kerroin(self, v):
        juoksut = sum(x["juoksut"] for x in self.JH[v].values())
        return juoksut / sum(_osuus(r) for r in self.H[v].values())

    def pelaajat(self, pohja):
        """-> ennuste {pid: juoksua/ottelu}, otos {pid: painotetut ottelut}, korvaustaso"""
        C = self.kerroin(pohja)
        kaudet = [pohja - i for i in range(len(PAINOT))]
        rate = sorted(C * _osuus(r) / r[1] for r in self.H[pohja].values() if r[1] >= 15)
        korvaus = rate[len(rate) // 4]
        e, otos = {}, {}
        for pid in set().union(*[self.H[v] for v in kaudet if v in self.H]):
            s = o = 0.0
            for w, v in zip(PAINOT, kaudet):
                r = self.H.get(v, {}).get(pid)
                if r:
                    s += w * C * _osuus(r); o += w * r[1]
            e[pid] = (s + K_PELAAJA * korvaus) / (o + K_PELAAJA); otos[pid] = o
        return e, otos, korvaus, C

    def lukkarit(self, pohja):
        """-> ennuste {pid: päästetyt/ottelu}, ottelut {pid: painotetut}, sarjan keskiarvo"""
        kaudet = [pohja - i for i in range(len(PAINOT))]
        s, o = collections.defaultdict(float), collections.defaultdict(float)
        for w, v in zip(PAINOT, kaudet):
            for pid, _, pa in self.LK.get(v, []):
                s[pid] += w * pa; o[pid] += w
        rivit = self.LK[pohja]; ka = sum(r[2] for r in rivit) / len(rivit)
        return {p: (s[p] + K_LUKKARI * ka) / (o[p] + K_LUKKARI) for p in s}, dict(o), ka

    def lukkari_jk(self, v, jk, lp, ka):
        """Joukkueen kauden v lukkarien ennusteiden otteluilla painotettu keskiarvo + pääasiallinen lukkari."""
        c = collections.Counter(pid for pid, t, _ in self.LK.get(v, []) if t == jk)
        if not c:
            return None, None
        return sum(lp.get(p, ka) * n for p, n in c.items()) / sum(c.values()), c.most_common(1)[0][0]


def _hyokkays(pids, e, korvaus):
    arvot = sorted((e.get(p, korvaus) for p in pids), reverse=True)[:KOKOONPANO]
    return sum(arvot) + max(0, KOKOONPANO - len(arvot)) * korvaus


def _ero(x):
    return (x["juoksut"] - x["paastetyt"]) / x["O"]


def _kor(a, b):
    return round(statistics.correlation(a, b), 2) if len(a) > 2 else None


def _virhe(p, a):  # keskimääräinen itseisvirhe sarjan tasoon nähden
    pm, am = statistics.mean(p), statistics.mean(a)
    return round(statistics.mean(abs((x - pm) - (y - am)) for x, y in zip(p, a)), 2)


def jalkitesti(D, viimeisin):
    rivit = []
    for kohde in sorted(D.JH):
        pohja = kohde - 1
        if kohde > viimeisin or pohja not in D.JH or pohja not in D.H or pohja not in D.LK or kohde not in D.LK:
            continue
        e, _, korvaus, _ = D.pelaajat(pohja); lp, _, ka = D.lukkarit(pohja)
        for jk, x in D.JH[kohde].items():
            if jk not in D.JH[pohja]:
                continue
            uusi = [p for p, r in D.H[kohde].items() if r[0] == jk]
            vanha = [p for p, r in D.H[pohja].items() if r[0] == jk]
            d_h = _hyokkays(uusi, e, korvaus) - _hyokkays(vanha, e, korvaus)
            l1, _ = D.lukkari_jk(kohde, jk, lp, ka); l0, _ = D.lukkari_jk(pohja, jk, lp, ka)
            d_l = (l1 - l0) if l1 is not None and l0 is not None else 0.0
            rivit.append({"kausi": kohde, "joukkue": jk, "edellinen": round(_ero(D.JH[pohja][jk]), 2), "toteuma": round(_ero(x), 2),
                          "ennustettu_muutos": round(d_h - d_l, 2), "toteutunut_muutos": round(_ero(x) - _ero(D.JH[pohja][jk]), 2)})
    if not rivit:
        return None
    ed = [r["edellinen"] for r in rivit]; to = [r["toteuma"] for r in rivit]
    yh = [r["edellinen"] + r["ennustettu_muutos"] for r in rivit]
    return {"kaudet": sorted({r["kausi"] for r in rivit}), "n": len(rivit),
            "muutos_korrelaatio": _kor([r["ennustettu_muutos"] for r in rivit], [r["toteutunut_muutos"] for r in rivit]),
            "edellinen": {"korrelaatio": _kor(ed, to), "virhe": _virhe(ed, to)},
            "edellinen_plus_muutos": {"korrelaatio": _kor(yh, to), "virhe": _virhe(yh, to)},
            "rivit": rivit}


def laske(viimeisin):
    D = Data(viimeisin)
    e, otos, korvaus, C = D.pelaajat(viimeisin)
    lp, lk_ott, ka_pa = D.lukkarit(viimeisin)
    nyt = D.H[viimeisin]; jh = D.JH[viimeisin]
    nimesta = {_norm(n): pid for pid, n in D.nimet.items()}
    joukkue26 = {pid: r[0] for pid, r in nyt.items()}
    sarja_ka = sum(x["juoksut"] for x in jh.values()) / sum(x["O"] for x in jh.values())
    ka_hyok = statistics.mean(_hyokkays([p for p, t in joukkue26.items() if t == jk], e, korvaus) for jk in jh)
    seur = json.load(open(SEURANTA, encoding="utf-8"))
    tulos = []
    for jk, kp in seur["kokoonpanot"].items():
        roster, ilman = [], []
        for nimi, _, uusi in kp.get("sopimus", []):
            puhdas = re.sub(r"\s*\(.*?\)", "", nimi).strip()
            pid = nimesta.get(_norm(puhdas))
            if pid and pid in e:
                roster.append(pid)
            else:
                ilman.append(puhdas)
        hyok = _hyokkays(roster, e, korvaus)
        valittu = sorted(roster, key=lambda p: -e[p])[:KOKOONPANO]
        on = jk in jh
        vanhat = [p for p, t in joukkue26.items() if t == jk]
        d_h = hyok - _hyokkays(vanhat, e, korvaus) if on else None
        ehd = sorted((lk_ott.get(p, 0), p) for p in roster if p in lp)
        lk27 = ehd[-1][1] if ehd and ehd[-1][0] >= LK_MIN else None
        pa27 = lp[lk27] if lk27 else ka_pa
        pa26, lk26 = D.lukkari_jk(viimeisin, jk, lp, ka_pa) if on else (None, None)
        d_l = (pa27 - pa26) if on and pa26 is not None else None
        if on:
            teh, pa = jh[jk]["juoksut"] / jh[jk]["O"], jh[jk]["paastetyt"] / jh[jk]["O"]
            e_teh, e_pa = teh + d_h, pa + (d_l or 0)
        else:
            teh = pa = None
            e_teh, e_pa = sarja_ka + (hyok - ka_hyok), pa27
        tulleet = [p for p in roster if joukkue26.get(p) != jk]
        lahteneet = [p for p in vanhat if p not in roster]
        rp = lambda p: {"id": p, "nimi": D.nimet.get(p, ""), "ennuste": round(e[p], 2), "otos": round(otos.get(p, 0), 1),
                        "joukkue": joukkue26.get(p), "kokoonpanossa": p in valittu}
        tulos.append({
            "joukkue": jk, "superpesis_edellinen": on,
            "teh": None if teh is None else round(teh, 2), "pa": None if pa is None else round(pa, 2),
            "ero": None if teh is None else round(teh - pa, 2),
            "hyokkays_muutos": None if d_h is None else round(d_h, 2),
            "lukkari_muutos": None if d_l is None else round(-d_l, 2),
            "muutos": None if d_h is None else round(d_h - (d_l or 0), 2),
            "ennuste_teh": round(e_teh, 2), "ennuste_pa": round(e_pa, 2), "ennuste_ero": round(e_teh - e_pa, 2),
            "lukkari_ed": D.nimet.get(lk26) if lk26 else None, "lukkari": D.nimet.get(lk27) if lk27 else None,
            "lukkari_ennuste": round(pa27, 2),
            "kokoonpano": [rp(p) for p in valittu],
            "tulleet": [rp(p) for p in sorted(tulleet, key=lambda p: -e[p])],
            "lahteneet": [rp(p) for p in sorted(lahteneet, key=lambda p: -e[p])],
            "ilman_dataa": ilman, "sopimuksia": len(kp.get("sopimus", [])),
            "tyhjia_paikkoja": max(0, KOKOONPANO - len(roster)),
        })
    tulos.sort(key=lambda r: -r["ennuste_ero"])
    return {"kausi": viimeisin + 1, "pohja": viimeisin, "seuranta_paivitetty": seur.get("paiv"),
            "parametrit": {"kerroin_C": round(C, 3), "korvaustaso": round(korvaus, 3), "sarja_juoksut": round(sarja_ka, 2),
                           "lukkari_ka": round(ka_pa, 2), "kokoonpano": KOKOONPANO, "k_pelaaja": K_PELAAJA, "k_lukkari": K_LUKKARI,
                           "painot": {str(viimeisin - i): w for i, w in enumerate(PAINOT)}},
            "joukkueet": tulos, "jalkitesti": jalkitesti(D, viimeisin)}


def main():
    from . import kaudet
    d = laske(max(kaudet.MSU))
    with open(os.path.join(OUT, f"siirtovaikutus_{d['kausi']}.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    for r in d["joukkueet"]:
        m = r["muutos"]
        print(f"{r['joukkue']:<6} muutos {'' if m is None else f'{m:+.2f}':>6}  ennuste-ero {r['ennuste_ero']:+.2f}  lukkari {r['lukkari_ed']} → {r['lukkari']}")
    j = d["jalkitesti"]
    if j:
        print("jälkitesti", j["kaudet"], "n", j["n"], "muutos-korrelaatio", j["muutos_korrelaatio"], j["edellinen"], j["edellinen_plus_muutos"])


if __name__ == "__main__":
    main()
