# Prototype ESP32 KNX TP ↔ KNXnet/IP sur Wi-Fi

> Version 0.10.1 : moteur bidirectionnel TP↔IP consolidé mais verrouillé passif,
> deux tunnels ETS6 unicast (`1.1.254`, `1.1.252`) et une
> connexion de gestion distincte, désactivés par défaut. Procédure et limites :
> [ETS6.md](ETS6.md).

Un profil unicast distinct, borné à une session et à l'adresse cliente
`15.15.22`, prépare l'essai Node-RED KNX Ultimate sans modifier le verrou de
routage. Il reste désactivé au démarrage : [NODERED_TEST.md](NODERED_TEST.md).

Prototype prudent pour Wemos D1 mini ESP32 classique et NanoBCU v1.1.1 à transceiver **NCN5130**. Le firmware actuellement flashé est une version de diagnostic et de configuration : le routage est verrouillé à la compilation et la pile KNXnet/IP n'est pas démarrée.

La version 0.5.3 a introduit un essai TP manuel borné : source fixe `1.1.253`, destination fixe `2/0/0`, valeur ON/OFF explicite. Les résultats historiques sont détaillés dans [TP_TX_TEST.md](TP_TX_TEST.md). L'audit suivant a identifié deux erreurs de protocole dans cette première implémentation ; elle ne doit plus être utilisée telle quelle.

L'audit 0.5.4 corrige l'index `U_L_DataEnd`, retire `U_SetAddress` car il active aussi l'auto-ACK de groupe, décode explicitement `U_State.ind` et verrouille les émissions par `TP_TEST_ARMED=0`. Voir [AUDIT_NCN5130_SEND.md](AUDIT_NCN5130_SEND.md).

## État logiciel

- application `ESP32-KNX-WIFI-ROUTER` 0.9.5 ;
- ESP_BASE 2.4.1, dépôt local au commit `f4d8a4790b29aa93bb87af09ac57d9b76c000d7c` (tag `esp-base-2.4.1`) ;
- pile `thelsing/knx` épinglée au commit `980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd` ;
- `ROUTING_ARMED=0` vérifié par `static_assert` ;
- moteur TP↔IP, filtres persistants, files bornées et arbitre tunnel/routage
  décrits dans [ROUTER_ENGINE.md](ROUTER_ENGINE.md), tous inactifs au démarrage ;
- aucun appel à `knx.start()` ou `knx.loop()` : seule la réception multicast
  passive est active ; routage, tunnels et émissions restent inactifs.

ESP_BASE fournit Wi-Fi, AP de secours, pages système, logs, MQTT et OTA. L'application ajoute ses routes au serveur Web natif :

- `/knx` : état ESP32, écoute KNXnet/IP, journal borné, diagnostic NCN5130 et verrou ;
- `/knx-config` : configuration KNX et diagnostic ;
- `POST /knx-config-save` : validation puis sauvegarde explicite ;
- `POST /knx-diagnostic` : relance du diagnostic local ;
- pages ESP_BASE : `/`, `/wifi`, `/mqtt`, `/logs`, `/ota`, `/system` et `/api/status`.

ESP_BASE 2.4.1 n'offre pas d'authentification applicative. L'interface doit rester sur un LAN de confiance.

Le diagnostic 0.4.3 commence la capture UART avant l'initialisation d'ESP_BASE,
dispose d'un journal circulaire borné de 192 événements et permet d'effacer en
une opération les journaux et compteurs UART/TP avant une nouvelle campagne.
L'enchaînement reste strict : `U_State.req` puis `U_Busmon.req` ne sont émis
qu'après reconnaissance de la réponse `U_Reset.ind` attendue.
La version 0.4.4 ajoute les compteurs matériels d'erreurs UART de parité, de
trame et de débordement FIFO fournis par le pilote Arduino ESP32.
La version 0.4.5 ajoute un test de boucle UART ponctuel qui suspend l'automate
NCN5130, remet ses compteurs à zéro et n'envoie que `01 03 55 AA`. Les sondes
restent arrêtées après le test jusqu'à une action explicite ou un redémarrage.
La version 0.4.6 isole successivement les essais 19200/8N1 et 19200/8E1 avec
un seul propriétaire d'UART2. Elle relit dans le pilote et les registres le
débit, le format, les inversions, les contrôles de flux et le mode RS485.
La version 0.4.7 applique aussi cette séquence propre aux diagnostics NCN5130 :
arrêt de l'automate, remise à zéro, réouverture en 19200/8E1 normal, délai de
stabilisation de 5 ms, puis seulement lancement de `U_Reset.req`.
La version 0.4.8 ajoute un balayage borné des quatre formats NCN5130. Il s'arrête
sur trois `U_Reset.ind=03` consécutifs, sonde uniquement `U_State`, puis laisse
Busmon, le routage et les tunnels arrêtés.

