"""Lyöntirivit ottelun tapahtumista – 1:1-portti Power Queryn fHaeOttelu-funktiosta (YDIN 2026, file1).

Validoitu 3.10.2026: 497 ottelua (MSU2025, Talvisuper 2026, MSU2026) vs. MasterLyonnit.
482 identtistä; 11 eroaa vain supervuoroparin osalta (Excel-cache jäädytetty ennen korjausta),
4 pesistulokset.fi:n jälkikorjausten vuoksi. Ks. docs/validointi.md.

Sarakkeet vastaavat MasterLyonnit-taulua: Päivämäärä, Jakso, Vuoropari, team (=SisäpeliID), batter,
Tilanne, LyontiNro, Tyyppi, Pesäväli, Yritys, Tulos, Onnistuiko, Laiton, TapahtumaTeksti, X, Y.
"""
JAKSO={0:"1. Jakso",1:"2. Jakso",2:"Supervuoropari",3:"Kotiutuskilpailu"}

def _txt(x):
    if isinstance(x,str): return x
    if isinstance(x,dict) and "text" in x and x["text"] is not None: return str(x["text"])
    return ""

def ottelun_lyonnit(events):
    pvm=None
    for e in events:
        for s in e.get("events") or []:
            for t in s.get("texts") or []:
                if isinstance(t,dict) and "match-started" in t and pvm is None: pvm=t["match-started"][:10]
    rows=[]  # expanded sub-events
    for oo,e in enumerate(events):
        evs=e.get("events") or []
        r=(evs[0].get("runnersAtBases") if evs else None) or []
        ps=[str(k) for k in (1,2,3) if len(r)>k and r[k] is not None]
        tilanne="0-tilanne" if not ps else "-".join(ps)+" -tilanne"
        hit=e.get("hit")
        x=float(hit["x"]) if hit and hit.get("x") not in (None,"") else None
        y=float(hit["y"]) if hit and hit.get("y") not in (None,"") else None
        per=e.get("period"); inn=e.get("inning")
        jakso=JAKSO.get(per,"Super/Koti")
        try: vuoro=f"{int(inn)+1}. vuoro"
        except Exception: vuoro="0. vuoro"
        for s in (evs if evs else [None]):
            if s is None: raw=""
            else:
                tl=s.get("texts")
                raw=" ".join(_txt(t) for t in tl) if isinstance(tl,list) else _txt(s.get("text"))
            raw=(raw or "").lower()
            typ="Header" if ". lyönti" in raw else "Special" if ("harha" in raw or "kärp" in raw) else "Event" if raw!="" else "Ignore"
            rows.append(dict(oo=oo,id=e.get("id"),jakso=jakso,vuoro=vuoro,team=e.get("team"),batter=e.get("batter"),tilanne=tilanne,x=x,y=y,raw=raw,typ=typ))
    out=[]
    for i,r in enumerate(rows):
        if r["typ"] not in ("Header","Special"): continue
        fol=[]
        for q in rows[i+1:]:
            if q["typ"] in ("Header","Special"): break
            if q["typ"]=="Event": fol.append(q["raw"])
        comb=" | ".join(fol).replace(" | lyöntivuorossa","")
        res=r["raw"] if comb=="" else r["raw"]+" | "+comb
        palo="paloi" in res or "kärp" in res; haava="haavoittui" in res; vapaa="vapaa" in res
        eteni="eteni" in res or "juoksu" in res or vapaa
        tls="Palo" if palo else "Haavoittuminen" if haava else "Vapaataival" if vapaa else "Onnistuminen" if eteni else "Laiton" if "laiton" in res else "Tuottamaton"
        tyy="V" if vapaa else (("HH" if "harha" in r["raw"] else "K") if r["typ"]=="Special" else "L")
        pts=4 if ("koti" in res or "juoksu" in res) else 3 if "kolmos" in res else 2 if "kakkos" in res else 1 if "ykkös" in res else 0
        out.append(dict(r,LyontiNro=r["raw"].split(".")[0] if r["typ"]=="Header" else "S",Tyyppi=tyy,Tulos=tls,
                        Onnistuiko=1 if tls in("Onnistuminen","Vapaataival") else 0,Laiton=1 if tls=="Laiton" else 0,Teksti=res,pts=pts))
    # group like PQ (by id+OriginalOrder+... keys)
    g={}
    for o in out:
        k=(o["id"],o["oo"],o["jakso"],o["vuoro"],o["team"],o["batter"],o["LyontiNro"],o["Tyyppi"],o["tilanne"],o["x"],o["y"])
        g.setdefault(k,[]).append(o)
    res=[]
    for k,L in g.items():
        tl=[o["Tulos"] for o in L]
        lop="Palo" if "Palo" in tl else "Haavoittuminen" if "Haavoittuminen" in tl else "Onnistuminen" if "Onnistuminen" in tl else "Vapaataival" if "Vapaataival" in tl else "Tuottamaton"
        mp=max(o["pts"] for o in L)
        teks=" | ".join(dict.fromkeys(o["Teksti"] for o in L))
        res.append(dict(oo=k[1],Päivämäärä=pvm,Jakso=k[2],Vuoropari=k[3],team=k[4],batter=k[5],Tilanne=k[8],LyontiNro=k[6],Tyyppi=k[7],
            Pesäväli={4:"3-K",3:"2-3",2:"1-2",1:"0-1"}.get(mp,""),Yritys=1,Tulos=lop,Onnistuiko=max(o["Onnistuiko"] for o in L),
            Laiton=max(o["Laiton"] for o in L),TapahtumaTeksti=teks,X=k[9],Y=k[10]))
    res.sort(key=lambda r:r["oo"])
    return [r for r in res if r["LyontiNro"] is not None and r["Jakso"] not in ("Kotiutuskilpailu","Super/Koti")]
