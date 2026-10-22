# Diagnostic et reprise Wi-Fi

## Fonctionnement vérifié

ESP_BASE 2.4.1 désactive l'auto-reconnexion du SDK et utilise sa propre machine d'état :

1. essai du réseau principal pendant 15 secondes ;
2. démarrage de l'AP de secours si l'essai échoue ;
3. nouvelle tentative toutes les 60 secondes ;
4. AP conservé pendant la tentative ;
5. arrêt de l'AP après obtention d'une adresse STA, sauf configuration « toujours actif ».

Les identifiants ne sont ni effacés ni réécrits par ces tentatives. Aucune reprise supplémentaire n'a été ajoutée dans l'application, car elle doublerait cette machine d'état et pourrait créer des courses. L'application 0.3.2 ajoute uniquement l'observation des événements ESP32 et leur affichage sur `/knx`.

## Résultats mesurés

| Événement | Mesure observée |
|---|---|
| Nouvelle tentative après fallback | environ 60,1 à 60,3 s après la déconnexion précédente |
| Fenêtre ESP_BASE | 15 s |
| Association réussie | 95 à 228 ms lors des reprises mesurées |
| DHCP réussi | 4 405 ms puis 6 418 ms après association |
| RSSI connecté | −89 dBm puis −81 dBm |
| BSSID canal 4 | `02:00:00:00:00:01` |
| BSSID canal 1 | `02:00:00:00:00:01` |

Motifs natifs relevés :

- 2 `AUTH_EXPIRE` : authentification expirée ;
- 15 `4WAY_HANDSHAKE_TIMEOUT` : échange de clés WPA non terminé ;
- 39 `TIMEOUT` : timeout bas niveau ;
- 8 `ASSOC_LEAVE` : déconnexion volontaire déclenchée par ESP_BASE à la fin de sa fenêtre, et non cause initiale.

Plusieurs associations ont réussi sans obtenir DHCP dans les 15 secondes. Le réseau présente au moins deux BSSID et deux canaux pour le même SSID. Un même BSSID a échoué puis réussi. Ces éléments ne permettent pas de conclure à un simple problème de portée sur la base de `WL_CONNECT_FAILED=4` ou `WL_DISCONNECTED=6`. Le RSSI faible lorsqu'une connexion existe peut contribuer, mais des échecs d'authentification et de DHCP sont également constatés.

## Validation de reprise

Une séquence complète a été observée sans réécriture des identifiants : échec initial, AP de secours, tentative automatique, association, DHCP, arrêt de l'AP de secours, retour de l'IP `192.0.2.156`, puis disponibilité des pages et de `/ota`.

Les pertes observées pendant les essais reproduisent une indisponibilité effective du réseau principal, mais le point d'accès n'a pas été physiquement coupé depuis ce PC. Pour qualifier strictement une coupure électrique de l'AP, couper le nœud concerné pendant que l'ESP32 est connecté, attendre l'apparition de l'AP `espbase-example-setup`, puis remettre le nœud sous tension et vérifier le retour STA dans les tentatives de 60 secondes.

## Vérifications au garage

- relever BSSID, canal, RSSI et motif sur `/knx` ou l'USB ;
- vérifier si DHCP arrive en moins de 15 secondes ;
- contrôler `/api/status`, `/knx`, `/knx-config` et `/ota` après reprise ;
- ne pas épingler un BSSID avant de connaître le nœud réellement reçu au garage ;
- garder l'AP de secours accessible pendant le diagnostic.

Le routage KNX reste totalement indépendant de ce diagnostic et `ROUTING_ARMED=0` demeure obligatoire.

## Essai multicast sans économie Wi-Fi — firmware 0.9.5

L'application relève désormais le mode effectif avec `esp_wifi_get_ps()` après
l'initialisation d'ESP_BASE. Au démarrage de l'essai, l'API a retourné
`WIFI_PS_MIN_MODEM` avec `ESP_OK`. L'application a alors appelé
`WiFi.setSleep(false)` puis relu `WIFI_PS_NONE`, également avec `ESP_OK`.
ESP_BASE et UniFi n'ont pas été modifiés. L'état avant/après et les codes de
retour sont visibles dans `/knx`.

