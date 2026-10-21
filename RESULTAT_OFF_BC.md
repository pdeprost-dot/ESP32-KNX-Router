# Résultat de l'essai OFF avec contrôle TP `BC`

Essai unique réalisé le 21 octobre 2026, source `1.1.253`, destination `2/0/0`,
sans `F1`, sans ON, avec routage et tunnels arrêtés.

## UART instrumenté

Séquence demandée :

```
80 BC 81 11 82 FD 83 10 84 00
85 E1 86 00 87 80 48 DE
```

Les neuf paires ont été espacées d'environ 2 ms par la boucle Web. Aucun octet
RX n'est apparu pendant les commandes intermédiaires. Après la dernière paire :

```
+22451 us  RX BC
+22482 us  RX 11
+23774 us  RX FD
+26479 us  RX 10
+26508 us  RX 00
+27818 us  RX E1
+29174 us  RX 00
+30526 us  RX 80
+32779 us  RX DE
+35362 us  RX 8B
```

Le NCN5130 a donc renvoyé l'écho exact de la trame, puis une unique
`U_L_Data.con=8B`, confirmation positive. Aucun `U_State.ind` d'erreur et aucune
erreur UART matérielle n'ont été observés.

## KNX/IP

Le Siemens `192.0.2.60:3671` a relayé :

```
29 00 BC D0 11 FD 10 00 01 00 80
```

Décodage : source `1.1.253`, groupe `2/0/0`, `GroupValueWrite`, OFF, compteur
de routage 5. Cela confirme que le télégramme a bien été émis sur TP et reçu
par le Siemens.

## État final

Après confirmation, le firmware a envoyé `05` et restauré Busmon. Une OTA
finale a remis `TP_TEST_ARMED=0`. `ROUTING_ARMED=0`, l'écoute multicast reste
active et les tunnels restent arrêtés. L'effet physique doit encore être
confirmé par l'utilisateur.
