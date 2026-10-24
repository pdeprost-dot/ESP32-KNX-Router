# ESP32-KNX-Router

Firmware expérimental de passerelle KNX TP1 ↔ KNXnet/IP pour ESP32, avec
NanoBCU/NCN5130. La branche `feature/knx-intersite-l3` correspond au firmware
de développement **0.15.5**. Ce projet n'est ni un produit fini, ni un appareil
certifié KNX.

## État des fonctions

Validé sur matériel :

- NCN5130 en UART 38400 bauds, 8E1, polarité normale ;
- trames TP1 standard, routage KNXnet/IP et tunneling ETS6 ;
- cinq emplacements de tunnel configurables (la concurrence de cinq clients
  actifs simultanément reste à valider) ;
- intégration Node-RED par tunnel unicast ;
- Olimex ESP32-POE-ISO-16MB, Ethernet/PoE et OTA Ethernet ;
- filtres de routage Web sur bitmap commun de 8192 octets ;
- KXL3 entre deux ESP partageant le même segment TP1, en mode monitor-only,
  sans réinjection physique.

Validé hors ligne ou en simulation :

- codec TP1 standard et étendu jusqu'à 263 octets ;
- réinjection KXL3 → TP1 simulée et anti-boucle multisite ;
- simulateur TP1 pour développer KNXnet/IP sans NCN5130.

Reste à valider physiquement :

- KXL3 entre deux segments TP1 distincts et à travers un VPN L3 ;
- concurrence réelle de cinq clients tunneling ;
- télégrammes Siemens Synco/LTE réels ;
- comportement multicast Wi-Fi dans toutes les infrastructures.

Le démarrage reste passif. Les tunnels et les sens de routage ne deviennent
effectifs qu'après configuration et activation explicites. KXL3 est également
désactivé au démarrage.

## Matériel et cibles

| Environnement PlatformIO | Réseau | TP1 |
|---|---|---|
| `wemos_d1_mini32` | Wi-Fi | NCN5130, RX GPIO16 / TX GPIO17 |
| `olimex_poe_iso_16mb` | Ethernet LAN8720 | NCN5130, RX GPIO36 / TX GPIO4 |
| `olimex_poe_iso_16mb_wifi` | Wi-Fi de développement | NCN5130 |
| `olimex_poe_iso_16mb_wifi_simulated` | Wi-Fi de développement | simulé |

La cible Olimex emploie une table de partitions OTA pour flash 16 Mio. La cible
Wemos conserve ses deux emplacements OTA de 1792 Kio.

## Dépendances et compilation

- PlatformIO `espressif32@6.12.0` ;
- [ESP_BASE](https://github.com/pdeprost-dot/ESP_BASE) `esp-base-2.4.2` ;
- [thelsing/knx](https://github.com/thelsing/knx) au commit
  `980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd` ;
- PubSubClient 2.8.

```text
pio run -e wemos_d1_mini32
pio run -e olimex_poe_iso_16mb
pio run -e olimex_poe_iso_16mb_wifi_simulated
```

ESP_BASE mémorise la configuration Wi-Fi. Aucun secret n'est nécessaire dans
le dépôt. `include/secrets.h.example` ne contient que des valeurs fictives.

## Interfaces

Les pages principales sont `/knx`, `/knx-config`, `/knx-advanced`,
`/knx-maintenance`, `/knx-help` et `/knx-intersite`. ESP_BASE ajoute notamment
`/logs` et `/ota`.

La configuration Web/OTA ne dispose pas d'authentification applicative : elle
doit rester sur un LAN de confiance. KXL3 transporte des datagrammes UDP
unicast avec CRC32, identité de site, séquence, ACK et anti-doublon. Ces
mécanismes ne sont **pas** une authentification cryptographique ; utiliser KXL3
uniquement sur un réseau maîtrisé ou protégé par VPN.

## Documentation

- [Protocole KXL3](docs/KNX_INTERSITE_L3_PROTOCOL.md)
- [Validation KXL3 monitor-only sur un TP1 partagé](docs/VALIDATION_KXL3_TWO_ESP_SAME_TP1.md)
- [Validation des trames étendues](docs/VALIDATION_KNX_EXTENDED_FRAMES.md)
- [Simulateur TP1](docs/TP1_SIMULATOR.md)
- [Portage Olimex](OLIMEX_PORT.md)
- [Tests](TESTS.md)

Les adresses IP et identifiants de sites présentés dans la documentation
publique sont des exemples. Les configurations d'installation, captures réseau,
journaux, sauvegardes flash/NVS et secrets ne sont pas publiés.

## Licence

Le projet est distribué sous GPL-3.0-only, conformément à la dépendance
thelsing/knx. Voir [LICENSE](LICENSE) et
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
