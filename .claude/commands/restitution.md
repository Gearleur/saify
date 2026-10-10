---
description: Préparer la restitution : RESTITUTION.md (démarche, choix, limites) + docs/DEMO.md (script de démo de 15 min)
---

Prépare la restitution à partir du code réel, de `git log`, de `NOTES.md`, des ADR et de la consigne. N'invente rien : section sans matière = « non traité ». Concis, en français.

## 1. `RESTITUTION.md`
1. **Compréhension métier** : client, problème, enjeux, coût des erreurs, hypothèses prises.
2. **Architecture** : schéma texte (ASCII) du flux et des composants, une ligne par composant.
3. **Choix et alternatives écartées** : tableau « choix | pourquoi | alternative écartée | pourquoi pas ».
4. **Résultats mesurés** : chiffres mesurés sur un petit jeu de cas étiquetés (précision, rappel, cas en revue), commande pour reproduire.
5. **Limites** : honnêtes, y compris ce qui est fragile.
6. **Risques en production (finance)** : hallucinations (garde-fous, validation, LLM seulement pour l'ambigu), traçabilité et audit, données sensibles (IBAN, RGPD, hébergement, masquage avant LLM), coût et latence, évaluation continue, humain dans la boucle.
7. **Si j'avais une semaine** : 5-7 actions priorisées.

## 2. `docs/DEMO.md` : script de démo de 15 min, comme devant le client
Minutage : 2 min problème et contexte client · 8 min démo en direct (parcours unique, données du cas, une erreur ou un cas ambigu montré volontairement) · 3 min résultats et mesure · 2 min limites et suite. Indique les commandes exactes à lancer et un plan B si l'API tombe (mode mock).

## 3. Préparation des échanges
- 6 questions probables sur la **compréhension métier** (avec réponse courte).
- 6 questions sur les **choix techniques** (avec réponse courte).
- 5 moments de notre historique Claude Code à montrer pour illustrer ma démarche (cadrage, un désaccord avec une suggestion, un test qui a trouvé un bug, la relecture par le sous-agent) : cite-les d'après `NOTES.md` et `git log`.

Termine en listant les 3 points les plus faibles à préparer.
