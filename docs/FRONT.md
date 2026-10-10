# Front : arbitrages d'agencement et architecture

Front en **Vite + React 18 + TypeScript + Tailwind 4 + shadcn/ui (Radix)**, sources dans `front/`, build dans `middle_office/web/` servi par FastAPI (`/` et `/static/…`, voir ADR 0002). Contrat : `docs/API.md`. Ce document explique **pourquoi chaque information est à sa place**, en suivant la matinée réelle de l'opérateur middle office d'Orsay Gestion, puis comment le code est rangé.

```bash
cd front && npm install
npm run dev        # Vite sur :5173, proxy /api → 127.0.0.1:8000
npm run build      # écrit middle_office/web/ (index.html + assets/), à commiter
npm run typecheck  # tsc --noEmit
npm run lint       # ESLint (TypeScript + React Hooks), zéro avertissement toléré
npm run format     # Prettier
```

## Le principe directeur

L'écran suit la matinée, dans l'ordre :

| Heure | Geste de l'opérateur | Où |
|---|---|---|
| 8 h | Déposer les 4 fichiers, vérifier qu'ils sont tous là et acceptés | Aujourd'hui, bloc « Fichiers du jour » |
| 8 h | Savoir si un fichier est refusé, et quoi faire | Aujourd'hui, bandeau rouge tout en haut |
| 8 h à 10 h | Traiter le critique, puis l'« à relever », surveiller l'« en attente » | Aujourd'hui, file de traitement groupée par priorité |
| Pour chaque suspens | Comprendre, agir, marquer comme traité | Fiche ancrée à droite |
| 10 h | Envoyer le point de situation au responsable | Point de situation |
| Dans la journée | Répondre aux gérants et au RCCI | Questions |
| Rarement | Audit, paramétrage | Section « Contrôle » de la barre latérale |

Ce qui sert à 8 h est au-dessus de la ligne de flottaison (1440 × 900). Ce qui sert une fois par semaine n'occupe pas le flux principal.

## Direction visuelle : Attio, la retenue avant tout

- **Quasi monochrome.** La couleur ne porte qu'une information, sous la forme d'un **point de 7 px** (`StatusDot`) devant un texte gris foncé : rouge (critique, BLOQUANT, CSDR), ambre (à relever, signalé, vigilance), gris (en attente, exclu), vert (accepté, traité, confiance haute), bleu (en cours, prêt à envoyer). Aucune pastille ni tag rempli de couleur.
- **Le rouge est réservé** au BLOQUANT et au CSDR. Le seul fond teinté de l'application est le rouge très pâle du bandeau « Rapprochement bloqué » et d'un fichier refusé.
- **Tags neutres** (`Tag` : fonds, type, conservateur, code) : fond `#F4F5F6`, bordure `#E8E9EB`, texte gris, 12 px.
- **Tables façon Supabase** (`DataTable`) : en-têtes gris 12 px, lignes de 38 px, filets de 1 px, pas de carte autour des lignes, recherche et filtres en **menus déroulants** (`FilterMenu`, DropdownMenu shadcn) avec effectifs.
- **KPI en chiffres nus** (`KpiRow`), séparés par un filet, sans boîte colorée.
- **Tokens shadcn** en variables CSS (`front/src/index.css`) : fond `#FFFFFF`, barre latérale `#FAFAFA`, surface `#F7F7F8`, bordures `#EBECEE` / `#DFE1E4`, textes `#1E1F22` / `#5F6167` / `#9A9DA3`, survol `#F4F5F6`, sélection `#F2F5FE`, primaire **noir** (blanc en sombre), bleu `#2D6BF0` réservé au focus et aux liens.
- **Inter** 13 px (`cv11`, `ss01`, chiffres tabulaires), poids 500 pour les libellés, 600 au maximum ; **JetBrains Mono** 12 px pour les ISIN, fichiers, règles et SQL.
- Le clair est la référence ; le sombre suit `prefers-color-scheme` avec les mêmes règles (tokens redéfinis, aucune couleur en dur dans les composants).
- Fluidité : transitions de 120 à 160 ms, focus visibles, squelettes discrets au chargement, `prefers-reduced-motion` respecté.

