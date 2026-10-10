---
description: Relecture par le sous-agent reviewer (contexte neuf) : conformité à la consigne + qualité
argument-hint: [consigne du test, ou chemin du fichier qui la contient]
---

Lance le sous-agent `reviewer` (outil Agent, subagent_type = "reviewer") sur le travail courant.

Dans son prompt, donne-lui uniquement :
- la consigne d'origine, **telle quelle** : $ARGUMENTS (si vide, cherche-la dans `docs/CONSIGNE.md`, `NOTES.md` ou le README, et colle-la mot pour mot) ;
- la commande pour voir les changements : le commit de départ est le premier du dépôt (`git rev-list --max-parents=0 HEAD`), donc `git diff <ce commit>..HEAD` et `git status`.

Ne lui donne ni ton résumé, ni tes justifications : il doit juger sur pièces.

Quand il répond :
1. Affiche son rapport tel quel.
2. Classe les points en « à corriger maintenant » (bloquants, rapides) et « à mentionner à l'oral » (limites).
3. Demande-moi lesquels corriger ; ne corrige rien sans mon accord.
