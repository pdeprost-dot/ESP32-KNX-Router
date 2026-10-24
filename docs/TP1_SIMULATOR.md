# Simulateur TP1 de développement

Cette cible permet de tester KNXnet/IP sur l'Olimex sans NCN5130. Elle ne
simule pas une installation KNX et ne prouve jamais une émission physique.

## Cause du refus 0x27

Le serveur refusait `CONNECT_REQUEST` avec `0x27` parce que son état `ready`
n'est normalement établi qu'après les réponses `U_Reset.ind` et `U_State.ind`
du NCN5130. Sans transceiver, l'interface TP est donc indisponible. Le statut
`0x24` est, lui, réservé à l'absence de canal/adresse disponible.

## Compilation

```text
platformio run -e olimex_poe_iso_16mb_wifi_simulated
```

Les cibles `wemos_d1_mini32`, `olimex_poe_iso_16mb` et
`olimex_poe_iso_16mb_wifi` restent en `TP1_MODE_PHYSICAL`. La simulation est
donc impossible dans un binaire de production construit avec ces cibles.

## Comportement

- démarrage passif, routage automatique inactif ;
- aucune ouverture ni écriture d'UART2 ;
- entrée en mode tunnel uniquement sur activation explicite du serveur ;
- validation de la longueur et du FCS des trames TP soumises ;
- confirmation positive différée de 20 ms par défaut ;
- prochaine confirmation positive, négative ou absente configurable ;
- injection explicite d'une trame TP valide ;
- files UDP/UART-logiques et arbitrage de production réutilisés sans seconde
  implémentation KNXnet/IP.

La page `/tp1-sim`, présente uniquement dans la cible simulée, affiche
`TP1 MODE: SIMULATED`, `PHYSICAL NCN5130: NOT CONNECTED`, les compteurs, le
choix du résultat de la prochaine émission et l'injection hexadécimale. Une
injection ne produit aucune réponse applicative automatique.

## Limites

Les confirmations sont celles du simulateur logiciel. Elles valident le cycle
KNXnet/IP et l'arbitrage interne, pas le timing électrique TP1, les ACK bus, la
collision, ni la présence d'un participant. Les scénarios matériels doivent
être répétés avec une cible physique et un NCN5130.
