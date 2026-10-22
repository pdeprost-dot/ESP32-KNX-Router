# Tunnels ETS6 unicast (firmware 0.9.4)

## Capacités vérifiées

La dépendance `thelsing/knx` épinglée au commit `980c047` contient les services
KNXnet/IP Connect, ConnectionState, Disconnect, TunnelingRequest/Ack et le
transport cEMI des télégrammes individuels. Sa configuration permet quatre
tunnels, mais elle ne peut pas être démarrée telle quelle dans cette
application : elle créerait un second propriétaire du socket UDP et d'UART2.

Le prototype 0.9.4 réutilise donc exclusivement les deux tâches propriétaires
existantes et expose un serveur borné à **deux sessions tunnel et une session
de gestion distincte** :

- interface physique du prototype : `1.1.253` ;
- adresses individuelles réservées aux clients tunnel : `1.1.254` et
  `1.1.252` ;
- point de terminaison : `192.0.2.156:3671` en UDP unicast ;
- couche de tunnel : link layer (`0x02`) ;
- routage multicast : désactivé par `ROUTING_ARMED=0` ;
- tunnel : désactivé à chaque démarrage.

La tâche UDP est seule propriétaire de `WiFiUDP`; elle traite les acquittements
de tunnel et transmet les réponses par une file bornée. La tâche NCN5130 est
seule propriétaire d'UART2. En mode normal elle n'acquitte sur TP que les
télégrammes individuels destinés à `1.1.254` ou `1.1.252`; elle n'applique aucun auto-ACK
général aux télégrammes tiers.

## Premier essai ETS6

1. Ouvrir `http://192.0.2.156/knx` et cliquer **Activer le tunnel ETS6**.
2. Attendre l'état `NCN5130 : Mode normal prêt`.
3. Dans ETS6, créer/sélectionner une interface KNXnet/IP tunneling manuelle vers
   `192.0.2.156`, port `3671` (pas une interface de routage multicast).
4. Vérifier que la connexion reçoit l'adresse `1.1.254`.
5. Effectuer uniquement la lecture des informations d'un appareil TP connu.
   Ne lancer ni téléchargement, ni programmation, ni opération de masse.
6. Après l'essai, cliquer **Désactiver et revenir en Busmon** et vérifier l'état
   `Bus monitor passif`.

Le Siemens N146/02 peut rester raccordé en Ethernet pendant cet essai unicast :
le prototype ne fait aucun routage multicast.

## Limites de cette première étape

- deux sessions tunnel au maximum et délai d'inactivité de 120 secondes ;
- pas de KNX IP Secure ;
- pas de téléchargement ETS validé ;
- gestion individuelle transparente destinée d'abord à une lecture simple ;
- aucune promesse de reprise/rollback de session après redémarrage ;
- les files UDP/UART sont bornées et une saturation est comptabilisée ;
- ce prototype n'est pas encore un routeur bidirectionnel complet.
- le bouton **Test** d'ETS6 ouvre une connexion tunnel (`0x04`) puis une
  connexion de gestion de périphérique (`0x03`) courte de 24 octets. Elles ont
  des identifiants de canal distincts et n'occupent pas le même emplacement ;
- les `M_PropRead.req` observées pendant le test sont traitées par les objets de
  propriété réels de la pile. Une fonction cEMI de gestion non implémentée est
  refusée explicitement par `E_DATA_CONNECTION` (`0x26`) ;
- `CONNECTIONSTATE` et `DISCONNECT` libèrent chaque type de session séparément.
  Le statut `E_NO_MORE_CONNECTIONS` observé est `0x24` (et non `0x27`).

Le test logiciel `tools/test_knx_tunnel_protocol.py` vérifie indépendamment les
octets de CONNECT_RESPONSE, les canaux distincts, le statut `0x24`, ainsi que
les offsets de canal de CONNECTIONSTATE/DISCONNECT issus de la capture ETS6.

## Validation ETS6 du firmware 0.9.2

Deux actions successives sur le bouton **Test** d'ETS6 ont retourné `Ok`.
Les compteurs embarqués ont confirmé les échanges suivants :

