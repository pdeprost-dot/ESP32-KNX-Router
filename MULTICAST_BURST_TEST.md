# Test multicast borne — 21 octobre 2026

## Garde-fous

Le firmware `0.6.1` est reste strictement passif pendant tout l'essai :
`ROUTING_ARMED=0`, IP vers TP en mode passif, TP vers IP et tunnels inactifs,
NanoBCU en Busmon. Les datagrammes de diagnostic ont un format propre de huit
octets (`KXDG`, version, serie, sequence, total). Ils sont interceptes avant la
validation KNXnet/IP et ne peuvent donc jamais entrer dans la file TP.

Le PC a emis depuis `192.0.2.123`, avec cette adresse imposee comme
`IP_MULTICAST_IF`, vers `224.0.23.12:3671`, TTL 1. TShark sur `Wi-Fi 3` a capture
les 120 paquets attendus, sequences 0 a 19 pour chacune des six series. La
capture de reference est `udp_multicast_bursts_final_0.6.1.pcapng` et le script
reproductible est `tools/Test-KnxMulticastBurst.ps1`.

## Resultats

| Serie | Cadence | Consultation `/knx` | PC capture | ESP32 | Sequences absentes sur l'ESP32 | Passage UDP max | Vidage max/passage | `ESP_BASE.loop()` max | Heap avant/apres |
|---:|---:|:---:|---:|---:|---|---:|---:|---:|---:|
| 1 | 100 ms | non | 20/20 | 6/20 | 1,3,5,7-10,12-15,17-19 | 13 101 us | 1 | 13 529 us | 209468 / 209212 |
| 2 | 10 ms | non | 20/20 | 5/20 | 0-5,7-8,10,12,15-19 | 11 634 us | 4 | 11 537 us | 209232 / 209220 |
| 3 | 2 ms | non | 20/20 | 5/20 | 1-4,6-7,9-10,12-13,15-19 | 11 788 us | 4 | 11 666 us | 209220 / 209236 |
| 4 | 100 ms | oui | 20/20 | 6/20 | 0,2,5,9-19 | 6 715 062 us | 4 | 6 714 946 us | 209208 / 209224 |
| 5 | 10 ms | oui | 20/20 | 5/20 | 4-10,12-19 | 6 437 790 us | 4 | 6 437 673 us | 209096 / 209236 |
| 6 | 2 ms | oui | 20/20 | 2/20 | 0-11,13-17,19 | 6 276 312 us | 1 | 6 276 207 us | 209236 / 209212 |

Aucun doublon ni paquet KXDG invalide n'a ete observe. Le compteur d'erreurs
applicatives KNX/IP est reste a zero. `WiFiUDP` n'expose pas ici les compteurs
de debordement de la file lwIP : une perte avant `parsePacket()` ne peut donc
pas etre classee directement comme debordement.

La heap finale est de 209224 octets, contre 212540 juste apres le redemarrage.
Apres echauffement des pages elle oscille autour de 209,2 kio sans baisse
monotone entre les series. Le minimum historique atteint 184012 octets pendant
les consultations Web, puis la memoire libre remonte : aucune fuite durable
n'est mise en evidence par cet essai.

## Inspection de la desserte

`serviceIpListener()` ne traite pas un seul datagramme par tour : sa boucle en
traite au plus quatre. La limite a bien ete atteinte dans quatre series. Une
fois le controle rendu, les tours suivants sont rapides, mais une rafale plus
grande que la file UDP peut deja etre perdue.

L'ordre courant est `espBase.loop()` puis `serviceIpListener()`. Dans ESP_BASE
2.4.1, `espBase.loop()` appelle le serveur Web synchrone
`WebServer::handleClient()`. Une consultation de `/knx` a ainsi bloque le tour
principal entre 6,28 et 6,72 secondes. La quasi-identite entre cette duree et
l'intervalle maximal de desserte UDP prouve la correlation Web.

Il n'existe qu'une instance `WiFiUDP`, manipulee par le seul contexte Arduino
`loop()`. Les callbacks Wi-Fi ne font que mettre a jour des compteurs. Les
actions Web d'arret/reinscription sont elles aussi executees dans ce meme
contexte, avant le retour vers `serviceIpListener()` : aucune lecture
concurrente de l'instance UDP n'a ete trouvee.

## Conclusion et correction minimale proposee

Le blocage Web explique l'interruption de desserte de plusieurs secondes et
aggrave la rafale a 2 ms (2/20 au lieu de 5/20). Il n'explique toutefois pas la
perte de fond : sans Web, a 100 ms, la desserte revient au plus tard en 13,1 ms
et ne vide jamais plus d'un paquet, alors que 14 paquets sur 20 n'atteignent
pas l'application. Le transport multicast Wi-Fi reste donc un facteur distinct
et dominant.

La correction applicative minimale a evaluer est de desservir UDP avant et
apres `espBase.loop()`, et de remplacer la limite fixe de quatre par un vidage
borne en temps et en nombre. Elle reduira la fenetre avant un traitement Web,
mais ne peut pas supprimer les six secondes pendant lesquelles le serveur
synchrone garde la main. Une tache RX proprietaire unique avec file bornee est
la correction robuste si les pages doivent rester synchrones ; elle ne devra
jamais partager `WiFiUDP` entre deux contextes.

Avant cette evolution plus importante, le test discriminant suivant reste une
emission identique depuis un PC relie en Ethernet. Il permettra de separer le
trajet Wi-Fi vers Wi-Fi du recepteur ESP32. Aucun changement UniFi ni aucune
reinscription periodique n'est justifie par les seules mesures presentes.
