# Bilan des essais

## 2026-10-22 - tunnel ETS6 unicast (0.9.0)

- `tools/test_knx_tunnel_protocol.py` : CONNECT_RESPONSE et CRD `1.1.254`,
  TUNNELING_ACK et cEMI transparent conformes aux vecteurs indépendants ;
- `tools/test_ncn5130_rx_parser.py` : trames standard, étendues, consécutives et
  octet `CC` dans les données toujours valides ;
- compilation : RAM statique 65 496 / 327 680 octets (20,0 %), firmware
  1 042 249 / 1 835 008 octets (56,8 %), marge OTA 792 759 octets ;
- après OTA : version 0.9.0, Wi-Fi `example-wifi`, `192.0.2.156`, Busmon restauré
  (`TX 01`, `RX 03`, `TX 02`, `RX 07`, `TX 05`), aucune erreur UART ;
- tunnel désactivé par défaut, aucune session et aucune émission TP.
- après le second OTA, un redémarrage électrique a été nécessaire pour retrouver
  `192.0.2.156`; la version 0.9.0 est ensuite revenue sur `example-wifi` avec un
  RSSI de -48 dBm et les routes `/knx`, `/knx-config` et `/ota` en HTTP 200 ;
- DESCRIPTION_RESPONSE reçu de `192.0.2.156:3671` : adresse interface
  `1.1.253`, familles Core 1 et Tunneling 1 ;
- CONNECT_REQUEST link-layer envoyé tunnel désactivé : CONNECT_RESPONSE
  `06 10 02 06 00 08 00 27`, refus attendu `E_NO_MORE_CONNECTIONS` ;
- après ces requêtes passives : Busmon conservé, dialogue initial UART limité à
  `01/03/02/07/05`, aucune erreur UART et aucune émission applicative TP.

### Diagnostic du bouton Test ETS6

La capture `ets6_handshake_live.pcapng` établit la séquence suivante :

1. ETS (`192.0.2.123:60190`) envoie un CONNECT_REQUEST link-layer complet ;
2. l'ESP32 répond avec succès sur le canal 1, endpoint
   `192.0.2.156:3671`, CRD tunnel `1.1.254` ;
3. ETS envoie immédiatement un second CONNECT_REQUEST court de type
   `DEVICE_MGMT_CONNECTION (0x03)` ;
4. cette version l'ignore, puis conserve le canal 1 ;
5. les nouvelles demandes tunnel reçoivent `0x24 E_NO_MORE_CONNECTIONS`.

Le compteur observé était 3 connexions, 21 refus, 2 expirations et aucun
TUNNELING_REQUEST. Le canal résiduel a été libéré explicitement et Busmon a été
restauré. Un refus n'incrémente pas le canal et ne crée pas de session. La pile
thelsing de référence traite séparément les types 3 et 4 ; la prise en charge
du service de gestion reste à implémenter, sans augmenter le nombre de tunnels.

## 2026-10-21 - optimisation HTTP `/knx` (0.8.2)

- reference 0.8.0 : 24 942 octets en 11 232 a 11 581 ms ;
- 455 fragments HTML applicatifs identifies sur la page post-redemarrage ;
- regroupement fixe de 1 024 octets : 12 appels applicatifs, 27 appels totaux
  en comptant le cadre ESP_BASE, 349 a 1 104 ms sur six chargements ;
- construction mesuree 8 358 us, envoi 266 391 us, mutex 43 us au total et
  0 us pendant l'envoi ;
- six rafales UDP de 20 paquets a 100/10/2 ms, avec et sans `/knx` : toutes
  recues et traitees 20/20, sans saturation de file ;
- mode passif confirme : `ROUTING_ARMED=0`, tunnels et emission TP inactifs.

Voir [HTTP_KNX_PERFORMANCE.md](HTTP_KNX_PERFORMANCE.md).

Validation complete avec journaux remplis : 41 trames TP valides, reponse de
25 481 octets, 20 chargements Web en 516 a 769 ms apres le premier acces,
aucune perte de file et marge pile Web stable a 1 980 octets.

Deux repetitions multicast sans reinscription ont echoue partiellement : 4 a
11 paquets recus sur 20 selon la cadence, avec ou sans Web. La file UDP est
restee vide de saturation et les erreurs de lecture a zero. L'essai multicast
IP vers TP n'est donc ni prepare ni arme.

## 2026-10-21 - reception NCN5130 independante du Web (0.8.0)

- UART2 possede exclusivement par la tache `knxNcnRx`, 38400/8E1 normal,
  RX GPIO16 et TX GPIO17.
