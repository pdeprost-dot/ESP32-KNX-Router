# Bilan des essais

Date : 2026-10-20 (Europe/Paris)

| Étape | État | Preuve / blocage |
|---|---|---|
| Détection USB | Réussie | COM3, WCH CH9102, VID:PID `1A86:55D4`, pilote `oem4.inf` actif |
| Identification puce/flash | Réussie | ESP32-D0WD-V3 rev. 3.1, double cœur 240 MHz, flash 4 Mo à 3,3 V |
| Compilation | Réussie | PlatformIO, `espressif32@6.12.0`, `wemos_d1_mini32`; 829645 octets flash, 46656 octets RAM |
| Sauvegarde firmware existant | Réussie | `backup/original-esp32-2026-10-20-4MiB.bin`, 4194304 octets, SHA-256 `5274C13C496F0FC7A2E037276C009B5F400348DAA9DD16F94EDA95E62200CCF5` |
| Flash USB | Réussi | COM3, écriture et vérification esptool réussies, sans effacement global |
| Démarrage firmware | Validé | logs série 115200 bauds reçus, verrou `ROUTING_ARMED=0` confirmé |
| Connexion Wi-Fi | Validée | SSID `example-wifi`, IP `192.0.2.156`, RSSI observé -80 dBm |
| Dialogue NanoBCU | Non validé | aucune réponse `U_Reset.ind`/`U_State.ind` après plusieurs requêtes; vérifier alimentation, masse et croisement RX/TX |
| Réception TP | Non validée | essai matériel requis |
| Routage bidirectionnel | Non validé | topologie/adresse/groupe de test requis |
| Découverte/tunneling ETS6 | Non validé | configuration ETS et réseau réels requise |
| Reconnexion Wi-Fi | Non validée | essai matériel requis |

