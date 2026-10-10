# ADR 0001 : moteur de rapprochement déterministe, front HTML servi par FastAPI, LLM limité au besoin 2

- Statut : accepté
- Date : 2026-10-10

## Contexte
Le test dure 1 h. Un suspens raté coûte des pénalités CSDR et remonte au RCCI, et un chiffre inventé est un incident. Les règles de rapprochement sont explicites et sans tolérance. Les gérants posent des questions en langage libre sur `orsay.db`, qui ne doit jamais être modifiée.

## Décision
Le rapprochement est un moteur Python pur (parseurs par conservateur, `Decimal`, contrôles d'en-tête et de fin de fichier, typologie lue dans `parametrage.xlsx`), testé contre l'oracle de NOTES.md. Une page HTML unique, servie par FastAPI, permet de déposer les fichiers. Elle affiche les suspens filtrables et produit un point de situation copiable ou téléchargeable. Pour le besoin 2, Claude choisit un outil parmi des requêtes SQL paramétrées en liste blanche, sur une connexion SQLite en lecture seule. La réponse affiche la requête et les lignes sources.

## Alternatives écartées
- LLM pour rapprocher : c'est non déterministe sur une règle qui ne l'est pas, avec un risque de faux négatif inacceptable.
- Text-to-SQL libre : plus souple, mais il peut produire un chiffre faux (jointure ou unité oubliée, comme le % du nominal). La liste blanche est plus fiable sur 1 h.
- Streamlit ou notebook : rapide, mais ajoute une dépendance et donne une démo moins proche de l'outil métier qu'une page HTML.
- LangGraph : inutile pour un seul tour avec des outils. Le SDK Anthropic suffit.

## Conséquences
Le résultat est reproductible, testable et défendable ligne à ligne. En contrepartie, une question de gérant hors liste blanche reçoit « je ne sais pas répondre » au lieu d'un chiffre. En production, il faudra ajouter un historique des suspens (date d'apparition, âge CSDR), une piste d'audit persistante, de nouveaux formats de conservateurs et l'authentification.
