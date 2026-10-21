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
