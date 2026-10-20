# Mise à jour OTA et récupération USB

## Partitionnement retenu

La table versionnée [partitions_ota_1792.csv](partitions_ota_1792.csv) conserve NVS 20 Kio, métadonnées OTA 8 Kio et coredump 64 Kio. Elle fournit deux slots de 1 792 Kio et un SPIFFS de 384 Kio. Le firmware 0.3.1 de 1 003 824 octets laisse 831 184 octets par slot.

ESP_BASE 2.4.1 et l'application n'utilisent pas SPIFFS. Les configurations ESP_BASE et KNX sont dans la partition NVS. La réduction est donc adaptée à ce firmware.

## Sauvegardes avant migration

Les fichiers sont dans `backup/`, ignoré par Git :

| Sauvegarde | Taille | SHA-256 |
|---|---:|---|
| `pre-partition-migration-2026-10-20-4MiB.bin` | 4 194 304 o | `154E84F5FB524AF92340A0EA4E7DD544B1296C743A521F79F406EAD9EF4E704E` |
| `pre-partition-nvs-2026-10-20.bin` | 20 480 o | `91758599949C4056D62E84B9388879A5AB578A7918065C34D6991D37842918B7` |
| `pre-partition-otadata-2026-10-20.bin` | 8 192 o | `F94C5D786A7A8FAB06AC5D10E33BF37711A6697636DC037559EA19CC410A17F0` |
| `pre-partition-spiffs-2026-10-20.bin` | 1 441 792 o | `3CF4E5A0597DD20F5A6F7B56607F7BA795DE600E159F06A7189F7A990F376B46` |

La migration USB a nécessité la restauration ciblée du NVS et une nouvelle application des identifiants Wi-Fi via la commande série officielle ESP_BASE. Les paramètres KNX ont ensuite été vérifiés.

## Web OTA depuis ce PC

Compiler d'abord avec la table versionnée :

```powershell
pio run
```

Vérifier que l'ESP32 est joignable et que le binaire tient dans 1 835 008 octets, puis utiliser la page `http://192.0.2.156/ota` ou :

```powershell
curl.exe --noproxy "*" --fail-with-body --max-time 120 `
  -F "firmware=@.pio/build/wemos_d1_mini32/firmware.bin;type=application/octet-stream" `
  http://192.0.2.156/api/ota
```

Après le redémarrage, vérifier `/api/status`, `/knx`, `/knx-config` et `/ota`, la version, le Wi-Fi et les paramètres persistants. Le test réel 0.3.0 → 0.3.1 a réussi. ESP_BASE propose aussi ArduinoOTA sur le LAN STA.

Lors de ce test, la reconnexion juste après OTA a réussi sur `192.0.2.156` et les pages ont été vérifiées. Des redémarrages USB de contrôle ultérieurs ont en revanche fini en AP de secours, avec des échecs d'association STA 4/6 malgré la configuration présente. À l'installation, vérifier la portée de `example-wifi`; l'AP de secours reste accessible sur `192.168.4.1` si l'association échoue.

Les deux OTA sont sans mot de passe dans ESP_BASE 2.4.1. Elles doivent rester sur un LAN de confiance. Le Web OTA utilise `Update.begin(UPDATE_SIZE_UNKNOWN)`, écrit l'image dans le slot inactif, finalise avec `Update.end(true)`, puis redémarre environ 1,2 seconde après la réponse HTTP.

## Pas de rollback automatique garanti

ESP_BASE 2.4.1 ne marque pas explicitement une nouvelle image comme valide après son démarrage et ne contient aucun mécanisme applicatif de retour à l'image précédente. Il ne faut donc pas supposer qu'un firmware défectueux reviendra automatiquement au slot antérieur. Conserver l'accès USB et un binaire connu fonctionnel.

## Récupération USB

Pour réinstaller la version courante et sa table sans effacer volontairement NVS :

```powershell
pio run --target upload --upload-port COM3
```

Si les paramètres sont perdus, restaurer uniquement la sauvegarde NVS compatible :

```powershell
python -m esptool --chip esp32 --port COM3 write_flash 0x9000 `
  backup/pre-partition-nvs-2026-10-20.bin
```

Puis, si nécessaire, réappliquer le Wi-Fi avec la commande série ESP_BASE. Pour revenir exactement à l'état complet antérieur à la migration, y compris l'ancienne table :

```powershell
python -m esptool --chip esp32 --port COM3 write_flash 0x0 `
  backup/pre-partition-migration-2026-10-20-4MiB.bin
```

Une restauration complète écrase toute la flash actuelle. Vérifier le port, la taille 4 Mio et l'empreinte avant de l'exécuter. `ROUTING_ARMED=0` reste imposé dans toutes les versions décrites ici.
