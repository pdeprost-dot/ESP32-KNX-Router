# Procédure ETS6 (prototype)

1. Pour le diagnostic passif avec `ROUTING_ARMED=0`, le Siemens peut rester actif. Avant d'armer le
   routage, isoler la ligne de test : ne pas laisser le Siemens et ce prototype former deux chemins parallèles.
2. Définir dans ETS la topologie réelle et choisir une adresse individuelle libre de coupleur.
3. Importer/associer un produit routeur compatible `0x091A` et la version de pile employée.
4. Mettre le prototype en mode programmation par la méthode prévue lors de l'essai (le firmware
   n'affecte actuellement aucun bouton afin d'éviter GPIO0, broche de boot).
5. Télécharger d'abord l'adresse individuelle, puis l'application/les paramètres et tables de filtre.
6. Dans les interfaces ETS, rechercher le serveur KNXnet/IP sur le réseau local ; vérifier découverte,
   description et ouverture d'un tunnel.
7. Sur une adresse de groupe de test explicitement autorisée, observer un télégramme TP→IP puis IP→TP.
8. Vérifier les adresses source, le compteur de routage et l'absence de répétition/boucle.

L'étape 4 demande soit l'ajout d'un bouton dédié sur un GPIO libre, soit une procédure temporaire
convenue au banc. Ne pas utiliser GPIO0 sans tenir compte de son rôle au démarrage.