- Douze chargements de `/knx` pendant du trafic TP reel : 122 trames valides,
  aucune trame invalide, resynchronisation, erreur UART ou saturation de file.
- Blocage HTTP maximal : 17,012 s ; intervalle maximal de desserte UART :
  9,127 ms ; marge de pile de la tache : 4 696 octets.
- Test logiciel : `python tools/test_ncn5130_rx_parser.py`.
- Securite verifiee : `ROUTING_ARMED=0`, mode passif, TP vers IP et tunnels
  inactifs, aucune emission applicative TP.

Voir [NCN5130_TASK.md](NCN5130_TASK.md) pour les mesures et la delimitation.

Date : 2026-10-20 (Europe/Paris)

## Reprise après rétablissement de la masse — 0.4.3

Les essais 0.4.1/0.4.2 ne sont pas utilisés pour conclure sur le matériel : une
masse déconnectée a été trouvée puis rétablie. Le firmware 0.4.3 a été compilé,
déployé par OTA et redémarré avec UART2 en polarité normale, 19200/8E1,
RX GPIO16 et TX GPIO17. La capture commence avant l'initialisation d'ESP_BASE.

Après remise à zéro explicite des compteurs et journaux, la séquence complète
suivante a été relevée :

```
+48867 ms TX:01
+48869 ms RX:FE
+51867 ms TX:01
+51869 ms RX:FE
+54867 ms TX:01
+54869 ms RX:FE
+61305 ms TX:01
+61309 ms RX:FE
+64305 ms TX:01
+64308 ms RX:FE
```

Chaque `U_Reset.req` (`01`) a donc été suivi d'un unique `FE`, après 2, 2, 2,
4 et 3 ms. Le saut de chronologie entre 54 869 et 61 305 ms correspond a une
consultation HTTP synchrone de la page, qui retarde la boucle applicative ; il
ne correspond pas a une perte du journal. Bilan : 5 TX, 5 RX, 0
`U_Reset.ind`, 0 `U_State.ind`, 0 trame TP, 0 perte sur 192 emplacements.

La réponse de reset attendue n'ayant pas été reconnue, le verrou de séquence a
correctement interdit l'émission de `U_State.req` et `U_Busmon.req`. Aucun
changement de débit ou de polarité n'a été effectué. L'écoute KNXnet/IP est
restée active (`224.0.23.12:3671`) ; le routage et les tunnels sont restés
inactifs avec `ROUTING_ARMED=0`.

## Essai de polarité inversée après réparation — 0.4.4

La version 0.4.4 ajoute les compteurs d'erreurs UART matériels exposés par
`HardwareSerial::onReceiveError`, sans modifier la reconnaissance de
`U_Reset.ind` : seul `03` reste accepté. Après OTA, le diagnostic normal au
démarrage a reproduit six fois `TX:01 RX:FE`, avec zéro erreur UART.

L'essai isolé en polarité inversée, toujours à 19200/8E1 sur GPIO16/17, a donné
la capture intégrale suivante :

```
+32207 RX:00  TX:01  +32209 RX:07 RX:00
+35207 TX:01  +35209 RX:47 RX:00
+38207 TX:01  +38209 RX:47 RX:00
+41207 TX:01  +41209 RX:47 RX:00
+44207 TX:01  +44209 RX:47 RX:00
+47207 TX:01  +47209 RX:47 RX:00
```

Compteurs pendant cet essai : 6 erreurs de parité, 0 erreur de trame, 0
débordement FIFO, 0 perte de journal, 0 `U_Reset.ind`. La polarité normale a
ensuite été restaurée. Elle a de nouveau produit six fois `TX:01 RX:FE` ; le
compteur de parité est resté à 6, donc aucune nouvelle erreur n'est apparue en
mode normal.

`FE` demeure une donnée brute non valide. Sa relation exacte de complément
avec `01` rend plausible un écho inversé ou un chemin électrique inversant,
mais ne permet pas de distinguer à elle seule un écho matériel, une sortie du
NanoBCU ou un décodage de ligne incorrect. L'inversion UART globale est en
revanche défavorisée par les erreurs de parité et les octets non valides.

## Boucle UART2 GPIO17 vers GPIO16 — 0.4.5

NanoBCU déconnecté des lignes UART et pont matériel GPIO17 TX vers GPIO16 RX.
Le test a forcé UART2 en polarité normale à 19200/8E1, effacé les compteurs,
suspendu l'automate NCN5130 puis envoyé une seule fois `01 03 55 AA`.