- 2 connexions `DEVICE_MGMT_CONNECTION` acceptées et 2 `DISCONNECT` reçus ;
- 4 `M_PropRead.req`, 4 réponses acquittées et 0 fonction non implémentée ;
- aucune expiration de connexion de gestion ;
- un canal tunnel et un canal de gestion distincts lors de chaque test.

La capture 0.9.1 avait montré que les réponses aux lectures étaient déjà
correctes, mais que le canal de `CONNECTIONSTATE_REQUEST` et de
`DISCONNECT_REQUEST` était lu à tort à l'octet 7. Ces services placent le canal
à l'octet 6 et réservent l'octet 7. La correction 0.9.2 permet la libération
effective du canal de gestion.

ETS peut conserver le canal tunnel principal puis lancer d'autres demandes de
connexion. Avec la limite volontaire d'une seule session tunnel, celles-ci
reçoivent `E_NO_MORE_CONNECTIONS` (`0x24`). ETS peut alors afficher à la fois
`Test : Ok` et une bannière « Il n'y a plus de connexions disponibles » : la
bannière concerne la demande supplémentaire, pas les lectures de gestion qui
viennent de réussir. Il ne faut pas augmenter le nombre de tunnels pour masquer
ce comportement ; libérer/désélectionner la connexion ETS ou désactiver le
tunnel depuis `/knx` rend l'emplacement disponible.

Après la validation, le serveur a été désactivé depuis `/knx-diagnostic` et le
NCN5130 remis en Busmon passif. Aucun téléchargement ETS ni télégramme
applicatif TP n'a été émis.

## Validation 0.9.4 sous charge Web

ETS6 conservait parfois une connexion de travail puis demandait un nouveau
tunnel pour une opération. La limite précédente à un tunnel provoquait alors
`E_NO_MORE_CONNECTIONS` (`0x24`) alors que la première session était encore
valide. Le second emplacement utilise l'adresse libre confirmée `1.1.252` ; il
ne partage ni canal, ni séquences, ni état avec le premier emplacement
`1.1.254`. Une seule émission UART TP reste toutefois autorisée à la fois.

La capture `ets6_read_webload_094.pcapng` contient deux lectures successives de
l'appareil `1.1.7` pendant des consultations répétées de `/knx` :

- première lecture : tunnel canal 1, gestion canal 2 ;
- seconde lecture : tunnel canal 3, gestion canal 4 ;
- les canaux 1 et 3 se sont succédé et n'ont pas coexisté ; chaque
  `DISCONNECT` a libéré sa session avant la suivante ;
- 100 `L_Data.req` ETS uniques, 100 émissions TP et 100 confirmations NCN5130 ;
- 196 remontées cEMI vers ETS, toutes acquittées ;
- aucun doublon `TUNNELING_REQUEST`, aucune réémission TP et aucun statut ACK
  non nul ;
- ACK ESP32 des requêtes ETS : moyenne 23,019 ms, maximum 264,644 ms ;
- ACK ETS des indications ESP32 : moyenne 0,309 ms, maximum 1,586 ms ;
- tâche UDP : 314 messages protocolaires, traitement maximal 863 µs,
  314 envois réussis, aucune erreur, reprise ou perte ;
- files UDP et NCN5130 : aucune saturation ; erreurs UART : 0/0/0 ;
- `/knx` a bloqué la boucle Web jusqu'à 16,073 s, sans bloquer les propriétaires
  UDP et UART ; mutex de l'instantané maintenus 57 µs au total, 30 µs maximum ;
- heap minimal 135224 octets, marges de pile : Web 1932 octets, UDP 2824
  octets, NCN5130 4512 octets.

Le second emplacement est ainsi disponible pour une coexistence réelle, mais
cette capture n'en a pas forcé l'utilisation : ETS a fermé le premier tunnel
avant chaque connexion suivante, et l'adresse allouée est donc restée
`1.1.254`. Après l'essai, les deux tunnels et la gestion ont été libérés, le
serveur désactivé et le NCN5130 restauré en Busmon passif.
