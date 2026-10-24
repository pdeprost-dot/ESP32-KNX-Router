# Validation KXL3 entre deux ESP sur le même TP1

Date : 24 octobre 2026

Branche : `feature/knx-intersite-l3`

Base du développement : `e3f343c`

## Périmètre et sécurité de l'essai

L'Olimex Ethernet et la Wemos Wi-Fi sont raccordées au même segment KNX TP1,
avec un NCN5130 physique chacune. Le N146/03 n'a pas été modifié. Aucun
télégramme applicatif n'a été généré pour cette campagne : seul le trafic TP1
déjà présent a été observé.

Le firmware 0.15.5 ajoute `KXL3_MONITOR_ONLY`. Dans ce mode, la tâche KXL3 reste
propriétaire du socket UDP, valide l'enveloppe et la trame TP1, applique
l'anti-doublon et envoie l'ACK KXL3, mais ne dépose jamais de `TpEvent` dans la
file du moteur KNX. L'activation monitor-only ne demande pas le mode émission
normal au NCN5130. Le mode `BRIDGE` reste distinct dans le modèle de
configuration et n'a pas été utilisé.

## Configuration de la campagne (valeurs anonymisées)

| Élément | Olimex | Wemos |
|---|---|---|
| Firmware | 0.15.5 | 0.15.5 |
| Réseau | Ethernet, `192.0.2.10` | Wi-Fi, `192.0.2.11` |
| Site KXL3 | `10000001` | `10000002` |
| Pair attendu | `10000002`, `192.0.2.11:3672` | `10000001`, `192.0.2.10:3672` |
| Mode | `MONITOR_ONLY` | `MONITOR_ONLY` |
| NCN5130 pendant l'essai | Busmon passif | Mode normal déjà requis par le profil tunnel existant |

La configuration KXL3 a été enregistrée dans la clé NVS séparée `l3config`.
Après OTA, le transport était inactif et a nécessité une activation Web
explicite sur chaque appareil.

## Déploiement et contrôles préalables

- Web `/knx`, `/knx-advanced`, `/logs` et `/ota` accessibles sur les deux ESP ;
- NCN5130 reconnu sur les deux cartes, UART 38400/8E1 sans erreur matérielle ;
- OTA Ethernet Olimex : PASS ;
- OTA Wi-Fi Wemos : PASS ;
- retour réseau et version 0.15.5 : PASS ;
- image Olimex : 1 163 536 octets, RAM statique 100 944 octets ;
- image Wemos déployée : 1 127 488 octets, RAM statique 100 904 octets ;
- ESP_BASE reste en version locale 2.4.2, sans modification.

## Campagne matérielle

Fenêtre observée : environ 20 minutes, de 19:00:49 à 19:21:08, sans redémarrage
ni réinscription forcée. Les deux appareils voyaient le même bus ; les nombres
de trames TP locales diffèrent donc des nombres reçus du pair et ne constituent
pas une mesure de perte TP.

| Compteur final | Olimex | Wemos |
|---|---:|---:|
| DATA KXL3 émis | 41 | 24 |
| DATA KXL3 reçus et validés | 24 | 41 |
| DATA consommés en monitor-only | 24 | 41 |
| ACK KXL3 reçus | 41 | 24 |
| ACK KXL3 émis | 24 | 41 |
| Timeouts ACK | 0 | 0 |
| Erreurs d'émission / file TX pleine | 0 / 0 | 0 / 0 |
| Malformés / mauvais pair / doublons / origine propre | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| File RX pleine | 0 | 0 |
| RTT ACK min / moyen / max | 6 131 / 17 944 / 65 916 µs | 5 232 / 12 176 / 31 091 µs |
| KXL3 mis en file TP | **0** | **0** |
| Confirmations / échecs TP issus de KXL3 | **0 / 0** | **0 / 0** |

Bilan agrégé : 65 DATA émis, 65 DATA reçus, 65 ACK correspondants et aucun
timeout observé. Les boot IDs distants et les séquences ont été relevés sur les
deux appareils et ont progressé sans rejet d'identité.

## Ressources et TP1

| Mesure finale avant arrêt | Olimex | Wemos |
|---|---:|---:|
| Heap libre | 125 504 octets | 107 180 octets |
| Heap minimum natif | 109 932 octets | 82 424 octets |
| Marge pile loop/Web | 2 156 octets | 2 140 octets |
| Marge pile tâche UDP KNXnet/IP | 2 656 octets | 2 560 octets |
| Marge pile tâche NCN5130 | 3 976 octets | 3 976 octets |
| Trames NCN valides / invalides | 38 / 0 | 23 / 0 |
| Erreurs UART parité / trame / débordement | 0 / 0 / 0 | 0 / 0 / 0 |
| Pertes files événements / commandes NCN | 0 / 0 | 0 / 0 |

La rotation du journal UART de la Wemos a augmenté pendant l'essai ; il s'agit
de l'écrasement attendu d'un anneau d'affichage borné, pas d'une perte de la file
d'événements NCN5130.

## Preuve de non-réinjection

- le branchement `MONITOR_ONLY` est placé dans la tâche KXL3 avant l'unique
  `xQueueSend(rxQueue_, ...)` menant au moteur KNX ;
- les 65 DATA reçus ont tous augmenté `rx_monitor_only` ;
- `tp_queued_from_l3`, `tp_confirmed_from_l3` et `tp_failed_from_l3` sont restés
  à zéro sur les deux ESP pendant toute la fenêtre ;
- aucun passage KXL3 vers `SendTp`, UART2 ou le chemin NCN5130 n'a été observé ;
- aucune erreur, répétition KXL3 ou boucle n'a été observée ;
- le test déterministe vérifie la présence et l'ordre de cette garde dans le
  chemin compilé.

Cette campagne démontre l'absence de réinjection par le firmware et ses
compteurs. Elle ne constitue pas une capture électrique indépendante du bus.
Une future validation du mode `BRIDGE` devra employer deux segments TP séparés.

## Non-régression

PASS : protocole KXL3, formats standard et étendu, trames malformées, UDP
localhost bidirectionnel, ACK, perte, doublons, désordre, redémarrage, boucle
trois sites, parseur NCN5130, séquence d'émission, tunneling, routing,
filtrage, anti-écho, arbitrage, cinq tunnels et simulateur TP1.

PASS : compilation `wemos_d1_mini32` et `olimex_poe_iso_16mb`.

## État final

- KXL3 désactivé sur les deux appareils ;
- sockets KXL3 fermés et ACK en attente à zéro ;
- Olimex et Wemos en Busmon passif ;
- serveur de tunneling Wemos désactivé pour satisfaire l'état final passif ;
- configuration des pairs KXL3 conservée en NVS, mais jamais réactivée au boot ;
- routage multicast inchangé et passif ;
- N146/03 inchangés.

## Limites restantes

- pas de validation à travers un VPN L3 ;
- pas de validation du mode `BRIDGE` entre deux segments TP indépendants ;
- pas d'authentification cryptographique KXL3 ;
- les deux observateurs partageant le même TP, leurs comptages locaux peuvent
  différer selon leur mode NCN5130 et leur instant de démarrage.
