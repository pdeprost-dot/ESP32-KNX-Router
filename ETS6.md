# Premier tunnel ETS6 unicast (firmware 0.9.0)

## Capacités vérifiées

La dépendance `thelsing/knx` épinglée au commit `980c047` contient les services
KNXnet/IP Connect, ConnectionState, Disconnect, TunnelingRequest/Ack et le
transport cEMI des télégrammes individuels. Sa configuration permet quatre
tunnels, mais elle ne peut pas être démarrée telle quelle dans cette
application : elle créerait un second propriétaire du socket UDP et d'UART2.

Le prototype 0.9.0 réutilise donc exclusivement les deux tâches propriétaires
existantes et expose un serveur borné à **une session** :

- interface physique du prototype : `1.1.253` ;
- adresse individuelle réservée au client tunnel : `1.1.254` ;
- point de terminaison : `192.0.2.156:3671` en UDP unicast ;
- couche de tunnel : link layer (`0x02`) ;
- routage multicast : désactivé par `ROUTING_ARMED=0` ;
- tunnel : désactivé à chaque démarrage.

La tâche UDP est seule propriétaire de `WiFiUDP`; elle traite les acquittements
de tunnel et transmet les réponses par une file bornée. La tâche NCN5130 est
seule propriétaire d'UART2. En mode normal elle n'acquitte sur TP que les
télégrammes individuels destinés à `1.1.254`; elle n'applique aucun auto-ACK
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

- une seule session et délai d'inactivité de 120 secondes ;
- pas de KNX IP Secure ;
- pas de téléchargement ETS validé ;
- gestion individuelle transparente destinée d'abord à une lecture simple ;
- aucune promesse de reprise/rollback de session après redémarrage ;
- les files UDP/UART sont bornées et une saturation est comptabilisée ;
- ce prototype n'est pas encore un routeur bidirectionnel complet.

Le test logiciel `tools/test_knx_tunnel_protocol.py` vérifie indépendamment les
octets de CONNECT_RESPONSE (CRD `1.1.254`), TUNNELING_ACK et l'encapsulation cEMI.
