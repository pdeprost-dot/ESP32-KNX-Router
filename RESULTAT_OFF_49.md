# Résultat de l'essai OFF avec `U_L_DataEnd=49`

> Rectificatif : cet essai a démontré que `49` ne changeait pas la réponse,
> mais pas que `49` était correct. L'audit des diagrammes complets conclut que
> le checksum n'est pas indexé et que `48` est la valeur attendue. La cause du
> rejet reste inconnue; voir `AUDIT_NCN5130_SEND.md`.

Essai unique réalisé le 21 octobre 2026 avec `TP_TEST_ARMED=1` temporaire,
`ROUTING_ARMED=0`, sans `F1` et sans ON.

## Émission UART

Initialisation et sortie de Busmon :

```
TX 01  RX 03  TX 02  RX 07
```

Rafale réellement remise au pilote UART au même milliseconde :

```
80 BE  81 11  82 FD  83 10  84 00
85 E1  86 00  87 80  49 DC
```

Trame TP demandée : `BE 11 FD 10 00 E1 00 80 DC`, source `1.1.253`, groupe
`2/0/0`, `GroupValueWrite OFF`.

## Réponses NCN5130

Six millisecondes après la rafale :

```
47 17 17 17 17 17 17 17 17
```

- `47` : `U_State.ind`, receive error actif ;
- chaque `17` : `U_State.ind`, protocol error actif ;
- aucune `U_L_Data.con` positive ou négative ;
- aucune erreur UART matérielle et aucune perte de journal.

## Observation KNX/IP et retour sûr

Le journal multicast n'a reçu aucun télégramme du Siemens avec source
`1.1.253` et destination `2/0/0`. L'émission TP n'est donc pas confirmée.
L'application a envoyé `05` après le délai et restauré le Busmon passif.

Une seconde OTA a ensuite remis `TP_TEST_ARMED=0`. L'état final vérifié est :
Busmon passif, écoute multicast active, tunnels inactifs et routage désactivé.
L'effet physique reste à confirmer par l'utilisateur, même si les absences de
confirmation TP et d'observation IP rendent un effet improbable.
