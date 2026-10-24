# Validation du transport des trames KNX TP1 étendues

Date : 24 octobre 2026
Branche : `feature/knx-extended-frames`
Base : firmware 0.15.4, commit `c51e22f`
ESP_BASE : 2.4.2, inchangé

## Portée

Cette évolution supprime les limites applicatives de 32, 64 et 128 octets qui
empêchaient le transport transparent des trames longues. Elle ne met en œuvre
ni décodage Siemens Synco LTE, ni filtrage LTE, ni routage intersites L3.

Les données applicatives sont transportées comme une suite d'octets opaque. Les
tests synthétiques prouvent la conservation des octets ; ils ne constituent pas
une validation d'un équipement Siemens Synco.

## Limites protocolaires retenues

| Objet | Limite | Justification |
|---|---:|---|
| TP1 standard | 23 octets sur le fil | 7 octets hors APDU, APDU de 1 à 16 octets |
| TP1 étendue | 263 octets sur le fil | `9 + LG`, avec `LG` limité à 254 par le NCN5130 |
| APDU | 255 octets | champ `LG` 0..254 représentant APDU-1 |
| cEMI | 264 octets | code + longueur d'information additionnelle + TP étendue sans FCS |
| ROUTING_INDICATION | 270 octets | en-tête KNXnet/IP de 6 octets + cEMI |
| TUNNELING_REQUEST | 274 octets | en-tête/service tunneling de 10 octets + cEMI |
| Datagramme applicatif | 512 octets | limite existante, supérieure aux maxima KNX ci-dessus |

Le parseur refuse une longueur supérieure, tronquée ou incohérente et vérifie
le FCS TP avant conversion. Aucune troncature silencieuse n'est admise.

## Changements réalisés

- ajout d'un codec borné dans `include/knx_frame_codec.h` ;
- conversion TP1/cEMI sans copie par le constructeur de copie de
  `thelsing/knx` ;
- files IP→TP, tunnels→TP, confirmations et indications tunnel portées aux
  maxima documentés ;
- longueurs internes passées à 16 bits lorsque 255 octets ne suffisent plus ;
- émission UART portée à 263 octets ;
- émission de `U_L_DataOffset.req` aux index 64, 128, 192 et 256, soit les
  commandes `09`, `0A`, `0B`, `0C` ;
- `U_L_DataStart`/`U_L_DataCont`/`U_L_DataEnd` continuent d'utiliser l'index
  local sur 6 bits ; pour une trame de 263 octets, le dernier service est
  `46`, correspondant à l'index absolu 262 ;
- le chemin des trames courtes conserve le même séquencement, sans commande
  d'offset ;
- l'envoi tunnel alloue un seul instantané cEMI maximal sur la pile à la fois,
  et non cinq instantanés simultanés ;
- validation cEMI explicite avant le décodeur de routing.

### Bibliothèque thelsing/knx

Le tampon privé du constructeur de copie `CemiFrame` a une capacité de 263
octets dans la révision épinglée `980c047`. Une cEMI maximale en exige 264.
L'application n'utilise donc plus ce constructeur sur les chemins étendus : le
codec écrit dans un tampon applicatif de 264 octets, puis `CemiFrame` ne fournit
qu'une vue externe sur ce tampon. La dépendance épinglée n'a pas été modifiée et
ESP_BASE reste inchangé. Toute réintroduction d'une copie `CemiFrame` sur ce
chemin serait une régression à rechercher en revue de code.

## Tests hors ligne

`python tools/test_extended_frames.py` couvre, avec une référence indépendante
du code C++ :

- trames standard avec APDU de 1, 2, 15 et 16 octets ;
- longueurs étendues 9, 31, 32, 33, 63, 64, 65, 127, 128, 129, 191, 192, 193
  et 263 octets ;
- aller-retour TP1 ↔ cEMI sans perte ;
- FCS faux, trame tronquée, longueur déclarée incohérente et dépassement du
  tampon maximal ;
- commandes d'offset et `U_L_DataEnd` au maximum ;
- conservation opaque d'octets pouvant ressembler à des services TPUART
  (`CC`, `CB`, `09` à `0C`, `80`, `40`).

Résultat : `PASS`.

Les tests de non-régression suivants passent également :

- `test_ncn5130_rx_parser.py` ;
- `test_ncn5130_send_sequence.py` ;
- `test_knx_tunnel_protocol.py` ;
- `test_tunnel_tx_flow.py` ;
- `test_bidirectional_router.py` ;
- `test_routing_policy.py` ;
- `test_five_tunnel_sessions.py` ;
- `test_tp1_simulator.py`.

Ils couvrent notamment les confirmations, timeouts, ACK, doublons, expiration,
filtrage, anti-écho et arbitrage. Les anciennes trames courtes restent couvertes.

## Compilations

| Cible | Résultat | RAM statique | Flash linker | `firmware.bin` |
|---|---|---:|---:|---:|
| Olimex Ethernet physique | PASS | 100 048 / 327 680 | 1 145 377 / 6 291 456 | 1 151 952 octets |
| Olimex Wi-Fi simulé | PASS | 98 472 / 327 680 | 1 110 061 / 6 291 456 | 1 116 640 octets |
| Wemos D1 mini32 | PASS | 100 008 / 327 680 | 1 109 473 / 1 835 008 | 1 116 048 octets |

Le coût RAM vient principalement des files bornées de cinq tunnels et des files
NCN5130, désormais dimensionnées pour le pire cas. La pile de la tâche UDP ne
porte qu'un instantané maximal à la fois. Les marges de pile et le heap en charge
réelle restent à mesurer après déploiement.

## Validation matérielle et état final

Aucune OTA n'a été lancée pendant cette étape : les tests hors ligne réussissent,
mais le déploiement aurait interrompu l'interface en production et n'est pas
nécessaire pour établir le résultat logiciel. Aucune trame étendue synthétique
n'a été injectée sur TP1 et les N146/03 n'ont pas été modifiés.

Restent à valider sur matériel, dans une fenêtre contrôlée :

1. réception d'une vraie trame TP1 étendue et remontée en tunneling/routing ;
2. émission étendue provenant d'un client légitime, confirmation NCN5130 et
   observation indépendante sur le bus ;
3. heap, marges de pile et files au maximum de longueur et sous concurrence ;
4. transport réel de télégrammes Siemens Synco LTE, sans prétendre en décoder la
   sémantique.

Le firmware installé n'a pas été changé. Il demeure donc dans son état de
production antérieur ; aucune session, file ou activation de routage n'a été
créée par cette validation hors ligne.
