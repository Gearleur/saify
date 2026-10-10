---
description: Implémenter le plan validé étape par étape (tests + lint + commit par étape verte)
argument-hint: [numéro d'étape ou vide = prochaine étape]
---

Implémente le plan validé (`/grill`). Étape(s) visée(s) : $ARGUMENTS (vide = prochaine étape non faite).

Pour chaque étape, dans l'ordre :
1. Écris ou adapte d'abord un test qui exprime le résultat attendu, vois-le échouer.
2. Implémente le minimum pour le faire passer. Reste simple : pas d'abstraction ni de dépendance non demandée (demande avant d'en ajouter).
3. Lance les tests et le lint (commandes dans CLAUDE.md ; par défaut `uv run pytest -q` et `uv run ruff check .`). Corrige jusqu'au vert. Ne déclare jamais « fini » sans avoir vu la sortie verte.
4. Si vert : `git add -A && git commit -m "<message court, impératif>"`. Jamais de secret ni de fichier `.env` dans le commit.
5. Avant chaque choix structurant, dis-le en une phrase : « je choisis X plutôt que Y parce que Z », et demande-moi si c'est un choix qui engage (modèle, architecture, dépendance). Ajoute une ligne dans `NOTES.md` si tu as fait un choix ou écarté une alternative (matière pour la restitution).
6. Passe à l'étape suivante, sauf si une décision structurante est nécessaire : alors pose la question en une phrase.

Si une étape déborde (> 1,5× l'estimation), dis-le et propose de couper le périmètre plutôt que de continuer.
À la fin : résume en 5 lignes max ce qui marche, ce qui reste, ce qui est fragile.
