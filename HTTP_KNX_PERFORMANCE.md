# Optimisation HTTP de `/knx` (firmware 0.8.2)

Date : 2026-10-21. ESP_BASE reste strictement inchange.

## Cause mesuree

`WebResponse::write()` appelle directement `WebServer::sendContent()`. La page
ecrivait chaque etiquette, valeur et octet hexadecimal separement. Sur une
page apres redemarrage, l'instrumentation compte 455 fragments applicatifs de
1 a 520 octets. Avec les 15 appels fixes du cadre ESP_BASE, cela aurait produit
470 appels `sendContent()` pour une seule reponse.

Avant optimisation, trois reponses de 24 942 octets ont pris respectivement
11 517, 11 232 et 11 581 ms. La construction de chaine n'etait pas la cause
dominante : l'attente se produisait dans les nombreuses ecritures reseau.

## Correction applicative

`KnxPageWriter` regroupe les fragments dans un tampon fixe de 1 024 octets sur
la pile. Il n'utilise ni `String` d'accumulation ni allocation dynamique. Le
tampon est vide avant `endPage()`. Le serveur, le protocole chunked et ESP_BASE
ne sont pas modifies.

Les instantanes UDP et NCN5130 sont copies sous leurs verrous respectifs avant
`beginPage()`. Les deux sections critiques ont dure 43 us au total, 26 us au
maximum pour une section. Aucun mutex applicatif n'est maintenu pendant la
construction HTML ou l'envoi HTTP.

## Resultats

| Mesure | Avant 0.8.0 | Apres 0.8.2 |
|---|---:|---:|
| Duree client, plusieurs chargements | 11 232 a 11 581 ms | 349 a 1 104 ms |
| Taille totale observee | 24 942 o, journaux remplis | 13 741 a 13 874 o, journaux apres redemarrage |
| Fragments applicatifs pour la page mesuree | 455 appels directs potentiels | 12 appels groupes |
| Appels totaux, cadre ESP_BASE compris | 470 potentiels | 27 |
| Taille des blocs applicatifs groupes | sans regroupement, 1 a 520 o | 451 a 1 023 o |
| Construction HTML | non separee | 8 358 us |
| Ecriture reseau | dominante, incluse dans 11,2-11,6 s | 266 391 us sur la page relevee |
| Mutex pendant l'envoi | non instrumente | 0 us |
| Heap libre apres charge | 174 460 o | 172 928 o |
| Minimum historique heap | 152 492 o | 148 040 o |
| Marge pile loop/Web | 3 036 o | 1 980 o |
| Marge pile tache NCN5130 | 4 696 o | 4 696 o |

Les tailles totales ne sont pas directement comparables car les journaux TP
de la mesure avant OTA etaient remplis et ceux de la mesure apres redemarrage
etaient vides. Le regroupement ne supprime aucun contenu et la taille du corps
est mesuree separement par le firmware. Le gain provient du nombre d'ecritures,
pas d'une suppression de fonctions ou de journaux.

## Reception concurrente

Six rafales UDP unicast numerotees de 20 paquets ont ete envoyees a 100, 10 et
2 ms, avec et sans chargement simultane de `/knx`. Chaque serie a donne 20/20
au socket et 20/20 au traitement applicatif. Les files UDP et NCN5130 sont
restees sans saturation, les erreurs UDP a zero, et la tache NCN5130 a garde
une marge de pile de 4 696 octets. Aucun trafic TP n'a ete genere pendant cette
fenetre post-OTA ; la reception TP reste passive et l'essai 0.8.0 precedent
avait deja valide 122 trames pendant les blocages Web.

Le binaire 0.8.2 utilise 65 176 octets de RAM statique et 1 033 345 octets du
slot OTA de 1 835 008 octets, soit 801 663 octets de marge.

La page reste volontairement complete. Une route distincte pour les journaux
pourrait encore reduire sa taille, mais elle n'est pas justifiee par les temps
mesures apres regroupement et n'a donc pas ete ajoutee.
