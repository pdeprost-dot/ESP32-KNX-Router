# Bilan des essais

Date : 2026-10-20 (Europe/Paris)

| Étape | État | Preuve / résultat |
|---|---|---|
| USB / port série | Réussi | COM3, WCH CH9102, `VID:PID 1A86:55D4`, pilote `oem4.inf` |
| Puce / flash | Réussi | ESP32-D0WD-V3 rev. 3.1, 240 MHz, flash 4 Mio |
| Sauvegarde initiale | Réussi | image 4 Mio, SHA-256 `5274C13C496F0FC7A2E037276C009B5F400348DAA9DD16F94EDA95E62200CCF5` |
| Compilation finale | Réussie | PlatformIO `espressif32@6.12.0`, RAM 55232 octets (16,9 %), flash 995477 octets (75,9 %) |
| Flash final | Réussi | COM3, écriture et vérification par esptool |
| Démarrage / Wi-Fi | Validé | SSID configuré, IP `192.0.2.156`, RSSI observé -82 dBm après redémarrage |
| Pages ESP_BASE | Validées | `/`, `/wifi`, `/logs`, `/ota`, `/system`, `/api/status` en HTTP 200 |
| Pages KNX | Validées | `/knx` et `/knx-config` complètes et adaptatives, HTTP 200 |
| Enregistrement | Validé | `POST /knx-config-save` HTTP 200 ; valeurs relues après redémarrage |
| Validation serveur | Validée | `16.0.1` rejetée HTTP 400 ; route d'écriture en GET rejetée HTTP 404 |
| Diagnostic Web | Validé sans NanoBCU | lancement HTTP 202, expiration bornée, état « NanoBCU non détecté » |
| Verrou routage | Validé | `ROUTING_ARMED=0`, `static_assert`, aucun `knx.start()`/`knx.loop()`, routage et tunnels affichés inactifs |
| Dialogue NCN5130 | Non testé | NanoBCU volontairement non raccordé ; absence de réponse normale |
| Réception TP | Non validée | nécessite le raccordement décrit dans le README |
| Routage / tunnels ETS6 | Non validés | volontairement impossibles dans cette version |

## Persistance vérifiée

Les valeurs testées (`224.0.23.12`, port `3671`, délai `16000 ms`, sonde `3000 ms`, adresse physique vide) ont été enregistrées, l'ESP32 redémarré via COM3, puis le formulaire les a restituées. ESP_BASE a retrouvé le Wi-Fi et désactivé son AP de secours.

## Diagnostic attendu sans NanoBCU

Au démarrage ou après `POST /knx-diagnostic`, le firmware sonde le NCN5130 pendant le délai configuré sans bloquer la boucle. À l'expiration, il journalise une seule fois l'absence et cesse les émissions UART. Ce résultat n'est pas un défaut tant que le NanoBCU n'est pas raccordé.

Le prochain essai est limité au dialogue local NCN5130 puis à la réception TP passive. Le Siemens N146/02 peut rester actif. Aucun essai effectué sans NanoBCU ne justifie de remplacer la pile KNX.

## Stabilité mémoire 0.2.1

Après stabilisation Wi-Fi, 40 consultations de pages et trois diagnostics NCN5130 complets sans module, le heap libre s'est stabilisé à `223408` octets et le plus grand bloc à `110580` octets. Le minimum historique natif a atteint `183980` octets pendant les réponses Web, sans baisse du niveau stable. Aucun déclin durable n'a été observé. Le détail et les réserves proposées figurent dans [RESOURCE_AUDIT.md](RESOURCE_AUDIT.md).
