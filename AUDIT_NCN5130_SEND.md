# Audit du Send Frame Service NCN5130

La table 12 de la fiche NCN5130 définit `U_L_DataEnd` avec `l = dernier index
+ 1`. La trame OFF contient neuf octets, indexés de 0 à 8 : la commande finale
attendue est donc `0x40 | 9 = 0x49`, suivie du FCS `DC`. Les deux essais ont
envoyé `48 DC`, car `TpUartDataLinkLayer::processTxFrameBytes` de thelsing/knx
utilise directement la position du dernier octet. Notre variante avait recopié
ce calcul.

La trame TP `BE 11 FD 10 00 E1 00 80 DC` est longue de neuf octets et son XOR,
FCS compris, vaut `FF`; son checksum `DC` est donc correct. La séquence attendue
est :

```
80 BE  81 11  82 FD  83 10  84 00
85 E1  86 00  87 80  49 DC
```

L'écart `48` au lieu de `49` provoque un rejet de longueur : `47` est
`U_State.ind` avec `receive error`; les huit `17` suivants sont
`U_State.ind` avec `protocol error`, la séquence ayant perdu sa cohérence.

`U_Reset.req=01` est la seule sortie documentée du Busmon. `U_Reset.ind=03`
n'est émis qu'à l'entrée en état Normal, où les services d'émission sont
acceptés. `U_State.ind=07` indique seulement que les cinq erreurs sont absentes;
il ne décrit pas le mode.

`F1 11 FD FF` signifie `U_SetAddress.req`, adresse haute `11`, adresse basse
`FD`, puis dummy `FF`. Le NCN5130 ignore complètement ce dernier octet : il ne
configure ni CRC, ni MARKER, ni répétitions. En revanche, `F1` active l'auto-ACK
pour l'adresse individuelle stockée et pour toutes les adresses de groupe. Il
est donc retiré : la source `1.1.253` est déjà dans la trame TP et l'essai ne
doit acquitter aucun trafic tiers.

Le test hors ligne `tools/test_ncn5130_send_sequence.py` vérifie la longueur,
le XOR, tous les index, `DataEnd=49`, l'absence de `F1` dans l'initialisation et
la séquence complète. `TP_TEST_ARMED=0` interdit tout nouvel essai actif.
