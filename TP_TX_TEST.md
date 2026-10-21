# Essai d'émission TP ciblé

## Périmètre de sécurité

- source fixe : `1.1.253` ;
- destination fixe : `2/0/0` ;
- service : `GroupValueWrite`, valeur ON ou OFF explicite ;
- `ROUTING_ARMED=0`, tunnels et retransmissions automatiques arrêtés ;
- aucun rejeu des journaux ;
- aucun `U_ACK_REQ` de groupe ; l'adresse configurée dans le NCN5130 ne permet
  que son auto-ACK individuel pour `1.1.253`.

La pile existante construit la trame avec `CemiFrame` et `TpFrame`. Le firmware
quitte le Busmon par `U_Reset`, configure `1.1.253`, vérifie `U_State`, envoie
la trame, attend `U_L_Data.con`, puis restaure le Busmon passif.

## Résultat réel de l'unique OFF — 21 octobre 2026

L'OTA 0.5.2 a conservé les paramètres, repris le Wi-Fi en 2,3 s et retrouvé le
NCN5130 (`U_Reset.ind=03`, `U_State.ind=07`). Une seule commande OFF a été
demandée de `1.1.253` vers `2/0/0`.

- trame TP construite : `BE 11 FD 10 00 E1 00 80 DC` ;
- retour UART brut : `03 21 07 47 17 17 17 17 17 17 17 17` ;
- confirmation `U_L_Data.con` : absente ;
- répétition confirmée : aucune ;
- observation KNX/IP du Siemens avec source `1.1.253` : absente ;
- erreurs UART parité/trame/débordement : `0/0/0` ;
- état final : Busmon passif restauré par `05`.

La demande remise à l'UART est donc prouvée, mais pas l'émission TP. Aucun
second OFF ni aucun ON n'a été envoyé.

Le journal a révélé que la version 0.5.2 appelait `flush()` après chaque octet,
contrairement à la boucle d'émission de la pile, et étalait les neuf paires
`U_L_DATA` sur environ 5 ms. La version 0.5.3 transmet toute la séquence en
rafale puis attend une seule fois la vidange matérielle. Cette correction est
déployable sans provoquer d'émission ; sa validation active attend une nouvelle
autorisation après confirmation de l'effet physique du premier essai.
