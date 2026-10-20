# Prototype ESP32 KNX TP ↔ KNXnet/IP sur Wi-Fi

Prototype prudent pour Wemos D1 mini ESP32 classique et NanoBCU v1.1.1 à transceiver **NCN5130**. Le firmware actuellement flashé est une version de diagnostic et de configuration : le routage est verrouillé à la compilation et la pile KNXnet/IP n'est pas démarrée.

## État logiciel

- application `ESP32-KNX-WIFI-ROUTER` 0.2.1 ;
- ESP_BASE 2.4.1, dépôt local au commit `f4d8a4790b29aa93bb87af09ac57d9b76c000d7c` (tag `esp-base-2.4.1`) ;
- pile `thelsing/knx` épinglée au commit `980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd` ;
- `ROUTING_ARMED=0` vérifié par `static_assert` ;
- aucun appel à `knx.start()` ou `knx.loop()` : multicast, routage et tunnels sont inactifs.

ESP_BASE fournit Wi-Fi, AP de secours, pages système, logs, MQTT et OTA. L'application ajoute ses routes au serveur Web natif :

- `/knx` : état ESP32, réseau, diagnostic NCN5130, compteurs TP et verrou ;
- `/knx-config` : configuration KNX et diagnostic ;
- `POST /knx-config-save` : validation puis sauvegarde explicite ;
- `POST /knx-diagnostic` : relance du diagnostic local ;
- pages ESP_BASE : `/`, `/wifi`, `/mqtt`, `/logs`, `/ota`, `/system` et `/api/status`.

ESP_BASE 2.4.1 n'offre pas d'authentification applicative. L'interface doit rester sur un LAN de confiance.

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

Alimenter ensuite l'ESP32 par USB. UART2 fonctionne à 19200 bauds, 8E1 et 3,3 V ; UART0 reste réservé au flash et aux logs USB.

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

Voir [TESTS.md](TESTS.md) pour les validations factuelles et [RESOURCE_AUDIT.md](RESOURCE_AUDIT.md) pour le bilan flash, partitions, heap et piles.
