# Audit des ressources du firmware 0.2.1

Date : 2026-10-20. Cible réelle : ESP32-D0WD-V3 rev. 3.1, flash 4 Mio, sans PSRAM. ESP_BASE 2.4.1 n'a pas été modifié et `ROUTING_ARMED=0` est resté actif pendant toutes les mesures.

## Flash et RAM statique

| Ressource | Capacité | Utilisée | Restante | Utilisation |
|---|---:|---:|---:|---:|
| Emplacement application OTA | 1 310 720 o | 1 003 824 o, taille réelle de `firmware.bin` | 306 896 o | 76,58 % |
| Charge calculée par l'éditeur de liens | 1 310 720 o | 997 245 o | 313 475 o | 76,08 % |
| RAM statique annoncée par PlatformIO | 327 680 o | 55 232 o | 272 448 o | 16,86 % |

La taille du fichier binaire est la valeur prudente pour vérifier qu'une image tient dans un slot OTA. La mesure de l'éditeur de liens exclut certains en-têtes et alignements de l'image flash, d'où les 6 579 octets d'écart.

## Table de partitions effective

Table décodée directement depuis `.pio/build/wemos_d1_mini32/partitions.bin` :

| Partition | Type | Offset | Taille |
|---|---|---:|---:|
| `nvs` | données NVS | `0x009000` | 20 480 o (20 Kio) |
| `otadata` | métadonnées OTA | `0x00E000` | 8 192 o (8 Kio) |
| `app0` | application `ota_0` | `0x010000` | 1 310 720 o (1 280 Kio) |
| `app1` | application `ota_1` | `0x150000` | 1 310 720 o (1 280 Kio) |
| `spiffs` | système de fichiers | `0x290000` | 1 441 792 o (1 408 Kio) |
| `coredump` | diagnostic système | `0x3F0000` | 65 536 o (64 Kio) |

Les deux slots application ont la même capacité. La marge physique actuelle de 306 896 octets s'applique donc aussi bien à une mise à jour OTA qu'au slot actif. SPIFFS est réservé par la table, même si l'application KNX actuelle ne l'utilise pas directement. L'application stocke sa configuration dans NVS, espace partagé avec la configuration ESP_BASE.

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
| Slot OTA | au moins 256 Kio libres et 20 % du slot visés | 299,7 Kio, soit 23,42 % |
| Heap stable après Wi-Fi | au moins 128 Kio libres | 218,2 Kio |
| Minimum natif sous charge | au moins 96 Kio | 179,7 Kio |
| Plus grand bloc interne | au moins 64 Kio | 108,0 Kio |
| Marge pile `loopTask` | au moins 2 Kio | 3,8 Kio |

La contrainte la plus proche est la flash : pour conserver simultanément 20 % de marge, l'image ne devrait pas croître de plus d'environ 44 752 octets. Ce n'est pas une invitation à optimiser maintenant, mais un seuil de revue.

Ces mesures décrivent uniquement le firmware actuel avec la pile KNX arrêtée. Les objets de la bibliothèque KNX sont liés et contribuent déjà aux tailles statiques, mais les buffers, sockets multicast, tunnels et charges transitoires d'un routage actif ne sont pas mesurés. Après activation future, il faudra refaire exactement cette campagne avec trafic TP/IP et quatre tunnels, sans extrapoler les chiffres présents.
