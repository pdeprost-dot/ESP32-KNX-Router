# Essai Node-RED / KNX Ultimate

## Configuration source sauvegardee

L'export fourni avant toute modification est conserve dans
`nodered/knx_config_original.json`. Il contient un noeud
`knxUltimate-config` avec les parametres suivants :

| Parametre | Valeur d'origine |
|---|---|
| Passerelle | `192.0.2.60:3671` (Siemens N146/02) |
| Protocole | `Auto` |
| Adresse individuelle cliente | `15.15.22` |
| Interface locale | `Auto` |
| Reconnexion automatique | `yes` |
| Temporisation entre telegrammes | `40 ms` |

Le noeud applicatif exporte ecoute toutes les adresses de groupe, conserve le
DPT `1.001` et ne notifie que les ecritures. Aucun identifiant de groupe ni DPT
n'est modifie pour l'essai.

L'adresse `192.0.2.60` est un endpoint unicast. D'apres la configuration de
KNX Ultimate, le mode approprie pour `192.0.2.156` est donc **Tunnel UDP**,
et non Multicast, meme si le nom libre du noeud contient
`Multicast KNX Gateway 224.0.23.12`. Le mode `Auto` sera remplace temporairement
par le choix explicite `Tunnel UDP` pour rendre le test non ambigu.

La version exacte de `node-red-contrib-knx-ultimate` et l'adresse IPv4 du PC
Node-RED restent a relever avant la capture reelle.

## Profil firmware 0.10.1

Le profil Node-RED est distinct du profil ETS6 :

- un seul canal tunneling, adresse cliente preservee `15.15.22` ;
- aucune connexion de gestion et aucune session ETS concurrente ;
- un seul proprietaire du socket UDP et un seul proprietaire d'UART2 ;
- `ROUTING_ARMED=0` inchange : le routage multicast reste interdit ;
- tunnel desactive et NCN5130 en Busmon au demarrage ;
- activation refusee tant que la deconnexion Ethernet du N146 n'a pas ete
  explicitement confirmee dans la session ;
- desactivation : sessions liberees, confirmation effacee et retour Busmon.

Le test hors ligne `tools/test_node_red_tunnel_profile.py` verifie l'adresse
retournee dans la CRD, la limite a une session et la conversion independante
d'un GroupValueWrite OFF `15.15.22` vers `2/0/0`. Il ne constitue pas une
validation materielle.

## Procedure reelle (a executer apres accord)

1. Verifier le firmware, les pages Web, Busmon, le tunnel arrete et les files
   vides.
2. Fermer ETS6 et sauvegarder/exporter le flow Node-RED complet.
3. Debrancher uniquement l'Ethernet du N146/02 ; conserver le bus KNX alimente.
4. Confirmer cette intervention dans `/knx`, puis activer le profil Node-RED.
5. Dans KNX Ultimate, ne changer que l'IP en `192.0.2.156` et le protocole
   en `Tunnel UDP`. Conserver le port `3671`, l'adresse `15.15.22`, les adresses
   de groupe, les DPT et tous les autres champs.
6. Deployer le flow, verifier la session puis actionner un interrupteur KNX pour
   observer une remontee TP.
7. Pour l'emission, utiliser une seule injection booleenne `false` vers un noeud
   explicitement limite a `2/0/0`, DPT `1.001`. Aucun ON ni automatisme.
8. Relever les echanges et demander la confirmation de l'effet physique.
9. Desactiver le tunnel, verifier Busmon, restaurer l'export d'origine et
   seulement alors reconnecter l'Ethernet du N146.

La fiabilite Wi-Fi unicast/multicast reste une limite connue du prototype Wemos
et sera reprise sur la cible Olimex Ethernet.
