# Cible Olimex ESP32-POE-ISO-16MB

## État de validation

Le 23 octobre 2026, la cible `olimex_poe_iso_16mb` a été compilée et
flashée par USB sur une carte détectée comme ESP32-D0WD-V3 révision 3.1 avec
16 Mo de flash. Le démarrage série est validé. L'initialisation du PHY est
acceptée, mais le lien, le DHCP, le Web et l'OTA Ethernet restent à valider
avec un câble réseau raccordé. Le NanoBCU n'était pas raccordé pendant cet
essai.

Le démarrage reste passif : le moteur de routage effectif est désactivé, le
profil Node-RED n'est pas restauré sur une NVS neuve et aucune commande KNX
applicative n'est émise.

## Brochage retenu

| Fonction | GPIO | Remarque |
|---|---:|---|
| NanoBCU TX vers ESP32 RX | 36 | entrée seule, broche RX UEXT |
| ESP32 TX vers NanoBCU RX | 4 | broche TX UEXT |
| Ethernet MDC | 23 | RMII Olimex |
| Ethernet MDIO | 18 | RMII Olimex |
| Alimentation PHY | 12 | commande d'alimentation Olimex |
| Horloge PHY | 17 | `ETH_CLOCK_GPIO17_OUT`, variante WROOM/N16 |

Ce réglage ne convient pas sans vérification à la variante WROVER de certaines
révisions, où Olimex documente une horloge Ethernet sur GPIO0. La cible présente
est la variante 16 Mo WROOM et la flash a été mesurée avant programmation.

Références matérielles officielles :

- exemple Olimex ESPHome `esp32-poe-iso.yaml` (PHY, horloge et UEXT) ;
- exemple Olimex ESP-IDF Ethernet (LAN8710A avec pilote LAN8720) ;
- journal officiel des révisions matérielles ESP32-POE-ISO.

## Compilation et flash initial

```powershell
pio run -e olimex_poe_iso_16mb
pio run -e olimex_poe_iso_16mb -t upload --upload-port COM5
```

### Mode de développement Wi-Fi

Le transport est sélectionné exclusivement à la compilation :

- `olimex_poe_iso_16mb` : Ethernet, mode produit ;
- `olimex_poe_iso_16mb_wifi` : Wi-Fi, mode de développement sans RJ45.

La seconde cible conserve le brochage UART et le partitionnement 16 Mo de
l'Olimex, mais n'initialise pas le PHY. Elle utilise directement la connexion
STA, le Web, l'OTA et le MQTT gérés par ESP_BASE. KNXnet/IP emploie la même
tâche UDP et la même implémentation protocolaire dans les deux modes ; seuls
l'état de liaison, l'adresse locale et la MAC proviennent du transport choisi.

```powershell
pio run -e olimex_poe_iso_16mb_wifi
pio run -e olimex_poe_iso_16mb_wifi -t upload --upload-port COM5
```

Une carte dont la NVS est neuve démarre sur le point d'accès de secours
ESP_BASE. Les identifiants STA doivent être saisis dans `/wifi` ou par la
commande USB `WIFI <ssid>|<mot-de-passe>` ; ils ne sont jamais intégrés au
firmware.

Le port doit être adapté à la machine. La carte testée expose un pont CH340,
VID `1A86`, PID `7523`.

## Partitionnement 16 Mo

La table `partitions_ota_16mb.csv` conserve NVS, métadonnées OTA et coredump.
Elle fournit deux emplacements OTA de 6 Mio et un SPIFFS de 3 968 Kio. Le
binaire mesuré lors du portage fait 1 140 640 octets, soit une marge de
5 150 816 octets dans chaque emplacement OTA.

## Intégration ESP_BASE 2.4.1

ESP_BASE reste inchangé. Sur cette cible, son initialisation est réutilisée
pour Web, OTA, MQTT, identité et journaux, puis la radio Wi-Fi est arrêtée. La
boucle applicative dessert explicitement Web, OTA et MQTT avec l'état du lien
Ethernet. Le socket KNXnet/IP reste possédé par l'unique tâche UDP existante et
utilise l'adresse Ethernet pour les réponses et les DIB de découverte.

Une NVS neuve affiche « configuration requise » pour KNX : aucune adresse
individuelle ou adresse de tunnel personnelle n'est compilée dans le firmware.

Sans NCN5130, le diagnostic finit explicitement en `TP1 NON CONNECTÉ`. Les
services IP et Web restent desservis. Un serveur de tunnel non prêt refuse le
CONNECT conformément au protocole ; il ne prétend jamais avoir transmis une
requête sur TP1.

### Validation Wi-Fi du 24 octobre 2026

La cible de développement a rejoint le réseau configuré, obtenu une adresse
DHCP et desservi les pages Web et l'OTA. SEARCH et DESCRIPTION KNXnet/IP
unicast ont répondu avec l'adresse locale correcte. Le CONNECT Tunneling a été
traité mais refusé avec le statut `0x27`, attendu en l'absence du NCN5130.

Le transport multicast Wi-Fi reste imparfait : les rafales numérotées ont
montré des pertes croissantes avec la cadence, sans saturation de la file UDP.
Cela ne concerne pas la cible Ethernet définitive, qui devra être validée avec
un câble RJ45. Aucun routage ou envoi TP n'a été activé pendant ces essais.
