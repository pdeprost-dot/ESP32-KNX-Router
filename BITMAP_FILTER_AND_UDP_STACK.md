# Filtre bitmap et marge de pile UDP — 0.14.0

## Filtre

La table commune de routage couvre les 65 536 adresses de groupe avec un bit
par adresse : 8 192 octets. Elle remplace l'ancien modèle limité à 64 plages
sans modifier sa sémantique commune aux sens IP→TP et TP→IP.

La migration construit d'abord un candidat, vérifie son en-tête, sa longueur et
son CRC, l'enregistre sous une clé temporaire puis relit et valide cette copie
avant de remplacer la clé active. L'ancienne configuration n'est pas effacée
avant validation.

L'import KXRF1 reste textuel et borné à 12 288 octets. L'éditeur manipule les
plages sans produire les 65 536 entrées dans le HTML ou sur la pile.

## Pile UDP et loopTask

Les données volumineuses persistantes sont allouées statiquement. La lecture de
configuration utilise `memset` sur le candidat existant : elle ne crée pas une
copie temporaire de 8 Kio sur `loopTask`.

La marge minimale observée de la tâche UDP sous Web et tunneling est passée à
3 720 octets. Cette mesure valide une marge sur le banc utilisé, pas tous les
trafics possibles.

## Tests

Les tests indépendants couvrent table vide/pleine, bornes 0 et 65535, groupes
principaux 0, 15, 16 et 31, plus de 64 plages isolées, import/export sans perte,
rejet des entrées invalides et présence du correctif anti-copie temporaire.
