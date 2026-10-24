# Validation hors ligne du POC KNX intersites L3

Date : 24 octobre 2026

Branche : `feature/knx-intersite-l3`

Base : `d29a701`, support TP1 étendu
Firmware installé : inchangé, 0.15.4

## Architecture livrée

Le POC ajoute une couche UDP unicast indépendante de KNXnet/IP. Il réutilise :

- le codec TP1/cEMI borné ;
- la file et l'arbitrage d'émission NCN5130 ;
- le suivi des confirmations `U_L_Data.con` ;
- l'anti-écho des émissions locales ;
- les contrôles KNX de source, topologie et hop count.

La tâche `knxL3` est seule propriétaire de son socket. Elle ne touche jamais
UART2. Les échanges avec le moteur se font par deux files FreeRTOS bornées.

La configuration KXL3 est stockée sous une nouvelle clé NVS `l3config` : aucune
migration ni modification des clés du routeur, des tunnels ou de Node-RED. Une
configuration absente est normale. Même configuré, le service démarre inactif.

## Tests déterministes

Commande : `python tools/test_knx_intersite_l3.py`.

Résultat : PASS pour :

- encodage/décodage DATA et ACK ;
- trames TP1 courtes et étendues jusqu'à 263 octets ;
- payload opaque conservé exactement ;
- magic, version, type, header, flags, TTL, longueur et CRC invalides ;
- FCS TP1 faux, troncature et octet excédentaire ;
- deux pairs UDP réels sur localhost, trafic bidirectionnel et ACK ;
- perte/absence de pair sans retransmission ;
- doublon acquitté une seconde fois mais livré une seule fois ;
- paquets désordonnés livrés une fois ;
- redémarrage simulé par changement de boot ID ;
- mauvaise identité et origine locale rejetables par le modèle ;
- boucle A→B→C→A arrêtée par la clé d'origine et le rejet de soi-même.

Les tests de non-régression KNX existants sont exécutés séparément avant la
livraison finale : codec étendu, parser NCN5130, séquence d'émission, tunneling,
routing, filtrage, anti-écho, cinq tunnels et simulateur TP1.

## Configuration Web

`/knx-intersite` permet de définir :

- site local et port UDP ;
- IPv4, port et site ID attendu du premier pair ;
- enregistrement sans activation ;
- activation et retour à l'état inactif explicites ;
- compteurs DATA, ACK, erreurs, doublons, mauvais pairs, files et confirmations.

Le modèle contient quatre emplacements de pair. L'interface du POC configure le
premier ; aucune adresse ou identité d'installation n'est codée en dur.

## Résultats de compilation et ressources

| Cible | Résultat | RAM statique | Flash linker | `firmware.bin` |
|---|---|---:|---:|---:|
| Olimex Ethernet physique | PASS | 100 856 / 327 680 | 1 155 569 / 6 291 456 | 1 162 144 octets |
| Olimex Wi-Fi simulé | PASS | 99 296 / 327 680 | 1 120 313 / 6 291 456 | 1 126 896 octets |
| Wemos D1 mini32 | PASS | 100 840 / 327 680 | 1 119 173 / 1 835 008 | 1 125 744 octets |

Par rapport à `d29a701`, l'augmentation statique est de 808 octets sur Olimex
Ethernet, 824 octets sur Olimex Wi-Fi simulé et 832 octets sur Wemos. La mémoire dynamique
additionnelle comprend deux files de huit trames TP1 et une pile de tâche de
4096 octets, soit environ 8,5 Kio au démarrage avec l'alignement FreeRTOS. Les
files appliquent `drop newest`; aucun stockage flash de télégrammes n'existe.

## Ce qui n'est pas validé

- aucun firmware n'a été déployé ;
- aucun paquet n'a atteint un bus KNX réel ;
- aucun N146/03 n'a été modifié ;
- aucun VPN WireGuard/OpenVPN réel n'a été traversé ;
- aucune concurrence entre plusieurs ESP physiques n'est revendiquée ;
- LTE est transporté de façon opaque mais aucun équipement Synco n'a été testé ;
- l'enveloppe n'est pas sûre sur Internet sans VPN/authentification externe.

## Plan de validation physique ultérieur

1. configurer deux sites et leurs IP VPN explicites, transport toujours inactif ;
2. vérifier pare-feu et UDP 3672 dans les deux sens ;
3. activer un seul sens et observer une trame TP sans commande applicative ;
4. vérifier ACK KXL3, mise en file distante et confirmation NCN5130 séparément ;
5. tester une commande réversible unique après exclusion des N146/03 parallèles ;
6. revenir à l'état inactif et vérifier files, heap et marges de pile ;
7. seulement ensuite répéter à travers le VPN L3.

## État final exigé

Le firmware installé reste 0.15.4. Le développement n'effectue aucune OTA,
n'ouvre aucun port réseau sur le matériel et ne touche pas à la NVS physique.
Le transport intersites réel demeure donc inactif, sans file ni service de test.
