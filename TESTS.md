# Bilan des essais

Date : 2026-10-20 (Europe/Paris)

| Étape | État | Preuve / blocage |
|---|---|---|
| Détection USB | Bloquée | aucun périphérique de classe Ports et aucun pont USB-série connecté visible |
| Identification puce/flash | Non réalisée | aucun port COM détecté |
| Compilation | Réussie | PlatformIO 6.1.18, `espressif32@6.12.0`, `wemos_d1_mini32`; 461625 octets flash, 31080 octets RAM |
| Sauvegarde firmware existant | Non réalisée | exige un port et la taille flash |
| Flash USB | Non réalisé | aucun port COM détecté |
| Démarrage firmware | Non validé | exige flash et logs série |
| Connexion Wi-Fi | Non validée | secret local absent et matériel non accessible |
| Dialogue NanoBCU | Non validé | NanoBCU non confirmé raccordé |
| Réception TP | Non validée | essai matériel requis |
| Routage bidirectionnel | Non validé | topologie/adresse/groupe de test requis |
| Découverte/tunneling ETS6 | Non validé | configuration ETS et réseau réels requise |
| Reconnexion Wi-Fi | Non validée | essai matériel requis |

