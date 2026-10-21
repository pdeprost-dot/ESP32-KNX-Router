# Audit des ressources du firmware 0.2.1

Date : 2026-10-20. Cible réelle : ESP32-D0WD-V3 rev. 3.1, flash 4 Mio, sans PSRAM. ESP_BASE 2.4.1 n'a pas été modifié et `ROUTING_ARMED=0` est resté actif pendant toutes les mesures.

## Flash et RAM statique

| Ressource | Capacité | Utilisée | Restante | Utilisation |
|---|---:|---:|---:|---:|
| Emplacement application OTA | 1 835 008 o | 1 007 344 o, taille réelle de `firmware.bin` | 827 664 o | 54,90 % |
| Charge calculée par l'éditeur de liens | 1 835 008 o | 1 000 765 o | 834 243 o | 54,54 % |
| RAM statique annoncée par PlatformIO | 327 680 o | 55 280 o | 272 400 o | 16,87 % |

La taille du fichier binaire est la valeur prudente pour vérifier qu'une image tient dans un slot OTA. La mesure de l'éditeur de liens exclut certains en-têtes et alignements de l'image flash, d'où les 6 579 octets d'écart.

## Table de partitions effective

Table décodée directement depuis `.pio/build/wemos_d1_mini32/partitions.bin` :

| Partition | Type | Offset | Taille |
|---|---|---:|---:|
| `nvs` | données NVS | `0x009000` | 20 480 o (20 Kio) |
| `otadata` | métadonnées OTA | `0x00E000` | 8 192 o (8 Kio) |
| `app0` | application `ota_0` | `0x010000` | 1 835 008 o (1 792 Kio) |
| `app1` | application `ota_1` | `0x1D0000` | 1 835 008 o (1 792 Kio) |
| `spiffs` | système de fichiers | `0x390000` | 393 216 o (384 Kio) |
| `coredump` | diagnostic système | `0x3F0000` | 65 536 o (64 Kio) |

Les deux slots application ont la même capacité. La marge physique actuelle de 827 664 octets s'applique donc au slot actif comme à une mise à jour OTA. L'audit du code d'ESP_BASE 2.4.1 et de cette application ne trouve aucun montage ni accès SPIFFS/LittleFS ; ESP_BASE stocke sa configuration dans NVS. Les références LittleFS du dépôt ESP_BASE appartiennent à un exemple ESP8266 indépendant. Une partition SPIFFS de 384 Kio est néanmoins conservée pour un besoin applicatif futur. L'ancien espace SPIFFS a été sauvegardé avant migration.

## Mémoire dynamique et piles

| Mesure runtime | Après Wi-Fi stabilisé | Après 40 pages | Après diagnostics 1 / 2 / 3 |
|---|---:|---:|---:|
| Heap libre instantané | 226 712 o | 223 444 o | 223 408 / 223 408 / 223 408 o |
| Minimum natif depuis démarrage | 220 396 o | 183 980 o | 183 980 o |
| Plus grand bloc libre | 110 580 o | 110 580 o | 110 580 o |
| Mémoire interne libre finale | — | — | 223 408 o |
| Plus grand bloc interne final | — | — | 110 580 o |
| Marge pile `loopTask`/Web | 4 956 o | 3 884 o | 3 884 o |
| Marges piles idle finales | — | — | CPU0 436 o / CPU1 552 o |
| PSRAM | absente | absente | absente |

Les valeurs de pile sont les minima historiques FreeRTOS. Le serveur Web s'exécute dans `loopTask`, donc sa marge inclut les traitements applicatifs et Web. Les tâches internes Wi-Fi ne sont pas exposées individuellement par cette page. Les petites piles idle sont normales pour des tâches minimales mais devront rester surveillées après tout changement de framework.

Le niveau stable ne diminue pas au fil des diagnostics. La baisse du minimum historique correspond à un pic transitoire pendant les réponses Web ; ce compteur est monotone et ne remonte pas. Aucun signe de fuite durable n'a été observé sur cette campagne limitée.

## Incohérence de l'ancien libellé

