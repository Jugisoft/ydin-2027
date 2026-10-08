"""Tunnusluvut ottelukohtaisista tilastoriveistä (pesistulokset.fi stats-tool).
Termit pesistulokset.fi-standardin mukaan – ks. docs/mittarit.md.

Pelaaja: O, K, L, T, YHT, KL, KLY, KL%, KL0–KL3 (numero = kärkietenijän LÄHTÖPESÄ; KL3 = kotiutus),
         lyöntivuorot (turns_at_bat), etulyönnit/etenemiset (batadv, runpadv, runtadv – vain raakalukuina).
Joukkue: kotiutus% = KL3 omista yrityksistä, torjunta% = vastustajan epäonnistuneet KL3-yritykset,
         kärkilyönnit pesittäin, juoksut jaksoittain, vapaat (walks) ja harhaheitot (wild_throws).
"""
from collections import defaultdict

def i(v):
    try: return int(v or 0)
    except (TypeError, ValueError): return 0

def pct(a, b, nd=1):
    return round(100.0 * a / b, nd) if b else None

PELAAJA_SUMMAT = ["homeruns", "scorings", "runs", "scorings_tries", "runs_tries", "turns_at_bat", "batpe_total_succeeded", "batpe_total_tries",
                  "batadv_succeeded", "batadv_tries", "runpadv_succeeded", "runpadv_tries", "runtadv_succeeded", "runtadv_tries"] + \
                 [f"batpe_{x}_{n}" for x in ("succeeded", "tries", "outs", "caughts") for n in range(4)]

def pelaajat(rivit):
    """rivit: stats-tool/players ilman sum=1 -> {player_id: summat}"""
    S = defaultdict(lambda: defaultdict(int)); ott = defaultdict(int); jj = defaultdict(lambda: defaultdict(int))
    for r in rivit:
        p = r["player_id"]; ott[p] += i(r.get("matches"))  # virallinen otteluluku (matches-kenttä)
        for t in r.get("team_ids") or [r.get("team_id")]: jj[p][t] += 1
        for k in PELAAJA_SUMMAT: S[p][k] += i(r.get(k))
    out = {}
    for p, s in S.items():
        K, L, T = s["homeruns"], s["scorings"], s["runs"]
        d = {"O": ott[p], "K": K, "L": L, "T": T, "YHT": K + L + T,
             "KL": s["batpe_total_succeeded"], "KLY": s["batpe_total_tries"], "KL%": pct(s["batpe_total_succeeded"], s["batpe_total_tries"]),
             "LV": s["turns_at_bat"], "joukkue": max(jj[p], key=jj[p].get),
             # L% = lyödyt / lyöntiyritykset (etenijä kotiin lyönnillä), T% = tuodut / juoksuyritykset
             "LY": s["scorings_tries"], "TY": s["runs_tries"], "L%": pct(L, s["scorings_tries"]), "T%": pct(T, s["runs_tries"])}
        for n in range(4):
            d[f"KL{n}"] = s[f"batpe_succeeded_{n}"]; d[f"KLY{n}"] = s[f"batpe_tries_{n}"]
            d[f"KL%{n}"] = pct(s[f"batpe_succeeded_{n}"], s[f"batpe_tries_{n}"])
            d[f"palot{n}"] = s[f"batpe_outs_{n}"]; d[f"kopit{n}"] = s[f"batpe_caughts_{n}"]
        d.update({k: s[k] for k in ("batadv_succeeded", "batadv_tries", "runpadv_succeeded", "runpadv_tries", "runtadv_succeeded", "runtadv_tries")})
        out[p] = d
    return out

JOUKKUE_SUMMAT = ["runs", "runs_opponent", "scorings", "scorings_opponent", "homeruns", "homeruns_opponent",
                  "walks", "walks_opponent", "wild_throws", "wild_throws_opponent", "periods", "periods_opponent",
                  "pe_total", "pe_tries_total", "pe_total_opponent", "pe_tries_total_opponent"] + \
                 [f"{a}{n}{o}" for a in ("pe_total_b", "pe_tries_b") for n in range(4) for o in ("", "_opponent")] + \
                 [f"runs_p{n}{o}" for n in range(4) for o in ("", "_opponent")]

def joukkueet(rivit):
    S = defaultdict(lambda: defaultdict(int)); O = defaultdict(int); V = defaultdict(int)
    for r in rivit:
        t = r["team_id"]; O[t] += 1; V[t] += i(r.get("won"))
        for k in JOUKKUE_SUMMAT: S[t][k] += i(r.get(k))
    out = {}
    for t, s in S.items():
        d = {"O": O[t], "voitot": V[t], **{k: s[k] for k in JOUKKUE_SUMMAT}}
        d["kotiutus%"] = pct(s["pe_total_b3"], s["pe_tries_b3"])
        d["torjunta%"] = pct(s["pe_tries_b3_opponent"] - s["pe_total_b3_opponent"], s["pe_tries_b3_opponent"])
        d["KL%"] = pct(s["pe_total"], s["pe_tries_total"])
        for n in range(4): d[f"KL%{n}"] = pct(s[f"pe_total_b{n}"], s[f"pe_tries_b{n}"])
        out[t] = d
    return out
