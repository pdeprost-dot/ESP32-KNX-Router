# Validation OTA de la page KNX installateur sur Wemos

Date : 2026-10-25  
Cible : Wemos D1 Mini ESP32, Wi-Fi  
Branche : `feature/knx-intersite-l3`

## Compilation et déploiement

Le correctif applicatif provient du commit de développement `8726b90`.
ESP_BASE 2.4.2 est resté inchangé. Tous les tests `tools/test_*.py` ont réussi.

La cible `wemos_d1_mini32` compile avec 100 904 octets de RAM statique,
1 120 953 octets de flash linker et un `firmware.bin` réel de 1 127 536 octets.
L'OTA Wi-Fi a répondu HTTP 200, puis la carte a redémarré et retrouvé sa
connexion. Le numéro de version reste 0.15.5.

## Validation HTTP réelle

Avant correction, `/knx-config` s'arrêtait dans la valeur d'un emplacement de
tunnel vide. Après OTA :

- HTTP 200 et `Transfer-Encoding: chunked` ;
- 7 962 octets de HTML décodé ;
- cinq formulaires et neuf sections correctement fermés ;
- terminaison `</footer></body></html>\r\n0\r\n\r\n` ;
- aucune troncature.

La réponse et Chrome présentent les cinq emplacements ETS, les deux sens de
routage, la table commune, KXRF1, les paramètres avancés et les boutons de
sauvegarde/restauration. Le DOM reste complet en viewport mobile 390 × 844.
Aucun formulaire n'a été soumis.

## NVS et état final

Les adresses configurées et les emplacements vides ont été restitués à
l'identique. Les politiques et la table commune sont conservées. Le routage
automatique reste passif, ses files sont vides et aucune émission TP
applicative n'a été produite. KXL3 reste inactif avec socket fermé.

Le profil tunnel persistant était déjà actif avant l'OTA. Il a été restauré et
un client s'est reconnecté sans action manuelle. Le NCN5130 reste donc en mode
normal pour desservir ce tunnel ; il n'a pas été forcé en Busmon, ce qui aurait
modifié l'état persistant préexistant.

L'autre ESP et les interfaces KNX/IP tierces n'ont pas été modifiés.