La page ESP_BASE pouvait afficher un heap instantané inférieur à son « minimum » applicatif. ESP_BASE initialise et actualise son propre minimum dans sa boucle Web ; lors de la génération d'une réponse, le heap instantané pouvait déjà refléter des allocations que ce suivi applicatif n'avait pas encore échantillonnées. Ce n'était donc pas le minimum natif de l'allocateur.

Sans modifier ESP_BASE, `/knx` affiche maintenant :

- `ESP.getFreeHeap()` comme valeur instantanée ;
- `ESP.getMinFreeHeap()` comme minimum natif réel depuis le démarrage ;
- `ESP.getMaxAllocHeap()` et les mesures `MALLOC_CAP_INTERNAL` pour la fragmentation et la mémoire interne.

Le minimum natif est toujours inférieur ou égal au heap libre observé au même instant.

## Budget de réserve proposé

Avant d'ajouter une fonction, conserver les seuils suivants :

| Ressource | Réserve recommandée | Situation actuelle |
|---|---:|---:|
| Slot OTA | au moins 256 Kio libres et 20 % du slot visés | 811,7 Kio, soit 45,30 % |
| Heap stable après Wi-Fi | au moins 128 Kio libres | 218,2 Kio |
| Minimum natif sous charge | au moins 96 Kio | 179,7 Kio |
| Plus grand bloc interne | au moins 64 Kio | 108,0 Kio |
| Marge pile `loopTask` | au moins 2 Kio | 3,8 Kio |

Avec la nouvelle table, l'image peut croître d'environ 464 182 octets avant d'atteindre le seuil de réserve de 20 %. Ce n'est pas une invitation à consommer cette marge sans mesure.

Ces mesures décrivent uniquement le firmware actuel avec la pile KNX arrêtée. Les objets de la bibliothèque KNX sont liés et contribuent déjà aux tailles statiques, mais les buffers, sockets multicast, tunnels et charges transitoires d'un routage actif ne sont pas mesurés. Après activation future, il faudra refaire exactement cette campagne avec trafic TP/IP et quatre tunnels, sans extrapoler les chiffres présents.

## Complément 0.4.0 — écoute KNXnet/IP passive

Le firmware final occupe 1 007 593 octets sur un slot de 1 835 008, soit une
marge de 827 415 octets. La RAM statique est de 56 472 octets sur 327 680. Après OTA
et stabilisation Wi-Fi, le heap libre observé allait de 222 884 à 223 420
octets, avec un minimum historique de 214 640 à 218 284 octets. Le journal
circulaire ajoute 12 entrées bornées à 64 octets cEMI et n'écrit pas en flash.
La pile KNX, le routage et les tunnels restent arrêtés.

La version 0.4.1 avec journaux UART/TP utilise 1 009 293 octets de flash et
57 272 octets de RAM statique. La marge d'un slot OTA est de 825 715 octets.

La version 0.4.2 avec essai de polarité UART réversible utilise 1 010 033 octets
de flash et 57 280 octets de RAM statique, soit 824 975 octets libres par slot.

La version 0.4.3, avec capture UART précoce et journal porté à 192 événements,
utilise 1 010 645 octets de flash et 59 200 octets de RAM statique. La marge
reste de 824 363 octets dans chaque slot OTA de 1 835 008 octets. Les journaux
restent bornés en RAM et aucune écriture périodique en flash n'est ajoutée.

La version 0.4.4 avec compteurs d'erreurs UART utilise 1 011 349 octets de
flash et 59 208 octets de RAM statique. Il reste 823 659 octets dans chaque
slot OTA de 1 835 008 octets.

La version 0.4.5 avec test de boucle UART ponctuel utilise 1 012 105 octets de
flash et 59 208 octets de RAM statique. Il reste 822 903 octets dans chaque
slot OTA de 1 835 008 octets.

La version 0.4.6 avec lecture de configuration effective et résultats 8N1/8E1
utilise 1 013 781 octets de flash et 59 320 octets de RAM statique. Il reste
821 227 octets dans chaque slot OTA de 1 835 008 octets.

La version 0.4.7 avec initialisation propre du diagnostic NCN5130 utilise
1 013 997 octets de flash et 59 320 octets de RAM statique. Il reste 821 011
octets dans chaque slot OTA de 1 835 008 octets.
