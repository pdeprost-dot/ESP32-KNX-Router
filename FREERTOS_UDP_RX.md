# Reception UDP FreeRTOS et blocage Web — 21 octobre 2026

## Architecture 0.7.0

Une tache FreeRTOS `knxUdpRx`, epinglee sur le coeur 0, est l'unique
proprietaire de `WiFiUDP`. Elle realise l'ouverture, l'adhesion multicast, la
lecture et la fermeture du socket. La boucle Arduino et les gestionnaires Web
n'appellent plus aucune methode du socket.

Chaque datagramme valide au niveau UDP est copie dans une file FreeRTOS bornee
a 32 evenements de 512 octets maximum. La boucle applicative consomme cette
file et effectue ensuite la validation KNXnet/IP et le decodage. Les compteurs
de la tache et les bitmaps KXDG sont copies sous une section critique courte ;
la page Web ne consulte que ces instantanes.

Les commandes Web d'arret et de reprise ne manipulent qu'un etat demande. La
tache applique elle-meme le changement au socket. Tous les appels d'horloge ont
ete sortis de la section critique inter-coeurs apres qu'une premiere version a
gele le coeur reseau. La version corrigee est restee joignable pendant les
rafales, 25 consultations `/knx` supplementaires et le controle de stabilite.

Cette version reste strictement passive. `ROUTING_ARMED=0` est verifie a la
compilation et l'endpoint Web d'activation refuse explicitement la demande.
TP vers IP et les tunnels restent inactifs.

## Rafales KXDG

La capture PC `udp_multicast_bursts_freertos_fixed_0.7.0.pcapng` contient les
120 datagrammes emis, sequences 0 a 19 pour chaque serie.

| Serie | Cadence | `/knx` concurrent | PC | Socket ESP32 | Traites | File pleine |
|---:|---:|:---:|---:|---:|---:|---:|
| 1 | 100 ms | non | 20/20 | 11/20 | 11/20 | 0 |
| 2 | 10 ms | non | 20/20 | 6/20 | 6/20 | 0 |
| 3 | 2 ms | non | 20/20 | 12/20 | 12/20 | 0 |
| 4 | 100 ms | oui | 20/20 | 15/20 | 15/20 | 0 |
| 5 | 10 ms | oui | 20/20 | 13/20 | 13/20 | 0 |
| 6 | 2 ms | oui | 20/20 | 5/20 | 5/20 | 0 |

Les bitmaps recus par la tache et traites par l'application sont identiques
dans les six series. Il n'y a eu ni erreur de lecture, ni datagramme
surdimensionne, ni file pleine. L'intervalle maximal de la tache RX est reste
a 15,833 ms pendant les rafales, alors que la consommation applicative etait
suspendue jusqu'a 6,916 s par le Web. Lors de 25 consultations prolongees, la
tache est restee desservie avec un maximum de 22,864 ms et une file toujours
sans perte.

Les pertes residuelles surviennent donc avant la file applicative et ne sont
pas provoquees par `/knx`. Elles restent compatibles avec le trajet multicast
Wi-Fi/AP deja suspecte. Le test suivant est la meme emission depuis le PC
relie en Ethernet ; aucune modification UniFi ou OpenVPN n'a ete effectuee.

## Localisation du blocage HTTP

`ESP_BASE.loop()` appelle le `WebServer::handleClient()` synchrone. Pour les
pages applicatives, chaque `WebResponse::write()` appelle immediatement
`WebServer::sendContent()` : le HTML n'est pas construit dans un tampon puis
envoye separement.

Pendant les rafales, une page de 6,911 s se repartit ainsi :

- debut de page : au plus 203,240 us ;
- corps et appels `sendContent()` : 6,672,209 us ;
- fin de page : 40,354 us.

Pendant le test UART prolonge, une page a atteint 16,836 s, dont 16,609 s dans
le corps. La cause mesuree est donc le chemin synchrone d'ecriture des nombreux
fragments HTML et l'attente TCP/client associee, pas un calcul CPU long avant
l'envoi. ESP_BASE n'a pas ete modifie.

## Effet sur la reception TP

Pendant la fenetre de 25 consultations `/knx`, les actionnements KNX ont porte
le total a 267 octets UART et 20 entrees TP. Le pilote n'a signale aucune
erreur de parite, trame ou debordement. Cependant, le service UART de la boucle
principale n'a pas pu appliquer le delai inter-trame pendant le blocage Web :
plusieurs telegrammes ont ete concatenees en blocs invalides de 30 et 51
octets. Il s'agit d'une perte de delimitation applicative, meme sans perte
d'octets signalee par le materiel.

Les 78 pertes du journal UART et les quatre pertes du journal TP signifient
que les anneaux bornes ont remplace leurs entrees les plus anciennes. Elles ne
constituent pas, a elles seules, des erreurs du pilote UART.

Avant d'activer un routage bidirectionnel, la lecture UART et la delimitation
TP devront donc etre decouplees du serveur Web, avec un proprietaire unique et
une file bornee, selon le meme principe que la reception UDP.

## Ressources

| Ressource | Valeur |
|---|---:|
| RAM statique compilee | 65 144 / 327 680 octets |
| Firmware | 1 033 845 / 1 835 008 octets |
| Marge du slot OTA | 801 163 octets |
| File UDP | 32 x 524 octets, plus controle FreeRTOS |
| Pile reservee tache UDP | 6 144 octets |
| Heap juste apres redemarrage | 188 628 octets |
| Heap apres essais prolonges | 186 904 octets |
| Minimum historique apres pages | 160 280 octets |

La baisse par rapport a 0.6.1 correspond principalement a la file et a la
pile de la nouvelle tache. Apres echauffement, la heap remonte autour de 186 a
187 kio et ne montre pas de baisse monotone sur la periode mesuree.