```
+19489 TX:01
+19490 TX:03
+19491 TX:55
+19491 TX:AA
+19500 RX:FF RX:C0 RX:40 RX:25 RX:F5
```

Résultat : 4 octets TX, 5 octets RX, 2 erreurs de parité, 0 erreur de trame,
0 débordement FIFO et 0 perte de journal. La boucle ne reproduit donc pas les
octets émis. Ce test ne met pas en cause le NCN5130, absent des lignes ; il
oriente le diagnostic vers le chemin local GPIO/UART, le pont ou une charge
électrique encore présente sur GPIO16/17. Aucune nouvelle sonde n'a été lancée
après le test : l'état final affiché est `Sondes suspendues`.

## Boucles UART2 isolées et configuration effective — 0.4.6

Le test 0.4.5 n'a pas été reproduit après isolation complète de chaque format,
fermeture/réouverture d'UART2 et délai de stabilisation de 5 ms après
`HardwareSerial.begin()`. Un seul objet `HardwareSerial(2)` accède au
périphérique ; la pile KNX n'est toujours pas démarrée.

| Réglage relu | Essai 8N1 | Essai 8E1 |
|---|---:|---:|
| Débit | 19200 | 19200 |
| Données | 8 bits | 8 bits |
| Parité | aucune | paire |
| Arrêt | 1 bit | 1 bit |
| Inversion RX/TX | 0 / 0 | 0 / 0 |
| Flux matériel/logiciel | 0 / 0 | 0 / 0 |
| RS485 / boucle RS485 / half-duplex | 0 / 0 / 0 | 0 / 0 / 0 |
| RX pour `01 03 55 AA` | `01 03 55 AA` | `01 03 55 AA` |
| Erreurs parité/trame/débordement | 0 / 0 / 0 | 0 / 0 / 0 |

