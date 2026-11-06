# Mittarit

Lähde: pesistulokset.fi stats-tool, ottelukohtaiset rivit (`stats-tool/players` ja `stats-tool/teams` ilman `sum=1`), summattu kauden/vaiheen yli.

## Pelaaja
| Mittari | Kenttä | Huom |
| --- | --- | --- |
| O | matches | |
| K / L / T / YHT | homeruns / scorings / runs / K+L+T | Kunnarit vain kappaleina (ei yrityksiä) |
| KL / KLY / KL% | batpe_total_succeeded / batpe_total_tries | |
| KL0–KL3, KLY0–KLY3, KL%0–KL%3 | batpe_succeeded_n / batpe_tries_n | n = kärkietenijän lähtöpesä. KL3 = kotiutus 3. pesältä |
| palot0–3, kopit0–3 | batpe_outs_n / batpe_caughts_n | |
| LV | turns_at_bat | Lyöntivuorot |
| batadv / runpadv / runtadv | *_succeeded / *_tries | Järjestelmän omat luokitukset – vain raakalukuina |

## Joukkue
| Mittari | Laskenta |
| --- | --- |
| kotiutus% | pe_total_b3 / pe_tries_b3 |
| torjunta% | (pe_tries_b3_opponent − pe_total_b3_opponent) / pe_tries_b3_opponent |
| KL%, KL%0–3 | pe_total(_bn) / pe_tries_total (pe_tries_bn) |
| juoksut jaksoittain | runs_p0–p3 (+ _opponent) |
| (walks, wild_throws) | **Ei käytössä.** `walks` ei ole lukkarin vapaat (vain 0–3 per joukkue per kausi, oikeita vapaita ~3 per ottelu). `wild_throws`-kentän suunta (heittänyt vai hyötynyt joukkue) varmistamatta. |

## Lukkari
Lähde: pelaajarivin `defensive_position` = "L" (tasan yksi per joukkue per ottelu, ottelun kokoonpano). Lukkarille kohdistetaan joukkueen ottelukohtaiset `*_opponent`-luvut. Kesken ottelun tehdyt vaihdot eivät näy.

| Mittari | Laskenta |
| --- | --- |
| O, V–H | lukkarin aloittamat ottelut, `won` |
| Päästetyt / O | runs_opponent / O (ilman kotiutuskilpailua); jaksoittain runs_p0/p1_opponent |
| KL% v, KL%0–2 v | pe_total(_bn)_opponent / pe_tries(_bn)_opponent |
| Torjunta% | (pe_tries_b3_opponent − pe_total_b3_opponent) / pe_tries_b3_opponent |
| 3-tilanteet / O | rab3_opponent / O (vastustajan tilanteet, joissa etenijä 3. pesällä; ≥ KLY3) |
| K v / O | homeruns_opponent / O |

Ottelutapahtumista (6.11.2026, `ydin/lukkarit.py`, tallessa olevista `data/tapahtumat/<kausi>/`, ei uusia hakuja; kaudesta 2026, vain 1. ja 2. jakso):

| Mittari | Laskenta |
| --- | --- |
| vapaat, vapaat1, vapaat23, vapaatK | tapahtumat "sai vapaataipaleen väärien syöttöjen johdosta" lukkarin joukkueen puolustusvuoroissa, kohdepesän mukaan (1. / 2.–3. / kotipesään = juoksu) |
| karpaset, karpaset_l | "paloi kärpäsenä…" puolustusvuoroissa; _l = "…lukkarin toimesta" |

Tarkistus kausi 2026: 458/458 lukkaririviä löysi ottelunsa tapahtumista, vapaita 1 390 (≈3,0 / joukkue / ottelu), kärpäsiä 485.

## Validointi
- 3.10.2026: kausi 2026 runkosarja, 196 pelaajaa – 195 täsmää viralliseen kausisummaan (O, K, L, T, KL, KLY, KL3, KLY3); 1 ero korjattu (O = matches-kenttä).

## Lyöntiprofiili (pelaajakortti, 6.11.2026)
Lähde `data/out/lyonnit_<kausi>/p<id>.json` (kopioidaan sivustolle). Tilanne kärkietenijän mukaan: 0-tilanne, 1-tilanne, 2-tilanne (myös 1–2), takatilanne (kärki 3. pesällä).
Onnistui = kunnari, juoksu tai kärkietenijä eteni (sama kuin KPL Keskuksen Minun pelini). Matriisi palot (0/1/2) × lyönti (1./2./3.), sarjan vertailuluvut `lyontipohja` (sivu.py). Laittomat-% ja onnistumisen hetki lyönneittäin. Kartalla kenttään osuneet lyönnit (laittomat pois), koppi ja haava samassa ryhmässä.

## YDIN 2026:n mittarit, joita ei saa ilman lyöntikohtaista dataa
Ketjut (peräkkäiset onnistumiset), lyöntikartta/rajalyönnit (X/Y), palo-% kaikista lyönneistä, tilannekohtaiset onnistumiset (1-, 2-, 1-2-, 2-3-tilanne…), ajolähtö, lukkarin kärpäset pelaajatasolla.
Korvaavat: KL0–KL3 (pesäkohtaiset kärkilyönnit), joukkueen vapaat ja harhaheitot, juoksut jaksoittain.
