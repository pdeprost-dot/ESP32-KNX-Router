# Moteur de routage bidirectionnel — firmware 0.10.0

## État de sécurité

Le moteur est compilé mais reste inactivable dans cette version :

- `ROUTING_ARMED=0` et `static_assert` ;
- directions persistantes désactivées par défaut ;
- démarrage en Busmon passif ;
- tunnels désactivés au démarrage ;
- aucune file conservée ou rejouée après désactivation/redémarrage.

Le Siemens N146/02 peut donc rester connecté pendant le développement et la
validation hors ligne.

## Architecture consolidée

La tâche UDP reste l'unique propriétaire de `WiFiUDP`. Elle traite désormais
directement le protocole KNXnet/IP (tunnels et ROUTING_INDICATION), indépendamment
de la boucle Web. Seuls les paquets KXDG de diagnostic sont remis à la file de
consommation applicative.

La tâche NCN5130 reste l'unique propriétaire actif d'UART2. Les tunnels ETS et
le routage utilisent la même file de commandes et le même arbitre. Chaque
transaction porte :

- une origine `Tunnel` ou `Routing` ;
- l'index du tunnel lorsqu'il existe ;
- un jeton monotone ;
- une trame TP bornée.

Une confirmation NCN5130 n'est remise qu'à l'origine et au jeton correspondants.
Une confirmation tardive ou orpheline est journalisée et ne termine pas une
autre transaction.

## IP vers TP

Le chemin valide l'en-tête KNXnet/IP, la longueur déclarée, le service
`ROUTING_INDICATION`, le cEMI `L_data_ind`, le compteur de routage, la source et
les filtres persistants. La source KNX est conservée. Le compteur est décrémenté
une fois, le bit cEMI `AckRequested` n'est pas copié dans le contrôle TP et le
FCS est recalculé par `TpFrame`.

La file contient quatre trames au maximum. Une entrée expire après 2 000 ms.
Une file pleine rejette la nouvelle trame sans écraser une ancienne entrée.
L'émission attend le mode normal NCN5130 et la disponibilité de l'arbitre.

## TP vers IP

Une trame TP doit être complète, avoir un FCS valide, passer les filtres et
avoir un compteur de routage non nul. Elle est convertie en `L_data_ind`, sa
source et son APDU sont conservés, son compteur est décrémenté une fois, puis
elle est placée dans la file TX du propriétaire UDP vers le groupe configuré.

Il n'existe aucune file persistante et aucun rejeu après reconnexion.

## Réinjections et répétitions

Les émissions TP et IP mémorisent une empreinte exacte et bornée (huit entrées,
100 ms). Une correspondance est consommée une seule fois. Les paquets IP dont
l'adresse émettrice est l'adresse locale sont également refusés.

Cette règle ne déduplique pas globalement les télégrammes KNX : une répétition
ultérieure, une trame dont un octet diffère ou une nouvelle transaction reste
traitée. Les octets d'écho immédiats de l'émission UART sont déjà consommés par
la tâche NCN5130 et ne sont pas remis au parseur TP.

## Filtres persistants et Web

`/knx-config` expose les options réellement utilisées par le moteur :

- sens IP vers TP ;
- sens TP vers IP ;
- autorisation des destinations de groupe ;
- autorisation des destinations individuelles ;
- plage brute minimale/maximale des adresses de groupe.

La structure NVS passe en version 2. Une configuration version 1 est migrée en
mémoire en conservant l'adresse, le multicast, le port et les délais ; les deux
sens restent désactivés. Une écriture NVS n'a lieu qu'après enregistrement Web
explicite.

`/knx` affiche les directions configurées, l'état effectif, les profondeurs de
file, les émissions/confirmations/expirations, les suppressions d'écho et les
rejets par filtre, compteur, invalidité ou saturation.

## Préparation Ethernet Olimex

Le moteur appelle une petite frontière réseau (`knxNetworkConnected`,
`knxNetworkLocalAddress`, `knxNetworkQueueTx`) au lieu de dépendre directement
du média pour ses émissions. L'adaptateur actuel utilise le Wi-Fi STA et la
tâche UDP existante. Le futur port Olimex devra fournir l'adaptateur Ethernet,
la création/adhésion du socket et une affectation UART propre à la carte.

GPIO16/17 ne sont pas considérés comme disponibles sur l'Olimex. Leur choix
reste limité à la carte ESP32 actuelle.

## Validation hors ligne

`tools/test_bidirectional_router.py` utilise des calculs indépendants du code
embarqué et vérifie :

- vecteur cEMI → TP validé, source conservée, hop 6 → 5, FCS `03` ;
- vecteur TP → ROUTING_INDICATION, source/APDU conservés et nouveau décrément ;
- refus d'un compteur nul ;
- file de quatre éléments sans écrasement et expiration sans rejeu ;
- empreinte exacte, consommée une fois et expirée ;
- exclusion mutuelle tunnel/routage et association des confirmations ;
- présence des verrous passifs dans les sources.

Les tests historiques tunnel ETS, séquence NCN5130, parseur TP et IP→TP restent
également exécutés. La compilation PlatformIO utilise 66 456 octets de RAM
statique et 1 054 521 octets dans un slot de 1 835 008 octets.

## Restant à valider sur matériel

- trafic bidirectionnel réel après autorisation explicite et suppression du
  double chemin avec le Siemens ;
- simultanéité réelle de deux tunnels ETS et du routage sous charge ;
- comportement des répétitions, ACK et confirmations sur collisions réelles ;
- saturation/expiration avec trafic soutenu ;
- adaptation Ethernet et broches UART de l'Olimex ESP32-POE-ISO-16MB ;
- réception multicast sur Ethernet, indépendamment des pertes Wi-Fi suspendues.

## Déploiement passif 0.10.0

L'image a été déployée par OTA sur `192.0.2.156`. Après redémarrage :

- version `0.10.0`, RSSI -48 dBm, BSSID `02:00:00:00:00:01`, aucune
  déconnexion ;
- `/knx`, `/knx-config`, `/api/status` et `/ota` disponibles ;
- adresse `1.1.253`, groupe `224.0.23.12`, port 3671 et délais version 1
  conservés par la migration ;
- directions IP→TP et TP→IP désactivées, file 0/4, arbitre UART libre ;
- Busmon passif, tunnel désactivé, `ROUTING_ARMED=0` ;
- heap libre 163 164 octets et minimum natif 161 648 octets juste après la
  vérification Web.

Aucun essai de routage réel et aucune émission TP applicative n'ont été
effectués pendant cette validation.