Six rafales KXDG de 20 paquets ont été émises immédiatement, puis à nouveau
après trente minutes sans redémarrage ni réinscription multicast forcée. Les
captures PC contiennent chacune les 120 paquets KXDG émis.

| Série | Intervalle | `/knx` | Immédiat | Après 30 min |
|---:|---:|:---:|---:|---:|
| 1 | 100 ms | non | 18/20 | 17/20 |
| 2 | 10 ms | non | 19/20 | 16/20 |
| 3 | 2 ms | non | 19/20 | 16/20 |
| 4 | 100 ms | oui | 19/20 | 18/20 |
| 5 | 10 ms | oui | 13/20 | 15/20 |
| 6 | 2 ms | oui | 11/20 | 14/20 |

Dans les deux campagnes, le bitmap reçu par le socket est identique au bitmap
traité par l'application. La file UDP est restée à zéro perte, sans erreur de
lecture ni datagramme surdimensionné. Après trente minutes, l'ESP32 était
toujours sur la même association logique (1 association, 1 DHCP, 0
déconnexion), avec une seule adhésion multicast réussie et `WIFI_PS_NONE`
toujours effectif.

La suppression de l'économie Wi-Fi est corrélée à une nette amélioration par
rapport aux anciennes séries, mais n'élimine pas les pertes. Le RSSI de cette
campagne était faible, environ -80 à -85 dBm, et les paquets absents n'ont
jamais atteint le socket ESP32. Ce test ne permet donc pas d'attribuer les
pertes restantes à l'application ni de distinguer à lui seul le trajet radio,
le point d'accès et la distribution multicast du réseau.

Captures :

- `udp_multicast_bursts_wifi_ps_none_immediate_095.pcapng` ;
- `udp_multicast_bursts_wifi_ps_none_after30m_095.pcapng`.

Le prototype est resté en Busmon passif, tunnels désactivés et
`ROUTING_ARMED=0` pendant toute la mesure.

## Nouvelle position plus proche de l'AP

Une campagne strictement identique a été répétée après déplacement de l'ESP32
plus près de l'AP, sans modifier UniFi ni réinscrire le socket multicast. Le
BSSID est resté `02:00:00:00:00:01`, canal 4. Le RSSI mesuré était -78 dBm avant
les rafales et -80 dBm après. `esp_wifi_get_ps()` confirmait toujours
`WIFI_PS_NONE` avec `ESP_OK`.

| Série | Intervalle | `/knx` | Immédiat `eb2432d` | Après 30 min `eb2432d` | Plus proche AP |
|---:|---:|:---:|---:|---:|---:|
| 1 | 100 ms | non | 18/20 | 17/20 | 17/20 |
| 2 | 10 ms | non | 19/20 | 16/20 | 8/20 |
| 3 | 2 ms | non | 19/20 | 16/20 | 10/20 |
| 4 | 100 ms | oui | 19/20 | 18/20 | 14/20 |
| 5 | 10 ms | oui | 13/20 | 15/20 | 14/20 |
| 6 | 2 ms | oui | 11/20 | 14/20 | 8/20 |

La capture `udp_multicast_bursts_closer_ap_095.pcapng` contient les 120/120
paquets KXDG émis par le PC. Côté ESP32, le bitmap reçu par le socket est
identique au bitmap consommé par l'application pour chaque série. Aucune perte
de file, erreur de lecture, réinscription, déconnexion ou saturation n'a été
observée ; l'intervalle maximal de la tâche UDP était 9221 µs.

Cette position n'a donc pas amélioré la réception multicast. Le gain radio
observé est faible et variable, et les résultats à 10 et 2 ms sont même moins
bons que dans les deux campagnes de `eb2432d`. La distance seule n'explique pas
les pertes ; elles restent situées avant le socket ESP32 et peuvent dépendre du
trajet Wi-Fi vers Wi-Fi ou de la distribution multicast du réseau. Aucun
réglage UniFi n'a été modifié pour cet essai.
