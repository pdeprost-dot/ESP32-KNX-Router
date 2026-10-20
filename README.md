# Prototype ESP32 KNX TP ↔ KNXnet/IP sur Wi-Fi

Prototype prudent pour Wemos D1 mini ESP32 classique et NanoBCU v1.1.1. Il utilise la pile
[`thelsing/knx`](https://github.com/thelsing/knx) au commit
`980c047ad7fc5e27bf2fae95e48acde5d5e0b4fd`, le masque coupleur KNX IP/TP `0x091A`,
le routage multicast KNXnet/IP et quatre tunnels compilés.

Ce prototype n'est pas déclaré équivalent au Siemens N146/02 tant que TP, routage dans les
deux sens et ETS n'ont pas été validés sur l'installation réelle.

## Câblage

| NanoBCU v1.1.1 | Wemos ESP32 | Fonction |
|---|---|---|
| RX | GPIO17 | émission ESP32 vers NanoBCU |
| TX | GPIO16 | réception ESP32 depuis NanoBCU |
| GND | GND | référence commune et KNX noir (-) |
| KNX | KNX rouge (+) | bus TP |
| SAV, 3V3, 3V3 | non raccordés | |

UART2 est réglé à 19200 bauds, 8E1, niveau 3,3 V. UART0 reste réservé au flash et aux logs USB.

## Construction

1. Installer PlatformIO.
2. Copier `include/secrets.h.example` vers `include/secrets.h` et renseigner le mot de passe
   du SSID `example-wifi`. Le fichier réel est ignoré par Git.
3. Compiler avec `pio run`.
4. Après détection certaine du port : `pio run -t upload --upload-port COMx`.
5. Lire les logs : `pio device monitor -p COMx -b 115200`.

La cible `wemos_d1_mini32` ne doit être utilisée qu'après confirmation que la puce est un ESP32
classique et que la flash correspond. Exécuter avant le premier flash :

```text
python -m esptool --port COMx chip_id
python -m esptool --port COMx flash_id
```

Sauvegarder le firmware existant avant remplacement si son utilité est inconnue (taille à adapter
au résultat de `flash_id`) :

```text
python -m esptool --port COMx read_flash 0x0 0x400000 backup/original-4MiB.bin
```

Restauration :

```text
python -m esptool --port COMx write_flash 0x0 backup/original-4MiB.bin
```

## Mise en service et ETS6

Le firmware rejoint `224.0.23.12:3671` seulement après connexion Wi-Fi. Une mémoire vierge reste
non configurée. Il faut attribuer dans ETS une adresse de coupleur cohérente avec la topologie
(adresse finissant par `.0` pour un coupleur de ligne, par exemple), puis charger les paramètres
et tables de filtre avec un produit compatible avec le masque `0x091A`. Aucun groupe n'est
émis par ce firmware de lui-même.

Avant de raccorder le TP, déconnecter du réseau IP **ou** du bus TP le Siemens qui dessert cette
même ligne, ou isoler le prototype sur un segment de test. Deux chemins IP/TP parallèles vers la
même ligne et le même multicast risquent de créer des doublons ou des boucles.

Les compteurs `IP(rx/tx)` et `TP(rx/tx)` sont affichés toutes les 30 secondes. Ils indiquent une
activité de couche liaison, pas à eux seuls la validation du routage. La pile décrémente le compteur
de routage (sauf valeur 7 selon KNX) et applique la topologie et la table de filtre.

## Limites connues

- Le NanoBCU/NCN5120 est documenté comme presque compatible TP-UART ; le dialogue réel reste à tester.
- La configuration ETS complète nécessite un fichier produit adapté ; elle n'est pas fournie par la
  bibliothèque générique seule.
- Après une perte Wi-Fi, l'ESP32 demande une reconnexion automatique. La reprise multicast et des
  sessions de tunnel doit être testée matériellement ; les clients devront rouvrir leurs sessions.
- KNX Secure, Ethernet et WireGuard ne font pas partie de ce prototype.
- Les compteurs sont volatils et remis à zéro au redémarrage.

Voir [TESTS.md](TESTS.md) pour l'état factuel des validations.

