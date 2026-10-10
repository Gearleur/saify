# saify : projet vide, prêt pour le test

Aucun code. Un environnement Python (FastAPI, Anthropic, LangGraph, pandas…), les commandes Claude Code, et de quoi documenter.

## Démarrer
1. Coller la clé Anthropic dans `.env` (ligne `ANTHROPIC_API_KEY=`), sans l'afficher.
2. Mettre les fichiers du client dans `data/` et le texte de la consigne dans `docs/CONSIGNE.md`.
3. Dans ce dossier : `uv sync` (déjà fait) puis `claude`.

## Le flux (à suivre dans l'ordre)
| Étape | Commande | Ce qu'on fait |
|---|---|---|
| 1. Aligner | `/grill` | reformuler le cas client, 5 questions max, plan de 5 à 8 étapes, ADR de l'architecture. On valide avant tout code. |
| 2. Documenter | `CONTEXT.md`, `docs/adr/` | langage du domaine et décisions. Les tenir à jour. |
| 3. Contexte court | `/clear` | repartir propre après le cadrage ; les décisions sont écrites. |
| 4. Construire | `/implement` | une étape à la fois : test qui échoue, code minimal, test et lint verts, commit. |
| 5. Vérifier | tests + lint | preuve explicite, sortie vue. |
| 6. Relire | `/review` | sous-agent `reviewer` à contexte neuf : conformité à la consigne puis qualité. Il rapporte, ne corrige pas. |
| 7. Restituer | `/restitution` | `RESTITUTION.md` : problème, architecture, choix, limites, risques finance, suite. |

## Fichiers
`.claude/` (commandes, sous-agent, permissions) · `CLAUDE.md` (règles) · `CONTEXT.md` (domaine) · `data/` · `docs/` · `pyproject.toml`.