## Configuration persistante

La configuration applicative utilise son propre espace NVS `knxrouter`, version 1. Elle n'est écrite que lors d'un enregistrement explicite.

| Paramètre | Défaut | Validation |
|---|---:|---|
| Adresse physique prévue | non configurée | `0..15.0..15.0..255` |
| Multicast KNXnet/IP | `224.0.23.12` | IPv4 classe D |
| Port UDP | `3671` | `1..65535` |
| Délai diagnostic | `15000 ms` | `3000..60000 ms` |
| Intervalle sondes | `3000 ms` | `500..10000 ms`, inférieur au délai |

Les paramètres KNXnet/IP sont préparés pour une phase ultérieure et ne peuvent pas activer le routage. Le Wi-Fi est maintenant géré et persisté par ESP_BASE ; `include/secrets.h` n'est plus utilisé à l'exécution.

## Câblage du prochain essai

Couper l'USB avant le câblage, puis raccorder :

| NanoBCU v1.1.1 | ESP32 / bus |
|---|---|
| RX | GPIO17 (TX ESP32) |
| TX | GPIO16 (RX ESP32) |
| GND | GND ESP32 commun |
| KNX | rouge du bus KNX |
| GND bus | noir du bus KNX |
| SAV et sorties 3V3 | laisser libres |

Alimenter ensuite l'ESP32 par USB. UART2 fonctionne à **38400 bauds, 8E1,
polarité normale** et 3,3 V ; UART0 reste réservé au flash et aux logs USB.

Le Siemens N146/02 peut rester actif pendant ce diagnostic puisque le prototype ne route rien. Le firmware envoie uniquement `U_Reset.req`, `U_State.req` et `U_Busmon.req`, puis écoute en bus monitor passif. Il n'émet aucune commande applicative et ne répond pas aux télégrammes KNX.

## Construction et restauration

```text
pio run
pio run -t upload --upload-port COM3
pio device monitor -p COM3 -b 115200
```

La carte détectée est un ESP32-D0WD-V3 rev. 3.1 avec 4 Mio de flash, sur COM3 via WCH CH9102 (`VID:PID 1A86:55D4`). La sauvegarde antérieure au premier flash est `backup/original-esp32-2026-10-20-4MiB.bin` (ignorée par Git), SHA-256 `5274C13C496F0FC7A2E037276C009B5F400348DAA9DD16F94EDA95E62200CCF5`.

```text
python -m esptool --port COM3 write_flash 0x0 backup/original-esp32-2026-10-20-4MiB.bin
```

## Conditions avant tout routage

Ne pas armer le routage avant d'avoir confirmé avec l'utilisateur l'adresse physique, la topologie ETS et la présence du Siemens sur la même ligne. Deux chemins IP/TP parallèles peuvent produire des doublons ou des boucles. Le prototype n'est pas équivalent au Siemens N146/02 tant que TP, filtrage ETS, routage dans les deux sens et tunnels n'ont pas été validés sur l'installation réelle.

Voir [TESTS.md](TESTS.md) pour les validations factuelles, [RESOURCE_AUDIT.md](RESOURCE_AUDIT.md) pour le bilan des ressources, [OTA_AND_RECOVERY.md](OTA_AND_RECOVERY.md) pour les mises à jour, [WIFI_DIAGNOSTIC.md](WIFI_DIAGNOSTIC.md) pour la reprise réseau, [KNX_IP_LISTENER.md](KNX_IP_LISTENER.md) pour l'écoute passive et [IP_TO_TP_STAGE1.md](IP_TO_TP_STAGE1.md) pour le premier mode IP vers TP borné.