La boucle physique GPIO17 vers GPIO16 et UART2 fonctionnent donc correctement
dans les deux formats. L'échec 0.4.5 est compatible avec un artefact de son
protocole logiciel (réouverture suivie d'émissions unitaires immédiates) et ne
démontre pas une défaillance matérielle. UART2 a été restauré en 19200/8E1 normal après les essais,
mais l'automate NCN5130 reste explicitement suspendu tant que le pont est posé.
Le test GPIO lent n'a pas été ajouté, car il n'apporterait pas d'information
supplémentaire après ces deux boucles exactes.

## Diagnostic NCN5130 après reconnexion — 0.4.7

Après retrait du pont GPIO17 vers GPIO16 et reconnexion du NanoBCU, une nouvelle
campagne a commencé par l'arrêt de l'automate, l'effacement des compteurs, la
fermeture/réouverture d'UART2 en 19200/8E1 normal et une stabilisation de 5 ms.
La capture complète est :

```
+15412 TX:01  +15415 RX:FE
+18412 TX:01  +18415 RX:FE
+21412 TX:01  +21415 RX:FE
+24412 TX:01  +24415 RX:FE
+27412 TX:01  +27415 RX:FE
+30412 TX:01  +30415 RX:FE
```

Bilan : 6 TX, 6 RX, latence constante de 3 ms, 0 erreur de parité, 0 erreur de
trame, 0 débordement FIFO et 0 perte de journal. Aucun `U_Reset.ind` valide
(`03`) n'a été reçu. `FE` reste une donnée brute non reconnue. En conséquence,
le firmware n'a envoyé ni `U_State.req` ni `U_Busmon.req`, et aucune réception
TP n'a été engagée. Le problème précédent n'est pas considéré comme résolu.
L'écoute KNXnet/IP est restée active et `ROUTING_ARMED=0`.

## Balayage borné des formats NCN5130 — 0.4.8

Le balayage conserve GPIO16/17 et la polarité normale. Chaque format commence
par une fermeture/réouverture propre d'UART2, 10 ms de stabilisation, capture
des octets déjà présents, puis au maximum trois `U_Reset.req=01`.

| Format | Avant émission | Reset 1 | Reset 2 | Reset 3 | Erreurs P/F/O | Résultat |
|---|---|---|---|---|---|---|
| 19200/8E1 | aucun | `FE` | `FE` | `FE` | 0/0/0 | aucun `03` |
| 38400/8E1 | `F8` | `03` | `03` | `03` | 0/0/0 | valide et reproductible |
| 19200/8N1 | non testé | — | — | — | — | arrêt anticipé demandé |
| 38400/8N1 | non testé | — | — | — | — | arrêt anticipé demandé |

À 38400/8E1, après les trois réponses `03`, l'unique `U_State.req=02` a reçu
`07`, réponse reconnue par le masque d'état prévu. L'octet préalable `F8` a été
conservé comme observation brute et n'a joué aucun rôle dans la validation.
Le périphérique est resté configuré en 38400/8E1 à la fin du balayage, avec les
sondes suspendues. Aucun `U_Busmon.req` n'a été envoyé, aucune trame TP n'a été
mise en attente et aucun routage n'a été activé. L'écoute KNXnet/IP est restée
active et `ROUTING_ARMED=0`.

## Bus monitor TP et comparaison KNX/IP — 0.5.0/0.5.1

Le réglage permanent est désormais 38400/8E1, polarité normale, RX GPIO16 et
TX GPIO17. Au redémarrage : `TX:01 RX:03`, `TX:02 RX:07`, puis `TX:05` active
le bus monitor passif. Aucune erreur UART n'a été relevée.

Après actionnement d'un interrupteur, huit télégrammes TP ont été reçus sans
perte. Le NCN5130 ajoute `CC` après chaque trame TP ; cet octet d'encapsulation
est exclu du contrôle checksum et du décodage. Les huit checksums TP sont
valides. Exemples observés :

| Source | Destination | Service | APDU TP | Correspondance Siemens |
|---|---|---|---|---|
| `1.1.11` | `2/0/10` | GroupValueWrite | `00 80` | mêmes champs/APDU, IP +86 ms |
| `1.1.219` | `2/2/12` | GroupValueWrite | `00 80 00` | mêmes champs/APDU, IP +35 ms |
| `1.1.11` | `2/0/10` | GroupValueWrite | `00 81` | mêmes champs/APDU, IP +28 ms |

Le compteur de routage vaut 6 dans le télégramme TP et 5 dans le cEMI relayé,
ce qui est cohérent avec le franchissement du routeur Siemens. Les différences
d'encapsulation sont ignorées lors de la comparaison : TP contient son checksum
et le terminateur NCN5130 `CC`, tandis que KNX/IP contient l'en-tête cEMI
`29 00` et les champs de contrôle cEMI. La version 0.5.1 limite la corrélation
à 500 ms pour éviter de rapprocher à tort des commandes répétées identiques.

Certaines trames TP n'ont pas de correspondant IP proche ; cela peut refléter
le filtrage ou le comportement de répétition du Siemens et ne déclenche aucune
réémission du prototype. `ROUTING_ARMED=0`, tunnels arrêtés et aucune émission
TP↔IP sont maintenus.

| Étape | État | Preuve / résultat |
|---|---|---|
| USB / port série | Réussi | COM3, WCH CH9102, `VID:PID 1A86:55D4`, pilote `oem4.inf` |
| Puce / flash | Réussi | ESP32-D0WD-V3 rev. 3.1, 240 MHz, flash 4 Mio |
| Sauvegarde initiale | Réussi | image 4 Mio, SHA-256 `5274C13C496F0FC7A2E037276C009B5F400348DAA9DD16F94EDA95E62200CCF5` |
| Compilation finale | Réussie | PlatformIO `espressif32@6.12.0`, RAM 55232 octets (16,9 %), flash 995477 octets (75,9 %) |
| Flash final | Réussi | COM3, écriture et vérification par esptool |
| Démarrage / Wi-Fi | Validé | SSID configuré, IP `192.0.2.156`, RSSI observé -82 dBm après redémarrage |
| Pages ESP_BASE | Validées | `/`, `/wifi`, `/logs`, `/ota`, `/system`, `/api/status` en HTTP 200 |
| Pages KNX | Validées | `/knx` et `/knx-config` complètes et adaptatives, HTTP 200 |
| Enregistrement | Validé | `POST /knx-config-save` HTTP 200 ; valeurs relues après redémarrage |
| Validation serveur | Validée | `16.0.1` rejetée HTTP 400 ; route d'écriture en GET rejetée HTTP 404 |
| Diagnostic Web | Validé sans NanoBCU | lancement HTTP 202, expiration bornée, état « NanoBCU non détecté » |
| Verrou routage | Validé | `ROUTING_ARMED=0`, `static_assert`, aucun `knx.start()`/`knx.loop()`, routage et tunnels affichés inactifs |
| Dialogue NCN5130 | Non testé | NanoBCU volontairement non raccordé ; absence de réponse normale |
| Réception TP | Non validée | nécessite le raccordement décrit dans le README |
| Routage / tunnels ETS6 | Non validés | volontairement impossibles dans cette version |

## Persistance vérifiée

Les valeurs testées (`224.0.23.12`, port `3671`, délai `16000 ms`, sonde `3000 ms`, adresse physique vide) ont été enregistrées, l'ESP32 redémarré via COM3, puis le formulaire les a restituées. ESP_BASE a retrouvé le Wi-Fi et désactivé son AP de secours.

## Diagnostic attendu sans NanoBCU

Au démarrage ou après `POST /knx-diagnostic`, le firmware sonde le NCN5130 pendant le délai configuré sans bloquer la boucle. À l'expiration, il journalise une seule fois l'absence et cesse les émissions UART. Ce résultat n'est pas un défaut tant que le NanoBCU n'est pas raccordé.

Le prochain essai est limité au dialogue local NCN5130 puis à la réception TP passive. Le Siemens N146/02 peut rester actif. Aucun essai effectué sans NanoBCU ne justifie de remplacer la pile KNX.

## Migration des partitions et OTA 0.3.1

- table migrée par USB vers deux slots de 1 792 Kio, SPIFFS 384 Kio et coredump 64 Kio ;
- image complète, NVS, `otadata` et ancien SPIFFS sauvegardés avant migration ;
- NVS restauré, puis Wi-Fi reprovisionné par la commande série ESP_BASE sans exposer le secret ;
- paramètres KNX (`224.0.23.12`, `3671`, `16000`, `3000`) conservés ;
- Web OTA ESP_BASE testé de 0.3.0 vers 0.3.1 : HTTP 200, redémarrage, Wi-Fi connecté et pages Web complètes ;
- lecture USB du slot `app1` identique au binaire 0.3.1, SHA-256 `DA3BF6C79ADE56CA44D9CA0951E98F80D749956B79556DD31B61BC18716C67D3` ;
- `ROUTING_ARMED=0`, routage et tunnels toujours inactifs.

La reconnexion immédiatement consécutive à l'OTA a été validée (`CONNECTED_STA1`, IP `192.0.2.156`). Après les redémarrages USB supplémentaires utilisés pour relire le slot, l'association au point d'accès a ensuite expiré avec les statuts Wi-Fi 4 puis 6 malgré des identifiants présents. L'état final de banc est l'AP de secours `espbase-example-setup` sur `192.168.4.1`. Cela ne remet pas en cause l'écriture OTA vérifiée, mais la qualité radio ou l'accessibilité de `example-wifi` doit être confirmée à l'emplacement définitif.

## Diagnostic Wi-Fi 0.3.2

L'application journalise désormais les événements natifs ESP32, motifs 802.11, BSSID, canal, délais DHCP et RSSI. ESP_BASE retente nativement `example-wifi` toutes les 60 secondes après un essai de 15 secondes, tout en maintenant l'AP de secours.

Trois cycles de redémarrage ont produit des résultats intermittents : `AUTH_EXPIRE` (2), `TIMEOUT` (39), `4WAY_HANDSHAKE_TIMEOUT` (15), associations sans DHCP, et connexions complètes. Deux BSSID ont été observés : `02:00:00:00:00:01` canal 4 et `02:00:00:00:00:01` canal 1. Une reprise réussie sur le premier a obtenu DHCP en 4,405 s à −89 dBm ; une autre en 6,418 s à −81 dBm. Le même BSSID a pu échouer puis réussir, donc aucun n'est épinglé.

Après reprise, `/api/status`, `/`, `/knx`, `/knx-config` et `/ota` ont répondu en HTTP 200 avec des documents complets, parfois après répétition d'une requête. L'état final du banc est de nouveau l'AP de secours car le dernier cycle est resté sur le BSSID canal 1 sans DHCP. Voir [WIFI_DIAGNOSTIC.md](WIFI_DIAGNOSTIC.md).

## Stabilité mémoire 0.2.1

Après stabilisation Wi-Fi, 40 consultations de pages et trois diagnostics NCN5130 complets sans module, le heap libre s'est stabilisé à `223408` octets et le plus grand bloc à `110580` octets. Le minimum historique natif a atteint `183980` octets pendant les réponses Web, sans baisse du niveau stable. Aucun déclin durable n'a été observé. Le détail et les réserves proposées figurent dans [RESOURCE_AUDIT.md](RESOURCE_AUDIT.md).

## Écoute KNXnet/IP passive 0.4.0

L'OTA 0.3.3 vers 0.4.0 a réussi. Le Wi-Fi est revenu sur `example-wifi`, IP
`192.0.2.156`, RSSI -74 dBm. Les pages statut, KNX et OTA ont répondu et les
paramètres NVS (`224.0.23.12:3671`, 16 000/3 000 ms, adresse physique vide) ont
été conservés. L'inscription multicast a reçu quatre datagrammes, tous ignorés
car différents de `ROUTING_INDICATION`, sans erreur de format. Aucune adresse
KNX ne peut donc encore être confirmée.

Le heap s'est stabilisé autour de 223 kio. Après plusieurs consultations, le
ping répondait encore sans perte mais avec 295 à 1 571 ms de latence, tandis
que HTTP expirait. Les commandes pause/reprise/effacement restent à confirmer
en situation radio stable ; aucun redémarrage n'a été démontré. L'audit source
confirme `ROUTING_ARMED=0`, l'absence de démarrage de la pile et de tout envoi
UDP applicatif. Seuls les rapports IGMP d'adhésion multicast sont possibles.

L'essai réel a reçu six `ROUTING_INDICATION` valides depuis
`192.0.2.60:3671` : `15.15.22` vers le groupe `2/0/0` et `1.1.211` vers
`2/1/0`, services `GroupValueWrite`, compteur de routage 5, cEMI de 11 octets
finissant par `00 80` ou `00 81`. Aucun DPT n'a été supposé. Après l'OTA finale,
pause, reprise et effacement du journal ont répondu correctement. Deux services
`0x0201` ont été ignorés comme prévu, sans erreur de décodage.

## Premier essai NanoBCU raccordé — 0.4.1

Le diagnostic 0.4.0 a envoyé cinq `U_Reset.req` sans reconnaître de réponse.
La version 0.4.1 a ajouté des journaux UART et TP circulaires, sans démarrer la
pile KNX. Après OTA, six essais ont donné exactement la séquence suivante :

```
TX:01 RX:FE  TX:01 RX:FE  TX:01 RX:FE
TX:01 RX:FE  TX:01 RX:FE  TX:01 RX:FE
```

Chaque octet RX arrive environ 2 ms après le TX. Compteurs : 6 octets TX,
6 octets RX, 0 `U_Reset.ind`, 0 `U_State.ind`, aucune perte de journal et aucune
trame TP. `FE` est le complément bit à bit de `01` et n'est pas une réponse de
reset valide (`03` attendu). Le bus monitor n'a donc volontairement pas été
activé. Ce résultat impose de vérifier le sens RX/TX, une éventuelle inversion
du signal et le GND commun avant de modifier le protocole.

L'écoute KNXnet/IP est restée active. Aucun routage, tunnel, envoi TP ou rejeu
n'a été activé.

Après confirmation physique du câblage, la version 0.4.2 a permis un essai
temporaire avec inversion matérielle de l'UART ESP32. Il n'a produit aucun
`U_Reset.ind` : réponses brutes `00 07 00`, puis `47 00` à chaque sonde. La
polarité normale a été immédiatement rétablie et confirmée sur `/knx`. Une
inversion globale UART est donc exclue. L'essai reste disponible mais non
persistant ; tout redémarrage revient également en polarité normale.

## Préparation IP vers TP bornée 0.6.0 — 21 octobre 2026

- compilation PlatformIO réussie : RAM statique 64 584 octets sur 327 680,
  flash 1 031 821 octets sur un slot de 1 835 008 octets ;
- test indépendant `tools/test_ip_to_tp_stage1.py` réussi : source conservée,
  compteur 6 vers 5, contrôle TP `BC`, FCS `03`, `U_L_DataEnd=48` ;
- OTA réussie, version Web `0.6.0`, retour sur `example-wifi` à
  `192.0.2.156`, pages `/knx`, `/knx-config` et `/ota` HTTP 200 ;
- paramètres multicast conservés et adresse physique `1.1.253` enregistrée
  explicitement en NVS ;
- dialogue NCN5130 après redémarrage : `TX 01`, `RX 03`, `TX 02`, `RX 07`,
  `TX 05`, sans erreur UART ; Busmon passif restauré ;
- mode applicatif IP vers TP `PASSIF`, confirmation Siemens `Non`, file vide ;
- tentative d'activation sans confirmation refusée HTTP 423 ; aucune émission TP ;
- après plusieurs consultations Web : heap libre observé 208 968 à 212 800
  octets ; minimum natif 198 420 octets durant la première série et 211 824
  octets juste après le redémarrage correctif. Aucune baisse durable établie ;
- aucun `ROUTING_INDICATION` valide observé pendant cette vérification passive.
  L'essai réel reste donc à effectuer après déconnexion Ethernet du Siemens.

### Validation unicast et capture multicast

Après déconnexion Ethernet confirmée du N146, un unique GroupValueWrite OFF
unicast, source `15.15.254`, a été routé vers `2/0/0`. Réception IP, conversion
hop 6 vers 5, TP `BC FF FE 10 00 D1 00 80 03`, écho complet et confirmation
NCN5130 `8B` ont été observés. L'utilisateur a confirmé l'extinction de la
lampe. Retour Busmon passif effectué avant reconnexion du N146 ; aucun ON.

En passif, TShark a ensuite capturé sur `Wi-Fi 3` le même datagramme multicast
du PC, avec interface source `192.0.2.123`, TTL 1, destination
`224.0.23.12:3671` et charge exacte. L'ESP32 l'a reçu et décodé ; aucune mise en
file ni émission TP supplémentaire. Le fichier de preuve local est
`knx_multicast_wifi_capture.pcapng`.

## Rafales multicast passives 0.6.1 — 21 octobre 2026

Six series `KXDG` de 20 datagrammes ont ete emises a 100, 10 et 2 ms, sans
puis avec consultation simultanee de `/knx`. La capture PC contient 120/120
paquets ; l'ESP32 en a recu respectivement 6, 5, 5, 6, 5 et 2. Les pages Web
synchrones suspendent la desserte UDP pendant 6,28 a 6,72 secondes, mais des
pertes importantes existent aussi sans Web. Resultats, sequences absentes,
heap et analyse : [MULTICAST_BURST_TEST.md](MULTICAST_BURST_TEST.md).

## Tache UDP dediee 0.7.0 — 21 octobre 2026

La reception multicast est desormais assuree par une tache FreeRTOS qui est
seule proprietaire du socket et alimente une file de 32 evenements. Pendant
les six rafales, le socket et le consommateur ont conserve des bitmaps
identiques et la file n'a jamais ete pleine, y compris pendant des pages Web
de 6,9 secondes. Les pertes restantes precedent donc la file applicative.

Le chronometrage attribue l'essentiel du blocage aux appels synchrones
`sendContent()` du corps de `/knx`. Un essai TP concomitant a aussi montre la
concatenation de telegrammes en blocs de 30 et 51 octets : le pilote UART ne
deborde pas, mais la delimitation applicative est perdue tant que sa lecture
reste dans la boucle Web. Voir [FREERTOS_UDP_RX.md](FREERTOS_UDP_RX.md).

Une capture passive de 20 secondes après reconnexion du N146 a reçu un
`SEARCH_RESPONSE` `0x0202` depuis `192.0.2.60:3671`, MAC
`02:00:00:00:00:01`, vers le PC. Aucune nouvelle `ROUTING_INDICATION` n'est
apparue pendant cette fenêtre sans événement TP. Cette observation confirme la
présence Ethernet du N146, mais ne remplace pas un essai de routage déclenché.

### Capture simultanée TP / N146 / ESP32

Trois télégrammes rapprochés ont été reçus par le NanoBCU et exportés par le
N146. La capture `n146_tp_ip_simultaneous.pcapng` montre une concordance exacte
des sources, destinations et APDU ; le compteur passe de 6 sur TP à 5 dans les
trois cEMI du N146. Pendant la même fenêtre, le compteur ESP32 est resté à 22
télégrammes valides et aucune des trois indications n'est apparue dans son
journal multicast. Le mode applicatif est resté passif, file vide, sans nouvelle
émission TP.

### Réinscription IGMP et tenue

L'arrêt/recréation du socket a émis un Leave IGMP `0x17`, puis deux Membership
Reports `0x16` pour `224.0.23.12`. Le compteur d'inscriptions est passé de 1 à
2 sans redémarrage ni erreur. Après cette opération, l'ESP32 a reçu 4 des 8
indications N146 capturées pendant une première action KNX. Environ huit minutes
plus tard et sans nouvelle adhésion, il en a reçu 2 sur 6. La réception tient
donc dans le temps, mais les rafales restent partiellement perdues. Le prototype
est resté passif, file vide, sans émission TP ni tunnel.
# 2026-10-22 - moteur bidirectionnel passif 0.10.0

- `tools/test_bidirectional_router.py` : conversions indépendantes dans les deux
  sens, sources et APDU conservés, compteurs décrémentés, FCS, compteur nul,
  file bornée, expiration, échos à consommation unique et arbitre UART ;
- tests historiques IP→TP, tunnel ETS, envoi NCN5130 et parseur TP : OK ;
- compilation PlatformIO : RAM statique 66 456 / 327 680 octets, firmware
  1 054 521 / 1 835 008 octets ;
- `ROUTING_ARMED=0`, directions persistantes désactivées par défaut, tunnels
  désactivés au démarrage : aucune validation réelle de routage effectuée ;
- ESP_BASE 2.4.1 inchangé.
- OTA 0.10.0 validée : retour Wi-Fi et pages Web, paramètres version 1 migrés,
  Busmon passif, deux sens désactivés, tunnel arrêté, file TP vide.

# 2026-10-22 - préparation Node-RED unicast 0.10.1

- export KNX Ultimate original sauvegardé dans
  `nodered/knx_config_original.json` ; adresse cliente `15.15.22` préservée ;
- profil distinct limité à un tunnel, sans connexion de gestion concurrente ;
- activation soumise à la confirmation de déconnexion Ethernet du N146 ;
- démarrage et état préparé strictement passifs : `ROUTING_ARMED=0`, tunnel
  arrêté, NCN5130 Busmon ;
- `tools/test_node_red_tunnel_profile.py`, tests du routeur bidirectionnel et
  tests tunnel historiques : OK ;
- compilation PlatformIO : RAM statique 66 464 / 327 680 octets, firmware
  1 055 289 / 1 835 008 octets ;
- OTA 0.10.1 validée : retour sur `example-wifi`, `192.0.2.156`, RSSI -41 dBm,
  pages `/api/status` et `/knx` disponibles, Busmon passif, tunnel arrêté,
  profil ETS par défaut et `ROUTING_ARMED=0` ;
- préparation achevée avant l'essai réel documenté ci-dessous.

## Validation Node-RED 3.3.9

- instance `192.0.2.200:1880`, tunnel UDP connecté depuis le port 58744,
  canal 1 et adresse tunnel `15.15.22` annoncée dans la CRD ;
- 4 requêtes, 4 émissions TP confirmées, 0 échec, 14 indications remontées,
  12 ACK et aucune perte UDP TX ;
- l'utilisateur confirme l'effet physique des commandes lampe ON/OFF ; cet
  essai réel a dépassé le scénario borné à un unique OFF ;
- aucune erreur UART ; heap libre 164 488 octets, marges Web/UDP/NCN5130
  1 868/2 784/4 376 octets ;
- journal UART partiel (785 entrées écrasées) : compteurs fiables, chronologie
  par paquet et recherche exhaustive de doublons non démontrées ;
- routage multicast resté désactivé et `ROUTING_ARMED=0`.

## Découverte et reprise OTA 0.10.2

- référence pré-OTA : 180 échantillons sur 1 790 s, aucune perte de session ni
  erreur HTTP/UART/UDP ; détails dans `NODERED_TEST.md` ;
- SEARCH unicast corrigé et validé : réponse 76 octets, endpoint
  `192.0.2.156:3671`, IA `1.1.253`, familles Core/DM/Tunnelling ;
- OTA réussie, Wi-Fi et pages Web revenus ;
- profil Node-RED non persistant : serveur passif après boot ; tentative client
  automatique observée et refusée `0x27` ;
- après réactivation manuelle, reconnexion automatique Node-RED sur canal 1 en
  `15.15.22`, sans requête ni rejeu applicatif au CONNECT ;
- routage multicast resté désactivé, ESP_BASE inchangé.

## Coexistence ETS6 / Node-RED et flux tunnel sortant

- Node-RED maintenu sur canal 1 pendant une lecture ETS6 de `1.1.7` ;
- ETS sur le second tunnel `1.1.252` : 50/50 émissions TP confirmées, aucune
  confirmation négative ou absente ; session tunnel et gestion libérées ;
- aucune saturation NCN5130, aucune erreur UART, marges de pile préservées ;
- anomalie établie : le serveur envoyait plusieurs indications simultanées et
  comparait les ACK uniquement au dernier numéro émis (35 faux `ackErr` ETS) ;
- correction `0.10.3-dev` compilée, non déployée : file TX bornée par session,
  stop-and-wait, deux répétitions maximum, timeout et compteurs séparés ;
- `tools/test_tunnel_tx_flow.py`, tests découverte et routeur : OK ;
- RAM 68 656 / 327 680 octets, flash 1 058 813 / 1 835 008 octets.
