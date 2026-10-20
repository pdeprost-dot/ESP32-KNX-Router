# Écoute KNXnet/IP passive — version 0.4.0

Le listener rejoint `224.0.23.12:3671` sur l'interface Wi-Fi STA et se
réinscrit après chaque nouveau DHCP. `ROUTING_ARMED=0` reste imposé par
`static_assert`. La pile KNX complète, le tunneling, l'émission TP et les deux
sens de routage ne sont pas démarrés. Les observations ne sont jamais mises en
file ni rejouées.

L'adhésion multicast peut produire les rapports IGMP normaux de la pile IP ; le
firmware n'émet aucun datagramme KNXnet/IP applicatif.

## Réception et mémoire

Au plus quatre datagrammes sont traités par passage dans `loop()`. Les paquets
de plus de 512 octets sont rejetés. Avant le décodeur `thelsing/knx`, le code
valide l'en-tête, la version 1.0, la longueur, `ROUTING_INDICATION`, les bornes
des informations additionnelles et la longueur NPDU. Le décodeur existant
valide ensuite le cEMI et exige `L_data_ind`.

Le journal circulaire contient 12 entrées et au plus 64 octets cEMI bruts par
entrée. Un remplacement ou une entrée reçue pendant la pause est comptabilisé
comme perte. La pause fige le journal, pas les compteurs. Aucun accès périodique
NVS ou SPIFFS n'est effectué. Aucun DPT n'est déduit des données brutes.

## Diagnostic si aucun télégramme n'apparaît

1. Si les datagrammes et types ignorés augmentent, le transport multicast
   fonctionne, mais aucune `ROUTING_INDICATION` n'arrive. Vérifier l'existence
   d'un télégramme TP et la table/configuration du N146/02.
2. Si aucun datagramme n'arrive malgré une capture positive ailleurs, vérifier
   IGMP snooping, isolation Wi-Fi, VLAN et réinscription multicast.
3. Si les erreurs augmentent, capturer sur un poste tiers et comparer en-tête,
   longueur et cEMI pour isoler réception et décodage.

La configuration Siemens ne doit pas être modifiée automatiquement. Pour
l'essai, actionner un interrupteur KNX puis relever dans `/knx` la source, la
destination, l'APCI, le compteur de routage et les octets bruts.

## Validation du 20 octobre 2026

L'OTA 0.3.3 vers 0.4.0 a réussi. Le Wi-Fi est revenu sur `example-wifi` à
`192.0.2.156`, RSSI -74 dBm. `/api/status`, `/knx` et `/ota` ont répondu et
les paramètres NVS ont été conservés. L'inscription multicast a reçu quatre
datagrammes, tous d'un type autre que `ROUTING_INDICATION`, sans erreur de
format. Aucun télégramme routé n'était donc décodable dans cette fenêtre.

Le binaire final occupe 1 007 593 octets sur 1 835 008 (marge OTA 827 415 octets) et
56 472 octets de RAM statique. Le heap libre s'est stabilisé autour de 223 kio.
Après plusieurs consultations, ICMP répondait encore sans perte mais avec une
latence de 295 à 1 571 ms, tandis que HTTP expirait. Les commandes Web restent
à confirmer en situation radio stable ; ce résultat ne permet pas de conclure
entre liaison radio faible et saturation temporaire du serveur.

Un essai réel antérieur à la correction d'affichage finale a reçu six
`ROUTING_INDICATION` valides de `192.0.2.60:3671`, sans erreur : trois
écritures de `15.15.22` vers `2/0/0` et trois de `1.1.211` vers `2/1/0`.
Les cEMI observés se terminaient alternativement par `00 80` et `00 81` :

```
29 00 BC D0 FF 16 10 00 01 00 80
29 00 BC D0 FF 16 10 00 01 00 81
29 00 BC D0 11 D3 11 00 01 00 80
29 00 BC D0 11 D3 11 00 01 00 81
```

Ils ont été classés `GroupValueWrite`, groupe, compteur de routage 5 et
« candidat TP — non transmis, mode écoute ». Aucune valeur DPT n'est déduite.
Après l'OTA finale, les commandes pause, reprise et effacement ont toutes été
confirmées par HTTP. Deux datagrammes `0x0201` (SearchRequest) ont aussi été
correctement comptés comme types ignorés, avec zéro erreur.
