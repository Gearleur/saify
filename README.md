# Orsay Gestion · Middle office

**Le rapprochement quotidien des positions titres, et des réponses fiables aux gérants, sans chiffre inventé.**

Orsay Gestion est une société de gestion qui gère 3 fonds (PAT, OBL, ACT), répartis chez 3 conservateurs (CACEIS, Euroclear, BNP/BP2S). Chaque matin, un opérateur passe 1 h 30 à comparer l'inventaire interne (PMS) aux relevés des conservateurs. Un écart raté coûte des pénalités CSDR et remonte au contrôle (RCCI). Dans la journée, les gérants lui demandent l'encours, les échéances, la concentration… et il fouille la base à la main.

Cet outil fait les deux : il **rapproche en quelques secondes** et dit quoi faire pour chaque écart. Il **répond aux questions** à partir de la base, et chaque chiffre vient d'une requête SQL en lecture seule, affichée avec ses lignes sources.

![Vue « Aujourd'hui » : fichiers reçus, synthèse et file de traitement par priorité](docs/images/01-aujourdhui.png)

---

## Démarrer en 3 commandes

Prérequis : [uv](https://docs.astral.sh/uv/). Il installe lui-même Python 3.12 et les dépendances verrouillées. Node n'est **pas** nécessaire : le front est livré déjà construit.

```bash
git clone https://github.com/Gearleur/saify.git && cd saify
make install        # ou : uv sync --locked
make run            # ou : uv run uvicorn middle_office.api:app --reload
```

Ouvrez http://127.0.0.1:8000, puis cliquez sur **« Lancer sur les fichiers d'exemple »**.

**La clé Anthropic est facultative.** Sans clé, l'outil fonctionne entièrement : les questions sont comprises par mots-clés au lieu du LLM. Pour activer le LLM : `cp .env.example .env`, puis renseignez `ANTHROPIC_API_KEY`. Le fichier `.env` est ignoré par git.

**En production**, `DATE_ARRETE_ATTENDUE=auto` refuse des fichiers qui ne sont pas arrêtés à J-1 ouvré (calendrier TARGET2). Laissée vide (par défaut), la démo sur les fichiers du 25/09 fonctionne.

### Front et back sur deux serveurs séparés (développement)

```bash
# Terminal 1 : l'API seule
make back                      # http://127.0.0.1:8000  (autre port : make back PORT=8010)

# Terminal 2 : le front React avec rechargement à chaud (Node 20+)
make front-install             # une fois : npm ci
make front-dev                 # http://localhost:5173, /api relayé vers le back
                               # back sur un autre port ou une autre machine :
                               # make front-dev API_URL=http://127.0.0.1:8010
```

Après une modification du front : `make front-build`, qui reconstruit `middle_office/web/` (à commiter).

### Toutes les commandes

| Commande | Rôle |
|---|---|
| `make install` | Python 3.12 et dépendances exactes (`uv.lock`) |
| `make run` | application complète (API + front construit) sur `:8000` |
| `make back` / `make front-dev` | les deux serveurs séparés, pour développer |
| `make cli` | rapprochement du 25/09 en ligne de commande |
| `make check` | lint, format, typage (pyright) et 245 tests Python (sans réseau ni LLM) |
| `make front-check` / `make front-build` | lint, typage, format et 21 tests du front / build dans `middle_office/web/` |

---

## Ce que fait l'outil

### Besoin 1 : le rapprochement du matin

**8 h : déposer les fichiers.** Les 4 fichiers du jour (PMS en CSV, CACEIS en Excel, Euroclear en largeur fixe, BNP en XML) sont lus et nettoyés. Chaque transformation est tracée dans un **journal** à 4 niveaux :

| Niveau | Sens | Exemple réel du 25/09 |
|---|---|---|
| `NORMALISE` | forme corrigée, sens inchangé | ` fr0000014078 ` → `FR0000014078` ; `"10 000"` → 10000 ; 2 décimales implicites |
| `EXCLU` | ligne retirée selon une règle du client | sous-compte technique P3G ; ligne sans sous-compte ; lot annulé chez BNP |
| `SIGNALE` | ligne conservée mais douteuse | ISIN à la clé de contrôle invalide |
| `BLOQUANT` | fichier refusé, **avec le remède** | mauvaise date, total de contrôle faux, compte inconnu de la transco, ligne ou lot en double, code `ACTION` inconnu |

Une seule anomalie bloquante, et **aucun suspens n'est produit**. Un rapprochement partiel cacherait des écarts : c'est le pire risque pour le client. Pour la même raison, tout doute qui pourrait combler un écart bloque au lieu d'être additionné ([ADR 0003](docs/adr/0003-un-doute-qui-peut-masquer-un-ecart-bloque.md)).

**8 h 05 : traiter par priorité.** Les suspens arrivent à la maille fonds × ISIN × conservateur, avec leur type (`QTE`, `ABS_DEP`, `ABS_INT`, `DEP`) et l'action attendue lue dans le paramétrage du client :
- **Critique** : une opération aurait dû être dénouée et ne l'est pas (risque CSDR) ;
- **À relever** : titre absent, mauvais conservateur, écart inexpliqué ;
- **En attente** : écart ou absence **entièrement expliqué**, avec un calcul signé, par une opération en cours (« op. n°19 ACHAT 25 000, dén. 26/09 »).

![Table des suspens et fiche de détail, avec la piste et les lignes sources](docs/images/02-suspens-fiche.png)

Chaque suspens est traçable jusqu'à la ligne du fichier d'origine. Le statut de traitement (à traiter, en cours, traité) est **partagé avec l'équipe** et chaque changement est journalisé ; relancer le rapprochement du jour ne remet pas le travail à zéro.

**Le lendemain matin.** La date d'arrêté est lue dans les fichiers, jamais codée en dur. Avec les mêmes fichiers datés du 26/09, l'achat SCHNEIDER aurait dû se dénouer et ne l'est toujours pas : il passe **en critique**.

![Fichiers du 26/09 : SCHNEIDER passe en critique, risque CSDR](docs/images/07-lendemain-critique.png)

**10 h : le point de situation.** Un texte prêt à coller dans un mail pour le responsable, l'export CSV (formules neutralisées pour Excel), et la matrice fonds × conservateur.

| Point de situation | Journal de nettoyage |
|---|---|
| ![Point de situation](docs/images/03-point-de-situation.png) | ![Journal](docs/images/04-journal.png) |

### Besoin 2 : les questions des gérants et du RCCI

« Encours du fonds obligataire ? », « Qu'est-ce qui arrive à maturité d'ici la fin de l'année ? », « Concentration par émetteur de PAT ? », « Opérations non dénouées ? », « D'où vient le suspens sur SCHNEIDER ? »

![Réponse à une question de concentration, avec vigilances et preuves](docs/images/05-questions-reponse.png)

Le fonctionnement, conçu pour qu'**aucun chiffre ne puisse être inventé** :

```
question ─► LLM (Claude Haiku 5.5) ─► intention typée, validée par pydantic
             │  ne reçoit que la question et la date, jamais les données
             │  panne, clé absente ou refus : repli par mots-clés (raison tracée)
             ▼
            catalogue de requêtes SQL fixes, base en lecture seule, calculs en Decimal
             ▼
            phrase issue d'un gabarit + chiffres + requête exacte + lignes sources
```

- **Le LLM classe la question, il ne répond pas.** Il choisit une entrée du catalogue et ses paramètres. Les chiffres viennent du SQL, la phrase vient d'un gabarit.
- **Lecture seule garantie par 3 verrous** : fichier ouvert en `mode=ro`, `PRAGMA query_only`, et un autorisateur SQLite qui refuse toute opération autre qu'une lecture. « Personne ne doit pouvoir modifier l'inventaire » : c'est testé.
- **Sous le seuil de confiance, aucune réponse chiffrée** : l'outil affiche « Attention » et propose 2 ou 3 reformulations, revérifiées contre le catalogue. C'est le cas aussi pour une demande hors catalogue ou d'écriture.
- **Jamais de réponse à côté** : une autre date que celle de la base, l'encours d'un titre seul ou un titre ambigu (« l'OAT » : 4 titres) donnent un « Attention » plutôt qu'un vrai chiffre qui répondrait à une autre question. Les titres se citent par ISIN, libellé, nom court (« SFIL ») ou émetteur.
- **Chaque question laisse une ligne d'audit** : intention retenue, source (LLM ou mots-clés), confiance, paramètres, avec l'identifiant de requête mais jamais le texte de la question.
- **Règles de vigilance** : des seuils internes simples (un émetteur au-delà de 10 % ; les émetteurs au-delà de 5 % cumulant plus de 40 %), modifiables, et **jamais présentés comme un verdict réglementaire**.
- **Usage de la clé encadré** : modèle imposé, budget de 300 appels par jour, 4 appels simultanés au maximum, timeout, cache des questions identiques, rate limit dédié, consommation journalisée. La clé n'est jamais renvoyée ni écrite dans les logs.

![Une demande d'écriture : refus explicite, reformulations proposées](docs/images/06-questions-attention.png)

---

## Architecture

```
middle_office/
├── domaine/                  métier pur, sans HTTP ni framework
│   ├── rapprochement/        besoin 1 : sources.py (4 lecteurs + journal), moteur.py, situation.py, calendrier.py
│   ├── questions/            besoin 2 : catalogue.py, vigilance.py, comprehension.py, modeles.py
│   └── base_gestion.py · formats.py   orsay.db en lecture seule (3 verrous) · écritures françaises en Decimal
├── api/                      FastAPI (contrat : docs/API.md)
│   ├── routes/               systeme · rapprochements · questions (JSON et flux SSE) · web
│   ├── services/             dépôt, exécution, historique et statuts (SQLite), questions et audit, référentiel, encadrement du LLM
│   ├── middleware.py         request id, rate limit, taille des requêtes, en-têtes de sécurité, logs
│   └── config.py · schemas.py · erreurs.py · limiteur.py · dependances.py · app.py
└── web/                      build du front (généré)
front/src/                    React + TypeScript + Tailwind + shadcn/ui (architecture : docs/FRONT.md)
├── types/ · lib/api/         contrat d'API typé, client HTTP et SSE, formatage décimal sans float
├── components/ · components/ui/   composants partagés, primitives shadcn
├── features/                 triage · files · suspens · situation · journal · questions · settings
└── app/                      coquille, barre latérale, routes, palette ⌘K
tests/                        245 tests Python, oracles calculés à la main (front : 21 tests vitest)
```

Le domaine ne sait rien du HTTP, et l'API ne connaît aucun format de fichier : ajouter un quatrième conservateur, c'est écrire un lecteur. Sécurité : CSP stricte sans aucun tiers (`'self'` partout, polices servies par l'application), en-têtes de sécurité, erreurs sans trace interne, validation de chaque entrée, refus des XML piégés (`DOCTYPE`/`ENTITY`).

## Les choix, et pourquoi

| Choix | Plutôt que | Parce que |
|---|---|---|
| Rapprochement **déterministe**, en Python | un LLM | la règle est exacte, sans tolérance ; un LLM n'ajoute qu'un risque de suspens raté ([ADR 0001](docs/adr/0001-moteur-deterministe-front-html.md)) |
| `Decimal` partout, quantités en **texte** dans le JSON | `float` | pas d'arrondi binaire sur des positions ; le front formate sans `parseFloat` |
| Blocage **total** si un fichier est refusé, avec remède | rapprocher les fichiers sains | un fichier conservateur manquant produirait de faux « absents » en masse |
| Un seul suspens `DEP` (avec l'écart) quand un titre est chez un autre conservateur | `DEP` + `QTE` | l'énoncé : « un seul suspens, pas deux » |
| `orsay.db` facultative pour le rapprochement | la base comme clé | l'énoncé : elle informe, elle ne décide pas ; sans elle, les suspens sortent quand même |
| Questions par **catalogue** + LLM classifieur | du text-to-SQL | un chiffre faux (×1 000 sur le nominal, mauvaise jointure) serait un incident RCCI |
| React + shadcn, **build commité** | HTML natif / Next.js | finition et composants ; une seule commande pour la démo, sans Node ([ADR 0002](docs/adr/0002-front-react-shadcn.md)) |

Les décisions détaillées et les alternatives écartées sont dans [`NOTES.md`](NOTES.md), le vocabulaire métier dans [`CONTEXT.md`](CONTEXT.md).

## Ce qui est vérifié, et ce qui ne l'est pas

**Vérifié par exécution, et rejouable par vous en une commande :**

| Quoi | Commande |
|---|---|
| Les 7 suspens du 25/09 égalent un oracle calculé à la main (NOTES.md), les encours aussi (OBL 724 836,00 €, ACT 167 647 000,00 €, PAT 256 448 170,50 €) | `make cli`, `make check` |
| 245 tests Python : un par piège des données, un par règle métier, chaque bug trouvé en revue reproduit avant d'être corrigé, et l'API (erreurs, 413, 422, 429, SSE, lecture seule, audit, secret jamais exposé) | `make check` |
| Typage : pyright (code et tests) et TypeScript strict, 0 erreur ; lint et format sans exception (plus aucun `fmt: skip`) | `make check`, `make front-check` |
| 21 tests front, dont un test de contrat sur la vraie réponse de l'API | `make front-check` |
| Le build commité correspond aux sources du front | CI (`git diff --exit-code`) |

**Affirmé par l'assistant de code (Claude Code), d'après ses sessions, non rejoué ici :**
- Un essai réel avec Claude Haiku 5.5, sur des questions formulées librement, a révélé 4 défauts invisibles aux tests (horizon « fin d'année », refus d'écriture, hors catalogue, reformulations inventées), tous corrigés. La clé a depuis été révoquée (401), comme prévu par l'énoncé : le chemin LLM n'est plus vérifié que par des faux clients.
- Clone neuf sans `.env` : installation, tests, serveur et front fonctionnels.
- Front : zéro violation CSP sur le parcours complet, navigation au clavier.

**Non vérifié :** la CI GitHub sur cette version ; des tests de composants React (seule la logique pure est testée) ; le glisser-déposer à la vraie souris.

## Limites connues

- **Pas d'authentification** : le journal des statuts et l'audit des questions identifient une requête, pas une personne.
- **Processus unique** : le rate limit et le budget LLM vivent en mémoire, l'historique et les statuts dans un SQLite local (`var/`, hors git) sans rétention définie. Pour la production : une base partagée, et une durée de conservation fixée avec le RCCI.
- **Le seuil de confiance (0,7) repose sur la confiance que le LLM s'attribue**, un signal faible. Il faudrait le calibrer sur un jeu de vraies questions de gérants.
- **Unités** : on suppose les obligations en nominal partout. Un conservateur qui enverrait un nombre de titres produirait de faux écarts.
- **Un titre trouvé dans un autre fonds** (erreur de transco probable) donne deux suspens, non fusionnés.
- **Remèdes et horizon des échéances (12 mois)** : rédigés et choisis par nous, à valider avec le middle office.
- **Le domaine importe le SDK Anthropic** : une interface « classifieur » le rendrait indépendant du fournisseur.

## Ce que la relecture a changé

Le projet a été construit avec Claude Code, étape par étape, chaque étape relue et challengée. Sans ces relectures, l'outil aurait passé ses propres tests et donné les 7 bons suspens, mais il aurait été fragile là où le client a peur : des écarts perdus en silence, des chiffres répondant à une autre question. Le détail, avec la revue de code finale (deux faux négatifs et une réponse fausse reproduits puis corrigés), est dans [`docs/RELECTURE.md`](docs/RELECTURE.md).

---

## Documentation

- [`docs/API.md`](docs/API.md) : le contrat d'API (routes, erreurs, garde-fous, flux SSE)
- [`docs/FRONT.md`](docs/FRONT.md) : les choix d'agencement vue par vue, et l'architecture du front
- [`docs/adr/`](docs/adr/) : les décisions d'architecture · [`docs/RELECTURE.md`](docs/RELECTURE.md) : ce que la relecture a trouvé et changé
- [`NOTES.md`](NOTES.md) : le journal des choix, dans l'ordre, avec les alternatives écartées
- [`CONTEXT.md`](CONTEXT.md) : le glossaire métier (middle office, suspens, CSDR…)
- [`docs/CONSIGNE.md`](docs/CONSIGNE.md) : l'énoncé du cas · [`docs/sessions/`](docs/sessions/) : les exports des sessions Claude Code
- [`exploration/`](exploration/) : l'analyse exploratoire des données (notebook)

Les données de `data/donnees/` sont celles du cas (fictives).
