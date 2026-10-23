# Moteur KNX — référence 0.14.0

## Architecture

La tâche UDP est seule propriétaire du socket KNXnet/IP. La tâche NCN5130 est
seule propriétaire d'UART2. Le Web travaille sur des instantanés et des files
bornées ; il n'accède directement ni au socket ni à l'UART.

Les émissions TP de routage et de tunneling partagent un arbitre équitable.
Chaque transaction conserve son origine, son emplacement tunnel éventuel et un
jeton. Une confirmation NCN5130 tardive ne peut donc pas terminer une autre
transaction.

## Tunneling

Cinq emplacements configurables possèdent chacun endpoints contrôle/données,
canal, séquences RX/TX, indication en attente d'ACK, files, répétitions,
temporisation et compteurs. Une sixième connexion reçoit
`E_NO_MORE_CONNECTIONS` (`0x24`). Device Management est une connexion séparée.

La fermeture ou l'expiration d'un client ne libère que sa session. Les doublons
KNXnet/IP sont acquittés sans seconde émission TP. La lecture et la
programmation ETS6 ainsi que Node-RED ont été validées, mais pas cinq clients
échangeant simultanément.

## Routage et filtrage

IP→TP et TP→IP disposent de politiques séparées : blocage, transmission ou
filtrage pour groupes, télégrammes individuels et broadcast. Le filtre de groupe
est un bitmap partagé de 8 192 octets couvrant les 65 536 adresses. La même
décision s'applique aux deux sens lorsque leur politique sélectionne `filtrer`.

L'éditeur Web et KXRF1 acceptent des adresses/plages, sans limite de 64 plages.
L'import textuel est borné à 12 288 octets. La persistance NVS compacte est
versionnée, validée avant remplacement et migrée depuis l'ancien modèle.

Les conversions conservent la source et l'APDU, appliquent les règles KNX de
compteur de routage, reconstruisent les bits de contrôle propres au média et
recalculent le FCS TP. Les files expirent sans rejeu. Des empreintes courtes et
consommées une fois bloquent les échos propres sans supprimer globalement les
répétitions KNX légitimes.

## Activation sûre

`ROUTING_ARMED` autorise ou interdit à la compilation toute activation réelle
du routage. Dans cette référence, la capacité est compilée, mais le démarrage
force les deux sens à l'état passif. Une activation Web explicite est requise ;
la configuration demandée et l'état effectif sont affichés séparément.

Le tunnel n'est pas soumis aux filtres de routage.

## Ressources de référence

| Ressource | Mesure 0.14.0 |
|---|---:|
| Firmware lié | 1 090 597 octets |
| `firmware.bin` réel | 1 097 168 octets |
| Slot OTA | 1 835 008 octets |
| Marge OTA réelle | 737 840 octets |
| RAM statique | 86 904 / 327 680 octets |
| Heap libre observé | 135 816 octets |
| Minimum heap observé | 130 640 octets |
| Plus grand bloc observé | 81 908 octets |
| Marge pile Web / UDP / NCN | 3 420 / 3 720 / 4 408 octets |

La suppression d'une initialisation par agrégat évite la copie temporaire du
bitmap de 8 Kio sur `loopTask` pendant la migration/lecture NVS.

## Limites de validation

- filtres IP→TP et TP→IP validés matériellement avec routage borné ;
- routage multicast bidirectionnel complet et durable encore à valider ;
- pertes multicast du transport Wi-Fi encore connues ;
- cinq sessions ont des tests protocolaires hors ligne, mais cinq clients actifs
  simultanés ne sont pas validés ;
- cible Olimex ESP32-POE-ISO-16MB non validée faute de matériel ;
- aucune certification KNX.
