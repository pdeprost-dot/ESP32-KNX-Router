# Audit du Send Frame Service NCN5130

## Conclusion actuelle

La cause du rejet n'est pas encore identifiée. Les réponses `47`, puis huit
`17`, ont été identiques avec `U_L_DataEnd=48` et `49`; ce remplacement n'a donc
pas résolu le défaut et ne prouve pas que l'un ou l'autre est la cause.

## Preuves

- Vraie trame TP capturée : `BC 11 0B 10 0A E1 00 80 22`.
- cEMI Siemens correspondant : `29 00 BC D0 11 0B 10 0A 01 00 80`.
- La conversion `CemiFrame::fillTelegramTP` de thelsing copie CTRL1 comme
  contrôle TP et reconstruit NPCI/LG; elle calcule ensuite le FCS.
- Notre construction avait posé `AckRequested=0x02`, produisant `BE`; la capture
  réelle utilise `BC`. Ce bit cEMI ne doit pas être présent dans le contrôle TP.
- Avec contrôle `BC`, la candidate devient `BC 11 FD 10 00 E1 00 80 DE`; son
  XOR, FCS compris, vaut `FF`.
- Aucune commande n'était intercalée dans les rafales capturées. Les journaux
  sont écrits immédiatement avant chaque appel `HardwareSerial.write`; ils
  prouvent les appels au pilote, pas les niveaux électriques sur GPIO17.

## U_L_DataEnd

La table NCN5130 dit `l = last index + 1`. Les diagrammes complets montrent les
octets de données indexés, puis `U_L_DataEnd`, puis le checksum comme octet
suivant. Le checksum n'est donc pas lui-même une donnée indexée. Pour cette
trame, la dernière donnée APDU est à l'index 7 : `l=8`, soit `DataEnd=48`.
Cette lecture concorde avec thelsing/knx, qui utilise la position 8 lorsque sa
boucle atteint le FCS. La précédente affirmation définitive en faveur de `49`
était erronée.

## Initialisation et sécurité

`U_Reset.req=01` est la seule sortie documentée de Busmon et `U_Reset.ind=03`
atteste l'entrée en état Normal. `U_State.ind=07` ne décrit que les erreurs.
`F1 11 FD FF` active l'auto-ACK individuel et de groupe; `FF` est un dummy
ignoré. `F1` reste exclu de l'essai afin de ne confirmer aucun trafic tiers.

## Instrumentation préparée

La future émission est transformée en automate : une paire service/donnée est
écrite toutes les 700 microsecondes, tandis que RX est lu entre les paires. Les
événements sont horodatés avec `micros()` et associés au numéro de la dernière
paire envoyée. Cela permettra de déterminer si `47` apparaît après Start,
pendant les Cont, ou après End/FCS. Aucun essai n'a été lancé après cette
modification et `TP_TEST_ARMED=0` reste prioritaire.

Le test hors ligne utilise comme oracle la vraie paire cEMI/TP capturée, et non
le calcul de l'implémentation testée. Il vérifie `BC`, le FCS `DE`, les index
`80..87`, puis `48 DE`.
