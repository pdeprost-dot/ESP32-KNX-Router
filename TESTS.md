# Bilan des essais

Date : 2026-10-20 (Europe/Paris)

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
