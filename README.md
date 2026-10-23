# ESP32-KNX-Router

Référence de développement 0.14.0 d'une interface KNX TP ↔ KNXnet/IP pour
**ESP32 Wemos D1 mini** et **NanoBCU v1.1.1 à NCN5130**.

> Ce prototype n'est ni un routeur final, ni un produit certifié KNX. Le
> démarrage reste passif : l'activation du routage doit être explicite depuis
> le Web et n'est possible que dans une compilation où `ROUTING_ARMED=1`.

## État fonctionnel

- NCN5130 validé sur UART2 : RX ESP32 GPIO16, TX ESP32 GPIO17,
  **38400 bauds, 8E1, polarité normale** ;
- réception TP passive, émission TP et confirmations NCN5130 validées ;
- tunneling unicast validé avec ETS6 pour lecture et programmation ;
- intégration Node-RED validée avec profil tunnel persistant ;
- cinq emplacements tunnel configurables, plus une connexion Device Management
  séparée ; la concurrence réelle de cinq clients échangeant simultanément
  n'est pas encore validée ;
- politiques Web séparées IP→TP et TP→IP, avec groupe, individuel et broadcast ;
- filtre commun aux deux sens : bitmap complet de 65 536 adresses de groupe,
  soit 8 192 octets ; édition Web par adresses/plages et import/export KXRF1 ;
- décisions de filtrage validées hors ligne et matériellement dans les deux sens ;
- moteur bidirectionnel, files bornées, expirations, confirmations, arbitrage
  tunnel/routage et protections anti-réinjection implémentés ;
- validation complète du routage multicast en conditions réelles encore à faire ;
- pertes multicast Wi-Fi connues ; futur portage Ethernet
  **Olimex ESP32-POE-ISO-16MB** préparé conceptuellement mais non validé sur matériel.

Les preuves détaillées propres à l'installation, captures réseau, journaux et
sauvegardes flash/NVS ne sont pas publiés.

## Dépendances et licence

- ESP32 Arduino via PlatformIO `espressif32@6.12.0` ;
- [thelsing/knx](https://github.com/thelsing/knx), commit
  `980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd` ;
- [ESP_BASE](https://github.com/pdeprost-dot/ESP_BASE) **2.4.1**, commit
  `f4d8a4790b29aa93bb87af09ac57d9b76c000d7c` ;
- PubSubClient `2.8`.

Les versions sont épinglées dans [platformio.ini](platformio.ini). La dépendance
thelsing/knx est sous GPL v3 ; ce dépôt est donc sous GPL-3.0-only. ESP_BASE et
PubSubClient sont sous licence MIT. Voir
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Câblage Wemos

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

## Compilation et tests

```powershell
git clone https://github.com/EXEMPLE/ESP32-KNX-Router.git
cd ESP32-KNX-Router
pio run
```

Tests hors ligne principaux :

```powershell
Get-ChildItem tools/test_*.py | ForEach-Object { python $_.FullName }
```

Le partitionnement [partitions_ota_1792.csv](partitions_ota_1792.csv) fournit
deux emplacements OTA de 1 835 008 octets, avec NVS, métadonnées OTA, SPIFFS et
coredump. Pour la référence publique 0.14.0, `firmware.bin` mesure
**1 097 168 octets**, soit une marge réelle de **737 840 octets** par
emplacement OTA.

### Premier flash USB

```powershell
pio run --target upload --upload-port COM3
pio device monitor --port COM3 --baud 115200
```

### Mise à jour OTA

Depuis un réseau local de confiance :

```powershell
curl.exe --fail-with-body --max-time 120 `
  -F "firmware=@.pio/build/wemos_d1_mini32/firmware.bin;type=application/octet-stream" `
  http://192.0.2.156/api/ota
```

`192.0.2.0/24` est un réseau réservé à la documentation.

## Mise en service Web

ESP_BASE configure et conserve le Wi-Fi. Le fichier
[include/secrets.h.example](include/secrets.h.example) ne contient que des
valeurs fictives ; `include/secrets.h` est ignoré et ne doit jamais être publié.

- `/knx` : état KNX, sessions, compteurs et journaux bornés ;
- `/knx-config` : adresse du routeur, cinq adresses tunnel, routage et filtres ;
- `/ota` : mise à jour ;
- `/logs` : journaux ESP_BASE.

Après remise à zéro, aucune adresse individuelle d'installation n'est fournie :
la page indique que la configuration est requise. Les cinq adresses tunnel
doivent être distinctes, libres, différentes de celle du routeur et réservées
dans ETS. Un emplacement sans adresse reste indisponible.

Le format texte KXRF1 accepte des adresses et plages de groupe. La requête
d'import est limitée à **12 288 octets** ; tout dépassement est rejeté
explicitement. La représentation persistante n'est pas une liste de 64 plages :
elle couvre réellement les 65 536 adresses au moyen d'un bitmap commun de
8 192 octets.

## ETS6 et Node-RED

ETS6 utilise KNXnet/IP Tunneling UDP sur le port configuré. La lecture
d'informations et un téléchargement de paramètres réversible ont été validés.
La connexion Device Management possède son propre canal et ne consomme pas un
des cinq emplacements tunnel.

Node-RED a été validé avec `node-red-contrib-knx-ultimate` en mode Tunnel UDP.
Le profil activé dans l'application est conservé en NVS et restauré au
redémarrage. Les adresses dépendent de l'installation et ne sont pas codées en
dur dans la configuration d'usine.

## Sécurité et limites

- ESP_BASE 2.4.1 n'apporte pas d'authentification Web ou OTA : utiliser un
  LAN/VLAN de confiance ;
- aucun HTTPS et aucun rollback OTA applicatif automatique ne sont garantis ;
- conserver un accès USB et une image connue ;
- le routage démarre toujours passif, même lorsque sa capacité est compilée ;
- éviter deux chemins IP/TP parallèles avant validation de la topologie et des
  protections anti-boucle ;
- le filtrage du routage est indépendant du tunneling ETS/Node-RED ;
- le portage Olimex, le transport Ethernet et cinq clients simultanément actifs
  restent à valider sur matériel.

## Licence

Copyright © 2026 Pierre de Prost.

GNU General Public License version 3 uniquement. Voir [LICENSE](LICENSE).
