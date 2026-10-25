# Validation OTA de la page KNX installateur

Date : 2026-10-25  
Cible : Olimex ESP32-POE-ISO-16MB, Ethernet/PoE  
Branche : `feature/knx-intersite-l3`

## Correctif et compilation

Le correctif applicatif validé provient du commit de développement `8726b90`.
ESP_BASE 2.4.2 est resté inchangé. La cible `olimex_poe_iso_16mb` compile sans
nouvelle erreur : 100 944 octets de RAM statique, 1 156 997 octets de flash
linker et un `firmware.bin` réel de 1 163 568 octets.

## OTA et validation HTTP réelle

L'OTA Ethernet a répondu HTTP 200, puis la carte a redémarré et retrouvé son
adresse DHCP. Le firmware démarré reste numéroté 0.15.5 : le correctif ne
change pas la version applicative.

Avant correction, la réponse réelle s'arrêtait dans la valeur du premier
emplacement de tunnel vide. Après OTA, `GET /knx-config` renvoie :

- HTTP 200 et `Transfer-Encoding: chunked` ;
- 7 922 octets de HTML décodé ;
- les balises finales `</footer></body></html>` ;
- le terminateur chunked `0\r\n\r\n` ;
- cinq formulaires et neuf sections correctement fermés.

La réponse et le rendu Chrome contiennent les cinq emplacements ETS, les deux
sens de routage, la table commune, l'import KXRF1, les paramètres avancés et
les boutons d'enregistrement et de restauration. Le DOM reste complet avec un
viewport mobile de 390 × 844. Aucun formulaire n'a été soumis.

## Non-régression et état final

- paramètres NVS observables conservés, y compris les emplacements vides ;
- Web, interface KNX, interface KXL3 et OTA accessibles ;
- KXL3 inactif, socket fermé ;
- routage TP1 passif et files vides ;
- NCN5130 opérationnel en réception passive, réponses Reset/State valides ;
- aucune émission TP1 applicative pendant la validation ;
- serveur de tunneling laissé dans son état antérieur désactivé.

La Wemos et les interfaces KNX/IP tierces n'ont pas été modifiées.
