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

## Audit approfondi et preparation 0.10.2

L'utilisateur choisit de conserver Node-RED actif et le N146 debranche. La
version `3.3.9` est celle de `node-red-contrib-knx-ultimate`, pas celle du
runtime Node-RED. L'API d'administration de `192.0.2.200:1880` est protegee
par authentification ; la version exacte du runtime reste a lire dans l'ecran
**About** de cette instance.

### Decouverte

La sonde independante `tools/knx_ip_discovery_probe.py` a etabli sur 0.10.1 :

- `SEARCH_REQUEST` unicast : aucune reponse ;
- `DESCRIPTION_RESPONSE` : 68 octets conformes, IA `1.1.253`, nom
  `ESP32 KNX Tunnel`, medium TP1, familles Core v1, Device Management v1 et
  Tunnelling v1 ; Routing n'est pas annonce ;
- l'entree `224.0.23.12:3671 / Multicast Address / 15.15.199` est ajoutee
  explicitement par `nodes/utils/utils.js` du paquet npm officiel
  `node-red-contrib-knx-ultimate@3.3.9`, apres les resultats de `discover()`.
  Elle est donc synthetique et ne provient pas d'un `SEARCH_RESPONSE` ESP32.

Le firmware 0.10.2 prepare une reponse SEARCH de 76 octets reutilisant les
memes DIB que DESCRIPTION et un HPAI `192.0.2.156:3671`. Le test independant
`tools/test_knx_ip_discovery.py` verifie longueurs, IA, nom et familles. Cette
correction est compilee mais pas encore deployee afin de ne pas interrompre le
tunnel Node-RED 0.10.1 sans preparation de reprise.

### Compteurs et collecte

`tools/collect_knx_runtime.py` produit sur le PC un JSONL borne avec trois
rotations, sans ecriture dans la flash ESP32. Il releve `/api/status` et un
instantane `/knx`, continue apres une interruption Wi-Fi et distingue les
compteurs cumules du journal d'affichage ecrase.

0.10.2 ajoute des compteurs cumules distincts pour doublons tunnel, erreurs de
sequence, ACK errones et confirmations TP positives, negatives ou absentes par
timeout. Le profil prepare conserve Node-RED en `15.15.22`, rend le second
canal `1.1.252` disponible pour ETS et separe toujours la connexion de gestion.
L'ACK individuel NCN5130 est decide a partir des adresses des sessions
reellement connectees.

### Reference 0.10.1 avant OTA

Collecte `captures/node-red-baseline-0.10.1.jsonl` effectuee sur 1 790,001 s
(29 min 50 s entre premier et dernier echantillon, campagne murale de 30 min),
180 echantillons et 0 echec HTTP :

| Mesure | Debut | Fin |
|---|---:|---:|
| Heap libre API | 164 460 | 161 332 octets |
| Minimum historique | 148 208 | 145 928 octets |
| Plus grand bloc interne | 106 484 | 102 388 octets |
| Marge pile Web | 1 804 | 1 788 octets |
| Requetes / TP confirmes / echecs | 7 / 7 / 0 | 9 / 9 / 0 |
| ACK / indications tunnel | 18 / 20 | 34 / 40 |
| UDP TX succes / erreurs / reprises / pertes | 66 / 0 / 0 / 0 | 148 / 0 / 0 / 0 |
| UART TX / RX | 152 / 939 | 206 / 1 125 octets |

La session est restee sur le canal 1, sans DISCONNECT ni expiration. RSSI de
-51 a -45 dBm ; aucune erreur UART de parite, trame ou debordement. Le trafic
normal a ajoute deux requetes toutes deux confirmees et vingt indications. Le
heap libre echantillonne varie jusqu'a 161 296 octets et le minimum historique
baisse de 2 280 octets sous les consultations periodiques ; cette seule fenetre
ne prouve pas une fuite, mais constitue la reference a comparer apres OTA.

### OTA et reprise 0.10.2

La derniere version connue du runtime HPSERVER est `4.0.8`. Les ressources
publiques de l'editeur prouvent une interface de generation 4.x, mais n'exposent
pas la version exacte ; `/settings` reste protege par authentification. `4.0.8`
est donc conserve comme information connue, pas comme mesure distante.

OTA 0.10.2 reussie. Apres redemarrage :

