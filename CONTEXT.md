# Contexte métier : Orsay Gestion

**Orsay Gestion** : société de gestion de portefeuille agréée AMF, 3 FCP (PAT Orsay Patrimoine, OBL Orsay Obligations, ACT Orsay Actions Europe), 3 conservateurs (A = CACEIS, B = Euroclear, C = BNP/BP2S). Deux besoins : le rapprochement quotidien des positions titres (besoin 1) et les réponses aux gérants et au RCCI sur la base de gestion (besoin 2).

## Glossaire titres et middle office
- **PMS** : outil de gestion de portefeuille. Il tient l'inventaire interne, en date de négociation.
- **Conservateur / teneur de compte-conservateur (dépositaire)** : il détient les titres. Il voit les opérations au dénouement (J+2).
- **Rapprochement de positions** : comparaison des quantités PMS et conservateur, par fonds, ISIN et conservateur.
- **Suspens** : ligne qui ne rapproche pas. Types : `QTE` (quantité différente), `ABS_DEP` (absent chez le conservateur), `ABS_INT` (absent du PMS), `DEP` (chez un autre conservateur que prévu).
- **Dénouement / règlement-livraison** : échange effectif des titres contre les espèces (J+2). Une opération non dénouée explique un écart temporaire.
- **CSDR** : règlement européen qui pénalise les défauts de règlement-livraison.
- **RCCI** : responsable de la conformité et du contrôle interne.
- **Sous-compte** : subdivision de gestion dans le PMS. Plusieurs sous-comptes agrégés forment un fonds. `P3G` est un compte technique de passage, exclu.
- **Nominal** : la quantité d'une obligation s'exprime en montant nominal. Les cours sont en % du nominal, pied de coupon (hors coupon couru).
- **Journal de nettoyage** : trace de chaque transformation des données sources, au niveau NORMALISE, EXCLU, SIGNALE ou BLOQUANT.

## Termes propres à l'outil
- **Priorité d'un suspens** : `critique` (opération non dénouée à sa date prévue, risque CSDR), `à relever` (absence, mauvais dépositaire, écart non ou partiellement expliqué), `en attente` (écart, ou absence, entièrement expliqué par une opération en attente de dénouement ; jamais un DEP).
- **Piste** : l'opération en attente (table `mouvements`) qui explique un écart, avec un calcul signé (achats moins ventes) : entièrement, partiellement ou pas du tout.
- **Remède** : ce que l'opérateur doit faire pour lever un blocage (champ `remede` de tout BLOQUANT).
- **Explication** : ce que les opérations en attente disent de l'écart, en code stable : `totale`, `partielle`, `contraire` ou `aucune`. C'est elle, pas le texte de la piste, qui décide de la priorité.
- **Alerte** : code d'un signalement porté par un suspens (`CSDR`, `DEP_AMBIGU`, `ISIN_INVALIDE`, `PISTE_MULTI_CONSERVATEURS`). Le front et la priorité lisent les codes, jamais les messages.
- **Doublon** : deux lignes d'une même source au même compte et ISIN (pour C : même compte, ISIN et lot). BLOQUANT, car additionnées elles pourraient égaler le PMS et masquer un écart (ADR 0003).
- **Statut de traitement** : `à traiter`, `en cours`, `traité`. Il est partagé entre les postes et journalisé, avec une clé stable d'un rapprochement à l'autre du même arrêté.
- **Date d'arrêté attendue** : J-1 ouvré (calendrier TARGET2) quand `DATE_ARRETE_ATTENDUE=auto` ; des fichiers d'une autre date sont refusés.
- **Encours valorisé** : quantité × cours pour les actions ; nominal × cours / 100 pour les obligations (cours en % du nominal, pied de coupon, sans coupon couru).
- **Règle de vigilance** : seuil interne de concentration (un émetteur au-delà de 10 % ; émetteurs au-delà de 5 % cumulant plus de 40 %). Attire l'attention, ne juge jamais la conformité réglementaire.
- **Intention** : l'entrée du catalogue de questions que le LLM a reconnue (encours, échéances, concentration, opérations non dénouées, origine d'un suspens, hors catalogue).
- **Réponse à côté** : un vrai chiffre, mais pour une autre question (autre date, titre ignoré). L'outil refuse d'en donner : « Attention » et reformulations (ADR 0003).
- **Pièges des données** : formats FR (`1 234,56`, `dd/mm/yyyy`), séparateur `;`, décimales implicites, virgule décimale, ISIN en minuscules avec espaces, libellés de conservateur hétérogènes, namespace XML, lots multiples et annulations chez C.
