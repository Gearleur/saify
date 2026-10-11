# Ce que la relecture a trouvé et changé

Les tests vérifient ce qu'on a pensé à écrire ; la relecture sert à trouver ce qu'on n'avait pas pensé à tester. Deux temps : les revues pendant la construction, puis une revue de code finale, ligne à ligne, avant livraison. Le détail de chaque décision est dans [`NOTES.md`](../NOTES.md).

## Pendant la construction

Ce projet a été construit avec Claude Code, étape par étape. Chaque étape passait par une revue humaine qui **challengeait les choix**, et pas seulement le résultat. Tout ce qui suit est réellement arrivé pendant la construction : l'historique git et [`NOTES.md`](../NOTES.md) en gardent la trace.

**Ce que la première version, « qui marchait », contenait :**

| Sans relecture | Conséquence pour le client | Ce qu'a apporté la relecture |
|---|---|---|
| Les lignes à moitié vides d'un relevé étaient **ignorées sans trace** | des **faux négatifs invisibles**, le pire cas (pénalités CSDR) | BLOQUANT `LIGNE_INCOMPLETE` : une donnée n'apparaît ni ne disparaît sans trace |
| `"10.000"` était lu **10**, sans alerte | un faux écart, ou un vrai écart mal chiffré | contrôle sur le **texte brut**. Le test a montré que ma première idée (« quantité non entière ») ne protégeait rien, puisque `Decimal("10.000")` est entier |
| Une piste « op. n°19 » affichée à côté de **n'importe quel** écart | l'opérateur classe un suspens que l'opération n'explique pas | calcul signé : entièrement, partiellement ou pas du tout expliqué |
| La priorité déduite en **cherchant des mots** dans les messages | reformuler un message déclasse un critique en silence | champs structurés (`explication`, `alertes`) |
| La date d'arrêté **codée en dur** (25/09) | inutilisable le lendemain matin | date lue dans les fichiers ; le scénario du 26/09 fait apparaître le CSDR |
| `orsay.db` utilisée comme **clé** du rapprochement | contraire à l'énoncé ; base absente = plus de contrôle | base facultative, clé fonds tirée du paramétrage |
| Une seule anomalie de paramétrage faisait **planter** l'outil, ou « le dernier fonds lu gagnait » | un résultat faux sans erreur | BLOQUANT `PARAMETRAGE` avec le remède |
| Le LLM sans date de référence ; un « supprime la position » répondu par « pas compris » | une réponse sur le mauvais horizon ; un refus incompréhensible | trouvé par un **essai réel**, corrigé et verrouillé par des tests |

**Ce que la base de code aurait été :**
- **Une API en un fichier de 650 lignes** qui mêlait configuration, sécurité, schémas et routes. Elle a été découpée en couches (`domaine` / `api` / `web`), sans changer un seul comportement : les 95 tests de l'époque étaient le filet.
- **Un front HTML de 1 700 lignes dans un seul fichier**, à la finition « générée » : des pastilles colorées partout, si bien que la couleur ne signalait plus rien. Il a été refait en React avec shadcn, en composants de moins de 150 lignes, dans le style d'Attio : la couleur n'apparaît que là où elle porte une information.
- **Un dépôt encombré** : un `test.py` « Hello world », des CSV générés commités, des dépendances jamais utilisées (LangGraph, pdfplumber, rapidfuzz…), un paquet nommé `reco` alors qu'il portait aussi le besoin 2.
- **Des étapes enchaînées sans validation.** L'agent avait déjà commité l'étape 2 et commencé la 3 quand il a été arrêté : « on fait étape par étape, je veux comprendre pourquoi on implémente ça ». Chaque étape s'est ensuite terminée par une revue avec des questions précises.

Sans ces recadrages, l'outil aurait passé ses propres tests et donné les 7 bons suspens sur les données du 25/09. Mais il aurait été **fragile précisément là où le client a peur** : des écarts perdus en silence, des chiffres mal lus, des priorités qui se dérèglent au moindre changement de texte. Le code aurait aussi été difficile à reprendre. Les tests vérifient ce qu'on a pensé à écrire ; la relecture sert à trouver ce qu'on n'avait pas pensé à tester.


## Revue de code finale

Chaque défaut a été **reproduit par un script avant d'être corrigé** (un test qui échoue, puis la correction), un commit par point.

| Trouvé | Pourquoi c'était grave | Correction |
|---|---|---|
| Un lot répété chez C, ou un item `ACTION=X`, portait C au niveau du PMS : **le suspens SFIL disparaissait** (le lot n'était même pas lu) | faux négatif invisible, le pire cas | doublon et action inconnue `BLOQUANT`, pour toutes les sources ([ADR 0003](adr/0003-un-doute-qui-peut-masquer-un-ecart-bloque.md)) |
| Après un rapprochement bloqué, « d'où vient le suspens sur X ? » répondait **« aucun suspens »** | une fausse assurance, qui finit chez le RCCI | réponse sur le dernier rapprochement exploitable, blocage plus récent signalé |
| « Encours de LVMH » → encours des 3 fonds ; « au 01/01/2025 » → encours du 25/09 ; « SFIL » non reconnu | un vrai chiffre, mais pour une autre question | « Attention » sans chiffre ; titres par nom court ou émetteur ; filtres par titre |
| Le front redétectait le CSDR **par regex** sur les messages | un message reformulé fait perdre le rouge | codes `alertes` et `explication` exposés par l'API |
| Un achat de ligne nouvelle non dénoué (ABS_DEP expliqué à 100 %) restait « à relever » | du bruit dans la file du matin | absences entièrement expliquées → en attente |
| Un libellé `=1+2` ressortait tel quel dans le CSV | Excel l'exécute à l'ouverture | cellules texte neutralisées |
| Le contrôle des fichiers périmés existait mais **rien ne l'activait** | les fichiers d'avant-hier passaient | `EXPECTED_AS_OF_DATE=auto` (J-1 ouvré TARGET2) |
| La décision du LLM n'était tracée nulle part côté serveur | règle « sortie tracée » non tenue | une ligne d'audit par question |
| Le statut de traitement ne vivait que dans le navigateur | invisible pour le responsable, non auditable | statut partagé côté serveur, journal des changements |
| `except Exception` : nos bugs devenaient « fichier illisible, redéposez-le » | l'opérateur redépose en boucle | seules les erreurs de format bloquent le fichier |
| Casse des noms de fichiers : le front acceptait `Depositaire_A…`, le back répondait 422 | un dépôt refusé sans raison claire | une seule règle, insensible à la casse |
| 135 `fmt: skip`, E501 ignoré, aucun typage Python, aucun test front, Google Fonts, formats et accès à la base en double | du code qu'un relecteur ne prendrait pas au sérieux | formateur partout, pyright, vitest, polices locales, modules partagés |