- retour automatique sur `example-wifi`, IP `192.0.2.156`, RSSI initial -42 dBm ;
- `/`, `/knx`, `/knx-config`, `/ota` et `/api/status` en HTTP 200 ;
- `ROUTING_ARMED=0`, routage multicast inactif ;
- serveur tunnel revenu **desactive par defaut**, NCN5130 en Busmon : le profil
  Node-RED n'est pas persistant dans cette version ;
- Node-RED a detecte la perte et tente automatiquement un nouveau CONNECT depuis
  `192.0.2.200:51879`, refuse `0x27` pendant que le serveur etait passif ;
- apres confirmation manuelle du N146 debranche puis activation manuelle du
  profil, Node-RED s'est reconnecte sans modification de flow depuis
  `192.0.2.200:54888`, canal 1, adresse `15.15.22`, statut `0x00` ;
- juste apres reconnexion : 0 requete applicative, 0 emission TP et 0 indication.
  Aucun ancien telegramme n'a ete rejoue par l'ESP32 ou par le flow observe.

La decouverte unicast reelle valide SEARCH (76 octets) et DESCRIPTION
(68 octets) : endpoint `192.0.2.156:3671`, IA `1.1.253`, nom
`ESP32 KNX Tunnel`, DIB complets et familles Core/Device Management/Tunnelling.
Routing n'est pas annonce. La distribution d'une requete multicast par le LAN
reste une question de transport distincte et n'est pas deduite de cet essai
unicast.

## Coexistence Node-RED et ETS6 sous charge Web

Une lecture ETS6 de `1.1.7` a ete executee pendant que Node-RED restait connecte
et que `/knx` etait consulte. Les deux canaux ont coexiste, puis ETS a ferme ses
connexions sans laisser de session occupee :

- Node-RED : canal 1, adresse `15.15.22`, session maintenue ;
- ETS6 : second tunnel, adresse `1.1.252`, puis DISCONNECT propre ;
- gestion ETS : une connexion, deux requetes acquittees, DISCONNECT propre ;
- ETS : 50 requetes TP, 50 confirmations positives, 0 negative, 0 timeout ;
- files NCN5130 : 0 saturation sur 8 ; erreurs UART : 0/0/0 ;
- heap libre 161 308 octets, plus grand bloc interne 106 484 octets ; marges de
  pile Web/UDP/NCN5130 1 788/2 836/4 444 octets.

La capture a aussi revele 35 ACK ETS et 2 ACK Node-RED classes en erreur alors
que le dialogue TP etait integralement confirme. L'analyse du code etablit que
plusieurs `TUNNELLING_REQUEST` sortants pouvaient etre simultanement en vol et
que seul le dernier numero de sequence etait accepte. Il s'agit d'un defaut de
flux sortant du serveur, pas d'une preuve de perte reseau.

La preparation `0.10.3-dev` remplace ce comportement par une file bornee de
huit cEMI par session et un stop-and-wait : un seul paquet attend son ACK, avec
le meme numero et le meme contenu pour deux repetitions au plus, timeout a
1 000 ms et compteurs distincts de file pleine, repetition, timeout, ACK
duplique et ACK invalide. Le socket reste exclusivement gere par la tache UDP ;
l'UART2 reste exclusivement gere par la tache NCN5130. Tests hors ligne
`tools/test_tunnel_tx_flow.py`, decouverte et routeur bidirectionnel : OK.
Compilation : RAM statique 68 656 / 327 680 octets ; flash
1 058 813 / 1 835 008 octets.

OTA `0.10.3-dev` reussie. Wi-Fi, `/`, `/api/status` et `/knx` sont revenus ; le
serveur a demarre passif comme prevu. Apres confirmation manuelle du N146 reste
debranche et reactivation du profil, Node-RED s'est reconnecte automatiquement
depuis `192.0.2.200:54328`, canal 1, adresse `15.15.22`. Au premier bilan :
6 requetes, 5 emissions TP toutes confirmees, 9 indications toutes acquittees,
0 erreur de sequence/ACK, 0 repetition, timeout, file pleine ou ACK duplique ;
file vide et aucune emission en attente. Ces cinq requetes sont du trafic de
reconnexion du flow Node-RED ; leur nature applicative n'a pas ete deduite des
seuls compteurs. SEARCH 76 octets et DESCRIPTION 68 octets restent valides.