Écarté : les pastilles colorées par priorité, par type et par niveau de la première version (chaque ligne en portait trois, la couleur ne signalait plus rien) ; une identité « marquée » (couleur d'accent, typographie d'affichage) : c'est un outil de production, pas une vitrine.

## Aujourd'hui (`#/a-traiter`, vue d'arrivée)

**Ce qu'on y fait** : la matinée entière, de la réception des fichiers à la fin du triage.
**Pour qui** : l'opérateur middle office.
**Quand** : de 8 h jusqu'à la fin du traitement.

Ordre vertical, dans l'ordre du geste :

1. **En-tête** : titre, phrase d'état (« Arrêté du 25/09/2026, lancé à 20:48. Aucun critique : 5 suspens à relever. »), bouton « Lancer sur les fichiers d'exemple (25/09) ». La date de ce bouton vient de `GET /api/sante` (`date_arrete` = date de référence de la base de gestion), **jamais d'une constante**. Bouton noir tant que rien n'est chargé, puis secondaire.
2. **Bandeau « Rapprochement bloqué »**, uniquement s'il y a un BLOQUANT. Il passe avant tout le reste : sans lui, aucun suspens n'est calculé. Chaque point donne fichier, ligne, règle, valeur brute et surtout **« Que faire »** (le `remede` du back), avec une case « corrigé » pour suivre la relance (état local à l'écran).
3. **Fichiers du jour** : les 4 sources attendues (PMS, A CACEIS, B Euroclear, C BNP/BP2S) côte à côte, avec le fichier reçu et son état (Accepté, Refusé + règle, Non reçu). Pendant un dépôt (glisser-déposer n'importe où, ou « Déposer des fichiers »), la même bande montre **la sélection en cours seulement** (« Prêt à envoyer », problème détecté localement, « Non sélectionné »), le bouton « Rapprocher ces fichiers (n) » et l'erreur 413 / 422 / 429 (avec le compte à rebours `Retry-After`). Envoi en base64 dans du JSON.
4. **Synthèse** : Critique, À relever, En attente, Traités sur ce poste. Un clic fait défiler jusqu'au groupe.
5. **File de traitement** : **une seule table** groupée par priorité (Critique, À relever, En attente de dénouement), colonnes alignées entre les groupes. Un groupe vide le dit en une ligne (« Aucun risque CSDR détecté. ») : l'absence de critique est une information.
6. **Écarté ou signalé au nettoyage** : les EXCLU et SIGNALE du journal (SANOFI sans sous-compte, P3G, annulation RTE, ISIN invalide), avec un lien vers le journal complet.

**Pourquoi c'est placé là** : la vérification de réception est la première chose faite le matin ; elle tient en une bande de 90 px au-dessus de la file. Le blocage est au-dessus de la réception, parce qu'il interdit tout le reste.

**Colonnes de la file** : Titre (et ISIN), Fonds, Conservateur, Qté PMS, Qté conservateur, Écart, **Action attendue**, Statut. Le **type d'écart** n'y figure pas : le matin, l'opérateur a besoin de savoir *quoi faire* ; le type est en infobulle sur le titre et dans la fiche. Les colonnes secondaires se retirent selon la largeur réelle de la table (requêtes de conteneur), pas celle de la fenêtre : la fiche ouverte retire d'abord Conservateur, puis les quantités.

**Date d'arrêté inconnue** : si le PMS est absent ou porte plusieurs dates, `date_arrete` vaut `null` (rapprochement BLOQUE) ; l'interface écrit « Date d'arrêté inconnue », jamais une date supposée.

**Écarté** : des cartes par suspens (illisibles à 7 lignes, impossibles à 70) ; le journal complet sur cette page (74 lignes dont 69 NORMALISE, c'est de l'audit) ; une vue « Fichiers » séparée ; trois tables empilées pour les groupes (colonnes désalignées).

## Fiche du suspens (panneau ancré à droite)

**Ce qu'on y fait** : comprendre, agir, marquer comme traité, sans quitter la file.
**Pour qui** : l'opérateur, suspens par suspens.
**Quand** : pendant le triage, depuis Aujourd'hui, Suspens ou la palette.

Panneau ancré à droite, lu comme un record Attio ; la table reste visible à gauche (sous 1280 px, il passe en surcouche). Ordre :

1. **Comparer** : PMS, conservateur (son nom), écart signé (PMS moins conservateur) ; trois chiffres nus.
2. **Action attendue** (lue dans TYPES_ECARTS par le back), puis le **statut local** À traiter / En cours / Traité juste sous le geste qu'il conclut.
3. **Détails** en liste clé → valeur : priorité, type (libellé officiel et code), fonds, conservateur, ISIN, piste, signalements (point rouge si CSDR).
4. **Lignes sources** : fichier et numéro de ligne en mono, la traçabilité jusqu'à la donnée brute.

Clavier : `↑` `↓` passent au suspens voisin **dans l'ordre de la liste d'où la fiche a été ouverte**, `Échap` ferme. Statut dans `localStorage` (clé : date d'arrêté + fonds + ISIN + conservateur + type, accès en try/catch).

**Écarté** : la fenêtre modale qui masque la file (on perd le contexte d'un suspens à l'autre) ; la Sheet modale de shadcn (verrou de défilement qui injecte un `<style>`, refusé par la CSP).

## Suspens (`#/suspens`)

**Ce qu'on y fait** : analyser, trier, filtrer, retrouver un suspens, exporter.
**Pour qui** : l'opérateur en analyse, son responsable qui veut une vue par fonds ou par conservateur.
**Quand** : après le triage, ou quand on cherche un cas précis.

Barre d'outils façon Supabase : recherche (`/`), cinq menus déroulants (Priorité, Fonds, Conservateur, Type, Statut) avec cases et effectifs, « Réinitialiser », effectif filtré, « Exporter CSV ». Table à plat, triable sur chaque colonne (un clic, puis l'inverse, puis l'ordre du back) ; les quantités sont comparées en décimal exact, sans `float`. Ici le **Type** est affiché et l'Action passe dans la fiche : c'est la vue où l'on classe. Les filtres se pré-remplissent depuis l'adresse (`#/suspens?fonds=OBL&conservateur=A`, utilisé par la matrice du point de situation).

**Pourquoi une vue distincte d'Aujourd'hui** : la file du matin impose un ordre (la priorité) ; l'analyse a besoin de tous les tris. Les fusionner donnerait une file triable dans le désordre.

**Écarté** : la « forêt de chips » de filtres (15 boutons sur deux lignes).

## Point de situation (`#/point`)

**Ce qu'on y fait** : envoyer l'état du rapprochement au responsable, sans rien retaper.
**Pour qui** : l'opérateur vers 10 h ; le responsable en est le lecteur.
**Quand** : une fois par jour.

Le texte du back (figé à la création du rapprochement) est affiché tel quel, comme l'aperçu d'un mail. **« Copier le texte »** est le bouton primaire de la page ; « Exporter CSV » (lien direct vers `/api/rapprochements/{id}/suspens.csv`) est à côté. À droite, en appui : la **matrice fonds × conservateur** (un point de la couleur de la priorité la plus haute ; un clic ouvre les suspens filtrés ; un DEP `A→B` garde sa propre colonne, on ne le range pas d'office chez l'un ou l'autre), la répartition par type et les compteurs du journal.

**Écarté** : Copier et Exporter dans une barre globale présente partout (ils n'ont de sens qu'ici et dans la palette) ; un graphique (quatre nombres se lisent mieux nus).

## Questions (`#/questions`, besoin 2)

**Ce qu'on y fait** : interroger la base de gestion en français et obtenir un chiffre prouvé.
**Pour qui** : les gérants et le RCCI.
**Quand** : dans la journée, hors du flux du matin.

Mise en page d'**assistant métier sobre**, pas de bulle de chat : une colonne de travail et une colonne d'appui.

- **Champ de question** (Entrée envoie, Maj + Entrée passe à la ligne, 3 à 500 caractères contrôlés avant l'envoi, compteur), `/` y place le curseur.
- **Envoi par `POST /api/questions/flux`** (lu avec `fetch` + `response.body`, pas `EventSource`). Les étapes s'affichent au fil de l'eau : « Analyse de la question… » → l'intention comprise (« Concentration par émetteur, fonds PAT, par mots-clés, confiance 0,80, en 1,2 s ») → « Requête en lecture seule sur la base de gestion… » → la réponse. Une fois la réponse arrivée, les étapes se replient en une ligne (« Comprise par LLM en 2,4 s », « Requête en lecture seule en 3 ms »).
- **Carte de réponse** : la phrase (gabarit du back), les **chiffres en grand** (au-delà de trois, un classement compact : la concentration a 7 émetteurs), les **vigilances** (point ambre, « seuil de vigilance interne, pas un verdict réglementaire », émetteurs en tags neutres), les avertissements de méthode (point gris), puis les preuves : **lignes sources** (table, montants formatés en décimal), **requête SQL repliable** avec ses paramètres (`:date = 2026-09-25`) et un bouton Copier, et une **ligne de traçabilité** en mono (intention, source, confiance, fonds, horizon, ISIN, détail du repli).
- **État « Attention »** (aucun chiffre sûr) : un point ambre, « Pas de réponse chiffrée », le message de l'API et les **reformulations cliquables** qui relancent la question. Pas de rouge : ce n'est pas une panne, c'est l'outil qui refuse d'inventer.
- **Colonne d'appui** : l'**indicateur LLM** tiré de `/api/sante` (actif ou coupé, modèle, appels du jour sur le budget, et « dernière question en repli » avec la raison si le LLM a échoué), la date de référence de la base (`sante.date_arrete`), les **exemples cliquables** (encours OBL, tombées à 3 mois, concentration de PAT, opérations non dénouées, origine du suspens SCHNEIDER) et l'**historique de la session** (un point vert si chiffré, ambre si « Attention » ou erreur).
- **Erreurs** : 422 et 429 arrivent avant l'ouverture du flux et s'affichent sobrement avec le code et, pour le 429, un compte à rebours `Retry-After` ; un événement `erreur` du flux s'affiche de la même façon.

**Pourquoi dans sa propre section** : autre public, autre moment de la journée. **Pourquoi pas un chat** : chaque réponse est un objet de preuve (chiffre, requête, lignes) qu'on relit et qu'on copie ; un fil de discussion les noierait. L'historique de session suffit pour revenir à une réponse.

**Écarté** : afficher la confiance numérique en grand (signal faible, auto-déclaré par le LLM : elle est dans la trace) ; masquer le SQL derrière une page à part (la preuve doit être à un clic).

## Journal et fichiers (`#/journal`, section « Contrôle »)

**Ce qu'on y fait** : l'audit. Retrouver pourquoi une valeur a changé, prouver quel fichier a été rapproché.
**Pour qui** : l'opérateur en cas de doute, le RCCI, l'auditeur.
**Quand** : rarement.

Deux onglets. **Journal de nettoyage** : recherche (`/`) et menu « Niveau » (la définition de chaque niveau est dans le menu, pas de légende permanente). Par défaut NORMALISE est masqué et le compteur le dit (« 5 sur 74 lignes, 69 normalisations masquées »). Le remède d'un BLOQUANT est affiché sous le motif (« Que faire : … »). **Fichiers reçus** : source, nom, taille, contrôle, empreinte SHA-256 complète. L'ancienne adresse `#/fichiers` ouvre cet onglet. Les colonnes du journal sont les mêmes que celles des anomalies de la matinée (un seul module `journalColumns`).

**Écarté** : le journal complet en flux principal ; les SHA-256 sur la page du matin (inutiles pour trier, utiles pour prouver).

## Paramétrage (`#/parametrage`, section « Contrôle »)

**Ce qu'on y fait** : consulter le référentiel (lecture seule, tiré de `parametrage.xlsx`).
**Pour qui** : l'opérateur, son responsable.
**Quand** : une fois par semaine, ou en cas de BLOQUANT `PARAMETRAGE` ou de transco manquante.

Quatre onglets (Types d'écarts, Fonds et conservateurs, Transcodifications, Exclusions) au lieu d'une page qui empilerait huit tables. Une erreur `503 PARAMETRAGE_INDISPONIBLE` s'affiche à la place des onglets.

## Éléments transverses

- **Barre latérale** : sections en gris (Rapprochement, Base de gestion, Contrôle), compteurs gris, un point rouge seulement s'il y a du critique ou un blocage. En bas, l'**historique** des rapprochements (arrêté ou « Date inconnue », heure, nombre de suspens ou « bloqué »), rechargeable d'un clic ; puis la **santé de l'API** (version, base indisponible, LLM et appels du jour).
- **Barre du haut** : fil d'Ariane à gauche ; à droite, l'état du rapprochement chargé.
- **Palette ⌘K / Ctrl K** (cmdk, sans Dialog Radix) : vues, actions (lancer l'exemple, déposer, exporter le CSV), recherche de suspens par titre, ISIN ou fonds (ouvre la fiche), et « Poser la question : … » (toujours classé en dernier).
- **Clavier** : `↑` `↓` `Entrée` dans les tables de suspens, `Échap` ferme fiche, menu ou palette, `/` recherche (ou champ de question).
- **Toasts** blancs, un point de couleur, trois au maximum, en bas au centre.
- **Responsive** : sous 1280 px la fiche passe en surcouche ; les colonnes se retirent selon la largeur de la table ; sous 900 px la barre latérale devient un tiroir.
- **Reprise** : le dernier rapprochement ouvert est rechargé au démarrage (son identifiant est gardé dans `localStorage`, l'historique est côté serveur).

## Intégration et sécurité

- Vite : `base: "/static/"`, `build.outDir: "../middle_office/web"` (`emptyOutDir`), `modulePreload.polyfill: false` et aucun script inline : l'`index.html` buildé ne référence que `/static/assets/*.js` et `*.css`.
- **CSP inchangée** (`style-src 'self' https://fonts.googleapis.com`, sans `'unsafe-inline'`) : aucune violation en console sur tout le parcours. Les composants qui injectent un `<style>` sont évités : DropdownMenu en `modal={false}` (pas de `react-remove-scroll`), pas de Dialog/Sheet/ScrollArea/Select Radix, palette et fiche faites à la main. Les positions calculées par Radix (Popper) passent par le CSSOM (`element.style`), que la CSP n'interdit pas.
- Aucun `dangerouslySetInnerHTML` (interdit par une règle ESLint), aucune date en dur, aucun `parseFloat` (interdit aussi) : quantités et montants restent des chaînes, formatées par `lib/decimal.ts` (espace fine insécable, virgule, vrai signe moins, `+` devant un écart positif) et triées par comparaison décimale exacte.

## Architecture du code (`front/src/`)

```
src/
├── main.tsx, index.css        point d'entrée ; tokens (clair, sombre) et thème Tailwind
├── types/api.ts               types du contrat, alignés sur docs/API.md (date_arrete: string | null…)
├── lib/                       sans React : la logique pure, testable seule
│   ├── api/                   client typé, un module par ressource
│   │   ├── http.ts            fetch, ApiError {status, code, message, details, retryAfter}
│   │   ├── rapprochements.ts  liste, lecture, création, exemple, point de situation, lien CSV
│   │   ├── systeme.ts         santé, paramétrage
│   │   └── questions.ts       question JSON et flux SSE (générateur asynchrone typé)
│   ├── sse.ts                 lecteur SSE sur response.body
│   ├── decimal.ts             format et tri des chaînes décimales, sans float
│   ├── dates.ts               dates ISO → français, « Date d'arrêté inconnue »
│   ├── files.ts               sources attendues, contrôles locaux, base64
│   ├── metier.ts              vocabulaire affiché : priorités, types courts, niveaux, couleurs de point
│   ├── storage.ts             localStorage en try/catch
│   └── utils.ts               cn()
├── hooks/                     hooks transverses : route par hash, raccourcis, navigation ↑ ↓,
│                              tri, compte à rebours, copie, toasts, données partagées (contextes)
├── components/
│   ├── ui/                    primitives shadcn (button, dropdown-menu, tooltip, tabs, command,
│   │                          kbd, skeleton), seuls les tokens sont adaptés
│   └── *.tsx                  composants partagés écrits une fois : StatusDot, Tag, Mono, Quantity,
│                              KpiRow, DataTable (+ DataTableHeader), FilterMenu, SearchInput,
│                              AttributeList, PageHeader, Section, EmptyState, ErrorNotice, ToastProvider
├── features/                  un dossier par fonctionnalité : ses composants, hooks et types
│   ├── triage/                Aujourd'hui : bandeau bloquant, synthèse, file groupée, anomalies
│   ├── files/                 dépôt (sélection, glisser-déposer, envoi), bande des 4 sources,
│   │                          fichiers reçus, bouton « Lancer sur les fichiers d'exemple »
│   ├── suspens/               vue Suspens, filtres, colonnes partagées avec la file, fiche, statut local
│   ├── situation/             point de situation, matrice fonds × conservateur
│   ├── journal/               journal de nettoyage (colonnes partagées avec la matinée)
│   ├── questions/             besoin 2 : flux, étapes, carte de réponse, historique de session
│   └── settings/              paramétrage en lecture seule
└── app/                       coquille : App (providers), Shell, Sidebar, Topbar, palette,
                               table des routes, provider des données de rapprochement
```

Pourquoi ce découpage :
- **`types/` séparé** : le contrat est la frontière avec le back ; une évolution de `docs/API.md` se reporte à un seul endroit, et le compilateur montre tout ce qui en dépend (ex. `date_arrete` devenu nullable).
- **`lib/` sans React** : formatage décimal, SSE, contrôles de fichiers et client HTTP sont des fonctions pures ou des modules sans état d'interface ; on les relit et on les teste sans navigateur.
- **`components/` vs `features/`** : un composant qui sert à deux fonctionnalités monte dans `components/` (la `DataTable` sert la file, les suspens, le journal, les fichiers, le paramétrage ; `StatusDot` partout). Ce qui ne sert qu'à une fonctionnalité reste dans son dossier : on supprime une fonctionnalité en supprimant un dossier.
- **Partage entre fonctionnalités par import explicite** : la file du matin réutilise les colonnes de `suspens/` et du `journal/`, la palette réutilise l'action de `files/` ; pas de copie.
- **État** : pas de librairie de state global. Trois contextes React (données de rapprochement, fiche ouverte, dépôt en cours), deux petits stores `useSyncExternalStore` (statuts locaux, historique de questions) ; la route est le hash de l'URL.
- **Règles** : composants courts (le plus long fait moins de 150 lignes), une responsabilité par fichier, props typées, pas de `any`, imports par alias `@/`, la logique (filtres, tri, groupes, matrice, formatage) dans des hooks ou dans `lib/`, pas dans le JSX.

## Limites connues

- Le statut À traiter / En cours / Traité est local au poste (`localStorage`) : deux opérateurs ne le partagent pas ; il faudrait une route du back.
- L'état « Refusé » d'un fichier est déduit du journal (BLOQUANT sur ce fichier) : le contrat n'a pas de statut par fichier.
- Le libellé court des types (« Absent conservateur »…) est fixé côté front ; le libellé officiel de TYPES_ECARTS reste affiché dans la fiche et le paramétrage.
- L'historique des questions vit le temps de l'onglet.
- Pas de tests de composants automatisés : la vérification est faite par typage strict, lint et un parcours piloté dans Chromium (captures, console, CSP).
