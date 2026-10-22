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

L'instance reelle repond sur `192.0.2.200:1880`. La resolution DNS courante
de `HPSERVER` donne en revanche `192.0.2.100`, ou aucun service Node-RED ne
repond : le nom et l'adresse ne doivent donc pas etre assimiles sans corriger le
DNS. L'API d'administration de `.200` repond `401 Bearer`, ce qui interdit de
relever a distance la version sans authentification. La vieille sauvegarde
locale de 2019 n'est pas consideree comme la preuve de la version active.

La version exacte de `node-red-contrib-knx-ultimate` reste a relever dans
**Menu > Manage palette > Nodes > Installed** avant la capture reelle.

En `TunnelUDP`, KNX Ultimate utilise `physAddr` comme adresse source cEMI. Le
profil ESP32 alloue exactement `15.15.22` et renvoie `FF 16` dans la CRD du
`CONNECT_RESPONSE`. A la reception, une source cEMI nulle est remplacee par
l'adresse allouee et toute autre source est refusee. Adresse configuree,
adresse annoncee et source TP sont donc coherentes.

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
   Utiliser le deploiement limite aux noeuds modifies, pas un redeploiement de
   tous les flows. L'export inspecte a `initialread=0` et ne contient aucune
   injection automatique, mais les autres flows de l'instance authentifiee ne
   sont pas audites.
6. Deployer le flow, verifier la session puis actionner un interrupteur KNX pour
   observer une remontee TP.
7. Pour l'emission, utiliser une seule injection booleenne `false` vers un noeud
   explicitement limite a `2/0/0`, DPT `1.001`. Aucun ON ni automatisme.
8. Relever les echanges et demander la confirmation de l'effet physique.
9. Desactiver le tunnel, verifier Busmon, restaurer l'export d'origine et
   seulement alors reconnecter l'Ethernet du N146.

La fiabilite Wi-Fi unicast/multicast reste une limite connue du prototype Wemos
et sera reprise sur la cible Olimex Ethernet.

## Validation reelle du 22 octobre 2026

- instance active identifiee : Node-RED `192.0.2.200:1880`, module
  `node-red-contrib-knx-ultimate` 3.3.9 ;
- N146 debranche en Ethernet avant activation ; bus KNX reste alimente ;
- connexion TunnelUDP depuis `192.0.2.200:58744`, canal 1, sans refus ;
- `CONNECT_REQUEST` :
  `06 10 02 05 00 1A 08 01 00 00 00 00 00 00 08 01 00 00 00 00 00 00 04 04 02 00` ;
- `CONNECT_RESPONSE` :
  `06 10 02 06 00 14 01 00 08 01 C0 A8 32 9C 0E 57 04 04 FF 16` ;
- adresse allouee et source attendue coherentes : `FF 16` = `15.15.22` ;
- 4 requetes tunnel ont produit 4 emissions TP confirmees, 0 echec ;
- 14 indications TP remontees au tunnel, 12 ACK recus, 0 perte UDP TX ;
- UART : 0 erreur de parite, 0 erreur de trame, 0 debordement ;
- l'utilisateur a confirme que les commandes ON/OFF generees depuis Node-RED
  ont commande la lampe. Le scenario reel a donc comporte plusieurs commandes,
  dont ON, au lieu de l'unique OFF initialement prevu ; aucune commande
  supplementaire n'a ete emise par les outils de validation ;
- le journal UART circulaire avait ecrase 785 entrees : les compteurs ci-dessus
  sont certains, mais la capture ne permet pas de presenter une chronologie
  exhaustive ni d'exclure tous les doublons paquet par paquet ;
- heap libre observe : 164 488 octets ; marges de pile : Web 1 868 octets,
  UDP 2 784 octets, NCN5130 4 376 octets ; arbitre UART libre ;
- `ROUTING_ARMED=0` et routage multicast inactif pendant tout l'essai.

Etat a la fin du releve : tunnel Node-RED encore actif, session connectee. Le
choix de le conserver ou de restaurer le N146 doit etre explicite. Pour le
retour arriere : remettre le profil en Busmon, restaurer l'export sauvegarde
(`192.0.2.60`, protocole `Auto`) par deploiement limite, puis reconnecter
l'Ethernet du N146.
