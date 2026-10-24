# Protocole KNX Intersite L3 — KXL3 v1

## Objet et périmètre

KXL3 transporte une trame TP1 complète entre routeurs ESP-KNX par UDP unicast.
Il ne transporte ni Ethernet, ni multicast KNXnet/IP, et n'intègre aucun client
VPN. Il peut donc emprunter un LAN routé, WireGuard ou OpenVPN TUN.

Le payload canonique est la trame TP1 sur le fil, FCS inclus, de 8 à 263 octets.
Ce choix conserve les contrôles KNX, les adresses, le hop count, l'APDU et les
données LTE opaques. La réinjection reconstruit une cEMI validée, applique les
règles topologiques et décrémente le hop count KNX séparément du TTL KXL3.

## Format binaire v1

Tous les entiers multi-octets sont en ordre réseau (big endian).

| Offset | Taille | Champ | Règle |
|---:|---:|---|---|
| 0 | 4 | Magic | ASCII `KXL3` |
| 4 | 1 | Version | `1` |
| 5 | 1 | Type | `1=DATA`, `2=ACK` |
| 6 | 1 | Header length | `36` |
| 7 | 1 | TTL intersites | 1..255, valeur émise par défaut 4 |
| 8 | 4 | Origin site ID | identité stable du site où DATA est née |
| 12 | 4 | Sender site ID | pair immédiat ayant émis ce datagramme |
| 16 | 4 | Boot ID | aléatoire non nul à chaque démarrage |
| 20 | 4 | Sequence | compteur non nul de l'émetteur |
| 24 | 4 | Acknowledged sequence | 0 pour DATA, séquence DATA pour ACK |
| 28 | 2 | Payload length | 8..263 pour DATA, 0 pour ACK |
| 30 | 2 | Flags | réservé, doit être 0 en v1 |
| 32 | 4 | CRC32 | IEEE CRC32 de l'enveloppe et du payload, champ CRC mis à 0 |
| 36 | variable | Payload | trame TP1 complète pour DATA |

Taille maximale du datagramme : 299 octets. Une version, un type, un flag, une
longueur ou un FCS inconnu/invalide entraîne un rejet avant mise en file.

## États et activation

Le transport possède les états `INACTIF`, `ATTENTE RÉSEAU`, `SOCKET OUVERT`.
Une configuration NVS valide n'active jamais le service au démarrage ou après
OTA. L'activation doit être demandée explicitement sur `/knx-intersite`.

Deux modes sont distincts dans la configuration version 2 :

- `MONITOR_ONLY` valide, compte et acquitte les DATA, mais ne les expose jamais
  à la file du moteur TP ;
- `BRIDGE` remet les DATA validés au moteur de routage et à son arbitrage.

La configuration Web du firmware 0.15.5 enregistre volontairement
`MONITOR_ONLY` pour la campagne sur bus TP commun. Une activation monitor-only
ne fait pas quitter le NCN5130 du Busmon passif.

À la désactivation, le socket est fermé et le cache volatile est vidé. Les
files ne sont jamais persistées et aucun paquet n'est rejoué après redémarrage.
Une désactivation explicite ou une perte du transport réseau purge aussi les files
KXL3 et les ACK en attente : une réactivation ne rejoue donc aucun ancien DATA.

## Séquences, ACK et disponibilité

Chaque DATA reçoit un ACK applicatif reprenant sa séquence. Les ACK servent au
diagnostic de livraison au pair, pas à confirmer une émission TP1. Trois notions
restent distinctes :

- ACK KXL3 : datagramme accepté par le pair ;
- `U_L_Data.con` : résultat local du NCN5130 ;
- acquittement TP1 : comportement du média KNX.

Un ACK absent après 3 secondes incrémente `ackTimeouts`. Le POC ne retransmet
jamais automatiquement une commande KNX afin d'éviter une seconde action.

## Anti-boucle et anti-doublons

La clé `(origin site, boot ID, sequence)` est mémorisée dans un cache circulaire
de 32 entrées. Un doublon est acquitté mais n'est pas réinjecté. Un paquet dont
l'origine est le site local est rejeté. L'adresse IPv4, le port et `sender site`
doivent correspondre à un pair configuré.

Le TTL KXL3 est indépendant du hop count KNX. Le POC à un pair ne retransmet pas
un paquet KXL3 vers un troisième site. Le format distingue toutefois origine et
émetteur immédiat pour permettre un futur transit en étoile, qui devra décrémenter
le TTL à chaque saut sans modifier la clé d'origine.

## Files et arbitrage

- file locale TP→L3 : 8 éléments par transport, politique `drop newest` ;
- file L3→moteur KNX : 8 éléments, politique `drop newest` ;
- cache doublons : 32 clés ;
- suivi ACK : 8 émissions, sans stockage persistant ;
- maximum configuré : quatre pairs, un seul pair utilisé par le POC initial.

En configuration multi-pair, le premier pair examiné tourne à chaque trame locale,
afin qu'une file saturée ne favorise pas toujours le même emplacement.

La tâche `knxL3` est l'unique propriétaire de son socket UDP. UART2 reste la
propriété exclusive de la tâche NCN5130. Une trame distante rejoint la file et
l'arbitrage existants ; elle ne dispose d'aucun accès direct à UART2.

## Routage Route all du POC

Les tables S-Mode et un éventuel filtrage LTE ne sont pas appliqués à KXL3. Une
trame distante doit néanmoins être valide, avoir un hop count KNX non nul, ne pas
usurper l'adresse du routeur et respecter la topologie pour une destination
individuelle. Le hop count KNX est décrémenté avant émission TP1.

L'écho physique d'une émission issue de KXL3 est reconnu par l'anti-écho KNX
existant et ne repart pas vers le pair. Les répétitions KNX différentes ne sont
pas supprimées indistinctement.

## Sécurité

KXL3 v1 n'offre ni chiffrement, ni authentification cryptographique. Le site ID
déclaré n'est pas une preuve d'identité. Le POC doit être limité à des adresses
IPv4/ports explicitement configurés, derrière un pare-feu, et utilisé à travers
un VPN L3 ou une protection équivalente entre sites.

Le firmware ne découvre aucun pair, n'émet aucun broadcast et n'ouvre aucune
règle NAT ou pare-feu. Une évolution ultérieure devra authentifier l'enveloppe
(clé prépartagée ou certificats), protéger le rejeu au-delà du cache et prévoir
une rotation de clés.

## Limites v1

- aucune retransmission automatique ;
- aucune fragmentation IP applicative ;
- aucun transit multi-hop entre pairs dans le firmware ;
- aucune authentification forte ;
- pas de filtre LTE ou de table S-Mode ;
- état de disponibilité déduit des ACK et non d'un keepalive ;
- concurrence multi-pair conçue et bornée, mais pas validée sur quatre ESP.
