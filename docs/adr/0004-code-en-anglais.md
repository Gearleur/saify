# ADR 0004 : le code est en anglais, ce qu'un humain lit est en français

- Statut : accepté
- Date : 2026-10-11

## Contexte
Le back était en français. Le front mélangeait sans règle les deux langues : `ReconciliationProvider` à côté de `rapprochementsApi`, `StatusDot` à côté de `StatutControl`, `filtered` à côté de `visibles`. Le contrat d'API était en français, donc le front manipulait des champs français dans du code anglais. Un relecteur n'avait aucune règle pour savoir comment nommer une nouvelle chose.

## Décision
Une seule règle, qui tient en une phrase : **le code est en anglais, ce qu'un humain lit est en français.**
- **En anglais** : les identifiants, les fichiers, les champs JSON et les URL de l'API, le schéma SQLite que l'outil possède (`var/history.db`) et les variables d'environnement.
- **En français** : l'interface, les messages, les remèdes, les logs, les docstrings, la documentation, les commits et les noms de tests. Ces derniers sont des phrases qui spécifient un comportement.
- **Inchangé** : les données du client (colonnes d'`orsay.db` et du CSV PMS, feuilles du paramétrage, préfixes de fichiers) et les codes métier (`QTE`, `BLOQUANT`, `critique`, `a_traiter`…). Ce sont des valeurs, pas des noms de code.

Le vocabulaire métier a une traduction unique, fixée dans CONTEXT.md : suspens = `break`, rapprochement = `reconciliation`, conservateur = `custodian`, date d'arrêté = `as_of_date`…

## Alternatives écartées
- **Tout en français** : contraire aux conventions de l'écosystème (React, FastAPI, la bibliothèque standard), et le mélange réapparaît à chaque emprunt de nom technique.
- **Front en anglais, back en français** : deux règles au lieu d'une, et le front manipule des champs français dans du code anglais.
- **Code en anglais, contrat d'API en français** : moins de rupture, mais deux vocabulaires pour la même donnée de part et d'autre du contrat.

## Conséquences
- Le contrat d'API a changé de vocabulaire, pas de contenu : l'exemple de référence (`docs/sample_reconciliation.json`) est identique à l'ancien, clés traduites, ce qui a été vérifié automatiquement.
- Le renommage a été fait par les analyseurs du langage (jetons Python, AST TypeScript), qui ne touchent jamais au texte affiché ni aux données du client ; ruff, pyright, tsc et les tests ont servi de filet.
- Les variables d'environnement s'appellent `LLM_ENABLED` et `EXPECTED_AS_OF_DATE`. Un `.env` local qui utilise encore `LLM_ACTIF` ou `DATE_ARRETE_ATTENDUE` doit être mis à jour.
- L'historique s'appelle `var/history.db`. Un ancien `var/historique.db` est ignoré.
