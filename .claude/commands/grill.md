---
description: Cadrage du cas client (compréhension métier + 5 questions max) puis plan en 5-8 étapes
argument-hint: [consigne / cas client, collé ou chemin du dossier]
---

Tu cadres un travail à faire vite (test chronométré, restitution orale devant le client). Cas : $ARGUMENTS

1. **Lis d'abord** la consigne et le dossier fourni (fichiers, README, CONTEXT.md, CLAUDE.md). Ne pose aucune question dont la réponse s'y trouve.
2. **Reformule le cas client en 5 lignes** : qui est le client, quel est son problème métier, qui utilise le résultat, ce qui coûte cher en cas d'erreur (faux positif / faux négatif), ce qu'est une bonne réponse pour lui. Je corrige si besoin. C'est ma compréhension métier, je dois pouvoir la défendre à l'oral.
3. Pose **au maximum 5 questions**, une seule fois, dans un seul message, chacune avec ta réponse par défaut (je peux répondre « ok »). Uniquement sur ce qui reste flou parmi : livrable attendu, données d'entrée (formats, volume, pièges vus), critère de réussite, contraintes (temps, clé API, langue, démo), hors périmètre.
4. Après mes réponses, écris un plan de **5 à 8 étapes** : chaque étape = résultat vérifiable + test + durée. Étape 1 = version minimale de bout en bout, démontrable. Prévois une étape de mesure (jeu étiqueté) et les 10 dernières minutes pour la démo.
5. Pour chaque choix structurant (approche, outil, modèle), donne en une ligne l'alternative écartée et pourquoi. Termine par « Plan OK ? » et **attends mon accord** avant tout code.
6. Note le cadrage et les hypothèses dans `NOTES.md`; crée `docs/adr/0001-*.md` (modèle `0000-template.md`) pour la décision d'architecture principale.
