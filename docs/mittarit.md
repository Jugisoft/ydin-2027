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
| vapaat, harhaheitot | walks, wild_throws (+ _opponent) |

## Validointi
- 3.10.2026: kausi 2026 runkosarja, 196 pelaajaa – 195 täsmää viralliseen kausisummaan (O, K, L, T, KL, KLY, KL3, KLY3); 1 ero korjattu (O = matches-kenttä).

## YDIN 2026:n mittarit, joita ei saa ilman lyöntikohtaista dataa
Ketjut (peräkkäiset onnistumiset), lyöntikartta/rajalyönnit (X/Y), palo-% kaikista lyönneistä, tilannekohtaiset onnistumiset (1-, 2-, 1-2-, 2-3-tilanne…), ajolähtö, lukkarin kärpäset pelaajatasolla.
Korvaavat: KL0–KL3 (pesäkohtaiset kärkilyönnit), joukkueen vapaat ja harhaheitot, juoksut jaksoittain.
