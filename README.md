# ESP32-KNX-Router

Prototype de passerelle KNX TP ↔ KNXnet/IP pour **ESP32 Wemos D1 mini** et
**NanoBCU v1.1.1 équipé d'un NCN5130**. Le projet privilégie les files bornées,
les propriétaires uniques des interfaces UDP/UART et un démarrage sûr.

> Référence de développement, pas un routeur KNX certifié. Le routage
> multicast reste verrouillé par défaut avec `ROUTING_ARMED=0`.

## État validé

- NanoBCU NCN5130 : UART2, RX ESP32 GPIO16, TX ESP32 GPIO17,
  **38400 bauds, 8E1, polarité normale** ;
- réception TP passive et dialogue local NCN5130 validés ;
- émission TP ciblée validée avec confirmations NCN5130 ;
- serveur KNXnet/IP Tunneling unicast : lecture et programmation ETS6 validées ;
- intégration Node-RED avec `node-red-contrib-knx-ultimate` validée ; profil
  tunnel persistant après redémarrage ;
- moteur bidirectionnel TP↔IP, filtrage, compteurs de routage, anti-échos,
  files et expirations implémentés et testés hors ligne ;
- chemin IP→TP validé en essai borné, mais le routage bidirectionnel réel
  complet n'est pas encore validé ;
- pertes multicast observées sur le transport Wi-Fi : cette limite reste à
  caractériser sur la future cible Ethernet ;
- portage **Olimex ESP32-POE-ISO-16MB** prévu, non validé faute de matériel.

Les résultats détaillés sont dans [TESTS.md](TESTS.md). Les captures réseau,
journaux d'installation et sauvegardes flash ne font pas partie du dépôt.

## Dépendances

- ESP32 Arduino via PlatformIO `espressif32@6.12.0` ;
- [thelsing/knx](https://github.com/thelsing/knx), commit
  `980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd` ;
- [ESP_BASE](https://github.com/pdeprost-dot/ESP_BASE) **2.4.1**, commit
  `f4d8a4790b29aa93bb87af09ac57d9b76c000d7c` ;
- PubSubClient `2.8`.

Les versions sont épinglées dans [platformio.ini](platformio.ini). La pile
thelsing/knx est sous GPL v3 ; ce dépôt est donc publié sous GPL-3.0-only.
ESP_BASE et PubSubClient sont sous licence MIT. Voir
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Matériel et câblage Wemos

Couper les alimentations avant câblage.

| NanoBCU | ESP32 / bus |
|---|---|
| TX | GPIO16 (RX ESP32) |
| RX | GPIO17 (TX ESP32) |
| GND | GND ESP32 commun |
| KNX | rouge du bus KNX |
| GND bus | noir du bus KNX |
| SAV et sorties 3V3 | non raccordés |

L'ESP32 est alimenté par USB. Ces GPIO sont propres à la cible Wemos et ne
doivent pas être repris sans vérification sur l'Olimex.

## Installation et compilation

Installer [PlatformIO](https://platformio.org/), puis :

```powershell
git clone https://github.com/EXEMPLE/ESP32-KNX-Router.git
cd ESP32-KNX-Router
pio run
```

Tests hors ligne principaux :

```powershell
python tools/test_ncn5130_rx_parser.py
python tools/test_ncn5130_send_sequence.py
python tools/test_knx_tunnel_protocol.py
python tools/test_bidirectional_router.py
python tools/test_tunnel_tx_flow.py
python tools/test_knx_ip_discovery.py
```

Le partitionnement [partitions_ota_1792.csv](partitions_ota_1792.csv) fournit
deux emplacements OTA de 1792 Kio, ainsi que NVS, otadata, SPIFFS et coredump.

### Premier flash USB

Adapter le port série :

```powershell
pio run --target upload --upload-port COM3
pio device monitor --port COM3 --baud 115200
```

### Mise à jour OTA

Depuis un réseau local de confiance, ouvrir `http://192.0.2.156/ota`, ou :

```powershell
curl.exe --fail-with-body --max-time 120 `
  -F "firmware=@.pio/build/wemos_d1_mini32/firmware.bin;type=application/octet-stream" `
  http://192.0.2.156/api/ota
```

`192.0.2.0/24` est ici un réseau d'exemple réservé à la documentation.

## Configuration

ESP_BASE configure et conserve le Wi-Fi depuis son interface Web. Le fichier
[include/secrets.h.example](include/secrets.h.example) illustre uniquement une
configuration locale éventuelle ; `include/secrets.h` est ignoré par Git et ne
doit jamais être publié.

Pages principales :

- `/` : état ESP_BASE ;
- `/wifi` : configuration Wi-Fi ;
- `/knx` : état KNX, journaux bornés et tunnels ;
- `/knx-config` : paramètres et filtres ;
- `/ota` : mise à jour ;
- `/logs` : journaux ESP_BASE.

Exemple de laboratoire : interface `192.0.2.156:3671`, adresse physique du
prototype `1.1.250`, client tunnel `15.15.20`. Vérifier dans ETS que toutes les
adresses sont libres avant usage. Ne jamais activer deux chemins IP/TP en
parallèle sur la même ligne sans stratégie anti-boucle validée.

## ETS6 et Node-RED

ETS6 se connecte manuellement en KNXnet/IP Tunneling UDP sur le port 3671. Une
session tunneling et une connexion de gestion distincte sont prises en charge,
avec séquences, ACK, délais et répétitions bornées. La lecture d'informations
et un téléchargement de paramètres réversible ont été validés.

Pour Node-RED, utiliser un profil **Tunnel UDP**, l'adresse IP de l'ESP32 et une
adresse individuelle libre. Le profil sélectionné dans l'application est
conservé en NVS et restauré après le diagnostic NCN5130 au redémarrage.

## Sécurité et limites

- ESP_BASE 2.4.1 ne fournit pas d'authentification Web ou OTA : déployer
  uniquement sur un LAN/VLAN de confiance ;
- aucun HTTPS n'est fourni par le firmware ;
- aucun rollback OTA applicatif automatique n'est garanti ; conserver un accès
  USB et un binaire connu ;
- le firmware n'est ni certifié KNX ni destiné à une installation de sécurité ;
- `ROUTING_ARMED=0` doit rester la valeur par défaut tant que la topologie, les
  filtres et la coexistence avec les autres interfaces ne sont pas validés.

## Licence

Copyright © 2026 Pierre de Prost.

Ce projet est distribué sous la GNU General Public License version 3
uniquement. Voir [LICENSE](LICENSE). Il est fourni sans garantie.
