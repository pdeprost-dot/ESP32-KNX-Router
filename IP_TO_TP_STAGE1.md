# Routage IP vers TP — première étape bornée

Version préparée : `0.6.0`. `ESP_BASE 2.4.1` reste inchangé et le verrou global
`ROUTING_ARMED=0` reste compilé. Cette étape ajoute un mode applicatif manuel,
désactivé au démarrage, qui n'est pas un routeur KNX bidirectionnel complet.

## Périmètre et verrous

- entrée : `ROUTING_INDICATION` valide reçu sur `224.0.23.12:3671` par la STA ;
- seule destination admise : `2/0/0` ;
- seul service admis : `GroupValueWrite` ;
- adresse source cEMI conservée ; compteur de routage décrémenté de un, et
  refus si sa valeur reçue est zéro ;
- bit `AckRequested` propre au cEMI supprimé avant conversion TP ; FCS recalculé
  par `TpFrame` de la pile thelsing/knx ;
- sortie TP vers IP, tunnels et services de la pile KNX non démarrés ;
- aucune commande `F1`, donc aucun auto-ACK général de télégrammes tiers ;
- file FIFO RAM de 4 éléments, expiration après 2 s, attente bornée de
  `U_L_Data.con` pendant 2,5 s ; aucune persistance ni reprise après redémarrage ;
- désactivation : file supprimée, retour immédiat en Busmon, confirmation de
  déconnexion Siemens oubliée ;
- l'écho UART de l'émission sert seulement à vérifier la transaction courante.
  Il n'alimente ni la file IP→TP ni une sortie TP→IP.

L'activation Web nécessite deux opérations distinctes dans la même session :
confirmer que l'Ethernet du Siemens est débranché, puis activer le mode borné.
Un redémarrage revient toujours en passif et exige une nouvelle confirmation.

## Validation logicielle

`tools/test_ip_to_tp_stage1.py` utilise une référence construite séparément du
code embarqué. Pour le futur datagramme de validation `15.15.254 -> 2/0/0`, hop
IP 6 et OFF, il attend :

```
cEMI : 29 00 BE E0 FF FE 10 00 01 00 80
TP   : BC FF FE 10 00 D1 00 80 03
UART : 80 BC 81 FF 82 FE 83 10 84 00 85 D1 86 00 87 80 48 03
```

Le test vérifie notamment la source conservée, le passage hop 6 à 5, le contrôle
TP `BC`, le FCS `03` et `U_L_DataEnd=48`.

## Validation réelle à poursuivre

Le déploiement initial doit rester passif avec le Siemens connecté. Après
confirmation explicite de sa déconnexion Ethernet, l'essai prévu consiste en un
seul GroupValueWrite OFF émis par le PC avec la source de validation
`15.15.254`. Cette adresse est réservée à cet essai et doit rester absente de la
ligne. Il faudra distinguer réception IP, mise en file, octets UART, écho,
`U_L_Data.con=8B` et effet physique. Aucun ON n'est automatique.

Après l'essai, le mode doit être remis en passif avant de reconnecter le Siemens.

## Résultats réels du 21 octobre 2026

Le chemin fonctionnel a été validé de bout en bout avec un datagramme
`ROUTING_INDICATION` envoyé en **unicast** depuis `192.0.2.123:43671` vers
`192.0.2.156:3671` :

- cEMI reçu : `29 00 BE E0 FF FE 10 00 01 00 80` ;
- décision : `15.15.254 -> 2/0/0`, GroupValueWrite OFF, hop IP 6 ;
- TP construit : `BC FF FE 10 00 D1 00 80 03`, hop TP 5 ;
- services NCN5130 :
  `80 BC 81 FF 82 FE 83 10 84 00 85 D1 86 00 87 80 48 03` ;
- écho reçu : `BC FF FE 10 00 D1 00 80 03` ;
- confirmation : `U_L_Data.con=8B` ;
- effet physique confirmé par l'utilisateur : lampe éteinte.

Le compteur final de l'essai est `1 envoyé / 1 confirmé / 0 échec / 0 expiré`.
Le firmware a ensuite supprimé la file, oublié la confirmation de déconnexion
du Siemens et restauré Busmon passif. Aucun ON n'a été émis.

Ce résultat valide l'application IP vers TP, mais l'unicast n'est pas le
transport normal d'un routeur KNXnet/IP. Le multicast a donc été contrôlé
séparément en mode passif. Une capture TShark sur l'interface physique Wi-Fi a
ensuite prouvé la sortie du paquet PC :

```
Ethernet : 02:00:00:00:00:01 -> 02:00:00:00:00:01
IPv4     : 192.0.2.123 -> 224.0.23.12, TTL 1
UDP      : 43671 -> 3671
Charge   : 0610053000112900bee0fffe1000010080
```

L'ESP32 a reçu et décodé ce paquet multicast pendant le même essai passif : les
compteurs sont passés de 155/21 à 157/22 (datagrammes/télégrammes valides), le
second datagramme étant un service non-routing ignoré. La sortie multicast PC
et sa réception ESP32 sont donc validées sans émission TP. Une nouvelle
`ROUTING_INDICATION` du N146 après sa reconnexion reste à provoquer et observer
pour valider séparément son trafic de routage actuel.

Une capture passive supplémentaire de 20 secondes a toutefois confirmé que le
N146 reconnecté est joignable et répond depuis `192.0.2.60:3671` (MAC
`02:00:00:00:00:01`). La trame capturée est un `SEARCH_RESPONSE` `0x0202` en
unicast vers le PC, pas une `ROUTING_INDICATION`. Elle prouve la présence IP du
N146, mais pas une exportation récente du bus. La vérification discriminante
suivante consiste à produire un nouveau télégramme TP identifiable, sans viser
la lampe de test, tout en capturant `192.0.2.60 -> 224.0.23.12:3671` et en
comparant le journal ESP32.
