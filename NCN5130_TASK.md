# Tache NCN5130 dediee (firmware 0.8.0)

## Architecture

`knxNcnRx` est l'unique proprietaire actif d'UART2. Elle ouvre le port en
38400/8E1, polarite normale, RX GPIO16 et TX GPIO17. Les handlers Web ne
lisent et n'ecrivent jamais l'UART : ils placent les demandes de diagnostic
dans une file bornee de 8 commandes. La tache publie les trames et services
locaux dans une file bornee de 24 evenements. Le thread principal ne consomme
que ces evenements et des instantanes proteges.

Le firmware 0.8.0 reste strictement passif : `ROUTING_ARMED=0`, tunnels
arretes, TP vers IP inactif et aucune emission applicative TP. La seule
sequence transmise au demarrage est locale au NCN5130 : `U_Reset.req`,
`U_State.req`, puis `U_Busmon.req` apres validation des reponses.

## Delimitation des trames

La fin normale d'une trame n'est plus deduite de `available()`, d'un silence
entre deux appels de la boucle Web, ni de la valeur `CC`. Apres les sept
premiers octets, la longueur attendue est calculee d'apres le format TP :

- trame standard : `8 + (octet[5] & 0x0f)` octets, FCS compris ;
- trame etendue : `9 + octet[6]` octets, FCS compris.

Le XOR de toute la trame doit valoir `FF`. Un silence de 20 ms ne sert que de
garde de resynchronisation d'une trame incomplete. Un octet `CC` rencontre
dans les donnees reste donc une donnee. Les services locaux, etats et
confirmations ne sont classes comme tels qu'entre deux trames.

Reference primaire : fiche technique ON Semiconductor NCN5130, sections
Host Controller Interface et Bus Monitor Service :
https://www.onsemi.com/download/data-sheet/pdf/ncn5130-d.pdf

## Validation reelle du 21 octobre 2026

Pendant douze consultations successives de `/knx` et du trafic TP genere par
un interrupteur KNX :

| Mesure | Resultat |
|---|---:|
| Trames TP valides | 122 |
| Trames invalides / resynchronisations | 0 / 0 |
| File evenements pleine / commandes pleines | 0 / 0 |
| Erreurs UART parite / trame / debordement | 0 / 0 / 0 |
| Plus grand intervalle de la tache NCN | 9 127 us |
| Marge de pile de la tache NCN | 4 696 octets |
| Duree maximale mesuree de `/knx` | 17 012 280 us |
| Etat final du parseur | 0 / 0 octet courant/attendu |

Les trames observees restent distinctes (9 ou 10 octets selon la longueur
NPDU) et leur FCS est valide. Aucune concatenation n'est apparue alors que le
traitement HTTP restait bloque jusqu'a 17 s. Les 106 ecrasements du journal TP
et les 1 049 ecrasements du journal UART sont la rotation normale des anneaux
d'affichage bornes ; ce ne sont ni des pertes UART ni des files pleines.

Apres stabilisation, le heap libre etait de 174 908 octets et le minimum
historique de 152 492 octets. Le binaire utilise 1 028 425 octets sur un slot
OTA de 1 835 008 octets, soit 806 583 octets de marge ; la RAM statique est de
65 144 octets sur 327 680.

Le test `tools/test_ncn5130_rx_parser.py` verifie independamment une trame
standard capturee, deux trames consecutives, un octet `CC` dans les donnees
et le calcul de longueur d'une trame etendue.
