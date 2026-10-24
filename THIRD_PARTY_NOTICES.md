# Composants tiers

Ce projet utilise les composants suivants sans en recopier les sources dans ce
dépôt :

| Composant | Version épinglée | Licence |
|---|---|---|
| [thelsing/knx](https://github.com/thelsing/knx) | commit `980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd` | GNU GPL v3 |
| [ESP_BASE](https://github.com/pdeprost-dot/ESP_BASE) | tag `esp-base-2.4.2` | MIT |
| [PubSubClient](https://github.com/knolleary/pubsubclient) | `2.8` | MIT |
| Arduino core for ESP32 | plateforme PlatformIO `espressif32@6.12.0` | licences du projet Espressif/Arduino |

La GPL v3 de thelsing/knx impose une licence compatible au programme combiné ;
ESP32-KNX-Router est donc publié sous GPL-3.0-only. Les avis de copyright et
licences des dépendances restent ceux de leurs auteurs. PlatformIO télécharge
les versions déclarées lors de la compilation.
