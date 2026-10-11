# Notes de cadrage : Orsay Gestion (arrêté du 25/09/2026)

## Le besoin en 5 lignes
1. **Client** : Orsay Gestion, une SGP agréée AMF, 3 FCP (PAT, OBL, ACT), 3 conservateurs (A = CACEIS, B = Euroclear, C = BNP/BP2S).
2. **Problème** : chaque matin, 1 h 30 de rapprochement manuel PMS ↔ conservateurs. Les suspens sont détectés tard, d'où des pénalités CSDR et une remontée au RCCI.
3. **Utilisateurs** : l'opérateur middle office (rapprochement), son responsable (point de situation) et, pour le besoin 2, les gérants et le RCCI (questions sur la base).
4. **Coût d'erreur** : un **faux négatif** (suspens raté) coûte des pénalités CSDR et pose un problème de conformité, c'est le pire cas. Un **faux positif** fait perdre du temps et entame la confiance dans l'outil. Côté besoin 2, un chiffre inventé crée un incident RCCI.
5. **Bonne réponse** : une liste exhaustive et exacte des suspens par fonds, ISIN et conservateur, avec leur type et l'action attendue (selon le paramétrage). Elle doit être traçable jusqu'aux lignes sources et exportable telle quelle pour le responsable.

## Règles appliquées (énoncé)
- La source est `positions_internes.csv`. `orsay.db` sert uniquement d'information (statut des mouvements, explication des écarts).
- La maille est (fonds, ISIN, conservateur). Les sous-comptes sont **agrégés** par fonds via TRANSCO_SOUS_COMPTES.
- Sont exclus : le sous-compte `P3G`, les lignes sans sous-compte (signalées comme anomalie de saisie, pas comme suspens) et les items C `ACTION=S`.
- Libellés des conservateurs : CACEIS → A, EUROCLEAR → B, BNP/BP2S → C (insensible à la casse).
- Tolérance nulle. Les quantités sont en `Decimal`.
- Un titre attendu chez X et trouvé chez Y donne **un seul** suspens `DEP`, pas un ABS_DEP plus un ABS_INT.

## Pièges repérés dans les données
- CSV : ISIN en minuscules avec espaces, libellés de conservateur hétérogènes, CRLF.
- A (xlsx) : 2 lignes de titre avant l'en-tête, quantités en texte avec séparateur de milliers (`"10 000"`), comptes en texte avec des zéros en tête.
- B (largeur fixe) : 2 décimales implicites. Contrôle `T000013` = 13 lignes de détail, à vérifier.
- C (XML) : namespace, `Dim prop=`, virgule décimale, plusieurs lots à sommer, annulation `S`, date JJMMAAAA, `NbItems` qui compte les annulations (9).
- Vérifier la date d'arrêté de chaque fichier (doit être le 25/09/2026).
- ISIN `FR0000012966` (« ISIN SAISI A LA MAIN ») : la clé de contrôle est invalide.

## Résultat attendu (calculé à la main, sert d'oracle de test)
| Fonds | ISIN | Cons. | Type | Détail |
|---|---|---|---|---|
| ACT | FR0000012965 SCHNEIDER | A | QTE | PMS 250 000 / A 225 000 → achat 25 000 EN_ATTENTE (dén. 26/09) |
| ACT | FR0000016297 SAFRAN | B | QTE | PMS 40 000 / B 41 000 → vente 1 000 EN_ATTENTE (dén. 29/09) |
| OBL | FR0000051641 SFIL 3% 2033 | C | QTE | PMS 100 000 / C 50 000, aucun mouvement ne l'explique |
| OBL | FR0000011488 EDF 4% 2031 | A | ABS_DEP | 40 000 absent chez A |
| OBL | FR0000012966 (ISIN invalide) | A | ABS_DEP | 7 000, ISIN à clé invalide, probable erreur de saisie |
| OBL | FR0000015927 AFD 3.5% 2035 | A→B | DEP | attendu chez A, livré chez B (250 000) |
| OBL | FR0000999914 LVMH 3.25% 2029 | B | ABS_INT | 30 000 chez B, absent du PMS |

Anomalies hors suspens : SANOFI 12 345 sans sous-compte (exclu), P3G BTF 999 999 (exclu), RTE lot 2 annulé (exclu).

## Besoin 2 : points d'attention
- Les obligations sont cotées en % du nominal, pied de coupon. Valo = nominal × cours / 100, **sans** multiplier par `valeur_nominale` (la quantité est déjà en nominal), et sans coupon couru. Actions : quantité × cours.
- `orsay.db` est ouverte en lecture seule (`mode=ro`) et seules des requêtes en liste blanche sont autorisées. Chaque chiffre est affiché avec sa requête et ses lignes sources.

## Hypothèses (consultant)
- Le rapprochement se fait à la date d'arrêté du 25/09. Un fichier daté autrement est bloqué, pas rapproché.
- L'explication « opération non dénouée » vient de `mouvements` (statut EN_ATTENTE), à titre informatif, sans changer le type de suspens.
- Je traite d'abord le besoin 1, à fiabilité maximale et sans LLM. Le besoin 2 vient ensuite, en version minimale.

## Décisions du 10/10 (après cadrage)
- Le besoin 1 passe en priorité. Le besoin 2 ne sera traité que s'il reste du temps.
- Le **nettoyage automatique** est un livrable à part entière : chaque transformation est tracée dans un **journal de nettoyage** (fichier, ligne, valeur brute, valeur retenue, règle, motif).
- Le nettoyage classe chaque anomalie en 4 niveaux :
  - `NORMALISE` : valeur corrigée sans changer son sens (casse et espaces d'un ISIN, `"10 000"` → 10000, décimales implicites, virgule décimale, libellé de conservateur → A/B/C).
  - `EXCLU` : ligne non pertinente, retirée en citant la règle client (P3G, sans sous-compte, annulation `S`).
  - `SIGNALE` : ligne conservée mais douteuse (clé ISIN invalide, ISIN absent du référentiel, libellés PMS et conservateur différents).
  - `BLOQUANT` : le fichier ne peut pas être rapproché (date d'arrêté ≠ 25/09, total de contrôle faux, compte ou sous-compte absent de la transco, quantité illisible, libellé de conservateur inconnu).
- Les fichiers sont transmis par le navigateur en base64 dans du JSON. Cela évite la dépendance `python-multipart`.

## Plan validé (10/10) : besoin 1 uniquement, le besoin 2 seulement s'il reste du temps
Chaîne : dépôt des fichiers → nettoyage par source (journal 4 niveaux) → agrégation (fonds, ISIN, conservateur) → rapprochement → suspens + piste `orsay.db` → page HTML + point de situation.

| # | Résultat vérifiable | Test | Durée | État |
|---|---|---|---|---|
| 1 | Bout en bout en ligne de commande : 4 parseurs + rapprochement, `uv run python -m reco data/donnees` affiche les 7 suspens | Test oracle = tableau « Résultat attendu » ci-dessus | 15 min | fait |
| 2 | Journal de nettoyage (NORMALISE / EXCLU / SIGNALE / BLOQUANT) et contrôles bloquants (date, T/NbItems, transco, 0 ligne lue) | Un test par piège, avec des fichiers altérés en mémoire | 12 min | fait |
| 3 | Page HTML + FastAPI : dépôt de fichiers en base64 ou bouton « fichiers du 25/09 », tableau des suspens filtrable, onglet journal | TestClient : POST → 7 suspens ; GET `/` → page | 12 min | à faire |
| 4 | Point de situation : synthèse par fonds et conservateur, suspens, actions, anomalies ; copier et export CSV | Le texte contient les 7 suspens et les 3 exclusions | 5 min | à faire |
| 5 | Mesure sur jeu étiqueté : 6 à 8 mutations, chacune avec son suspens attendu | Rappel 100 %, 0 faux positif, chiffres reportés dans le README | 6 min | à faire |
| 6 | README (lancement, choix, vérifié vs affirmé, manques) et relecture `reviewer` | pytest + ruff au vert, lancement à froid | 5 min | à faire |
| 7 | Répétition de la démo (10 dernières minutes) | Parcours joué de bout en bout | 10 min | à faire |

Un commit à chaque étape verte, au moins toutes les 15 minutes.

### Règles de rapprochement retenues
- On agrège le PMS (sous-compte → fonds via TRANSCO_SOUS_COMPTES) et les conservateurs (compte ou desk → fonds, lots C additionnés).
- Jointure complète sur (fonds, ISIN, conservateur). Si les deux quantités existent et diffèrent, c'est un `QTE`, même pour une seule unité.
- Un `ABS_DEP` chez X et un `ABS_INT` chez Y, pour le même fonds et le même ISIN, fusionnent en **un seul** `DEP`. Un écart de quantité éventuel est mentionné dans le libellé.
- La piste explicative vient d'un mouvement `EN_ATTENTE` de même fonds et ISIN dans `orsay.db` (lecture seule). Elle est informative et ne change pas le type du suspens.
- L'action attendue est lue dans TYPES_ECARTS, jamais codée en dur.

### Conservateur C : points de vigilance
- Namespace obligatoire : 0 Item lu donne BLOQUANT (sinon on aurait « 0 position » silencieusement).
- Lecture par `Dim[@prop]`. Un prop manquant donne BLOQUANT.
- `DateArrete` est au format JJMMAAAA.
- Le contrôle `NbItems` se fait sur **tous** les Item, annulations comprises, avant filtrage.
- `S` donne EXCLU. On ne le soustrait **pas** (RTE : 25 000 et non 15 000).
- Les lots sont additionnés par (compte, ISIN) : HERMES 10 000 + 15 000 = 25 000.

### Choix structurants et alternatives écartées
- Rapprochement en Python déterministe plutôt qu'avec un LLM : la règle est exacte, un LLM n'apporte qu'un risque de faux négatif.
- Bibliothèque standard + openpyxl plutôt que pandas : pandas inférerait des types (zéros en tête, float), alors qu'on veut du `Decimal` de bout en bout.
- Upload en base64 dans du JSON plutôt que python-multipart : pas de dépendance ajoutée.
- HTML et JS natifs servis par FastAPI plutôt que React ou Streamlit : rien à compiler, lancement en une commande.
- BLOQUANT signifie que le fichier est refusé, pas rapproché partiellement : un rapprochement partiel rend des faux négatifs invisibles.
- Pas de LLM dans le besoin 1 : l'ambigu (ISIN invalide) est signalé à un humain, pas deviné.
- Paquet `reco/` à la racine plutôt que `src/reco/` : `python -m reco` fonctionne sans packaging (`pythonpath = ["."]` pour pytest).
- Code fonds (PAT/OBL/ACT) lu dans `orsay.db.portefeuilles` (nom d'entité → code) plutôt que codé en dur : la transco ne donne que le nom d'entité.
- Le rapprochement prend `{nom de fichier: octets}` : la même fonction sert la ligne de commande et, plus tard, l'API (base64 → octets).
- Une anomalie BLOQUANT sur n'importe quel fichier donne le statut `BLOQUE` et 0 suspens (pas de rapprochement des seules sources saines) : sinon, de faux ABS_DEP apparaissent, ou de vrais suspens disparaissent.
- Une exception imprévue dans un parseur devient BLOQUANT `FORMAT_ILLISIBLE` : on refuse le fichier, on ne devine pas.
- Contrôles ISIN (clé de Luhn, présence dans `titres`) et libellés divergents faits après la lecture, dans le rapprochement, parce qu'ils ont besoin de `orsay.db`. Libellé de repli lu dans `titres` (B n'a pas de libellé).

## Revue étape 1 (10/10, avec challenge)
- **DEP avec écart de quantité** : un seul suspens DEP (énoncé : « un seul suspens, pas deux »), avec un champ `écart` (PMS − conservateur) et l'action QTE ajoutée en complément. Alternative écartée : DEP + QTE, qui compte deux suspens pour un problème et pose un QTE sans clé commune (A côté PMS, B côté conservateur).
- **DEP ambigu** (1 absent, plusieurs trouvés, ou l'inverse) : on garde les suspens séparés et on signale « DEP ambigu » sur chacun. On ne devine pas, l'opérateur tranche.
- **orsay.db facultative** : la clé fonds est le nom d'entité de `parametrage.xlsx` (la référence) ; la base ne fournit que le code court, le référentiel et la piste. Sans base : suspens produits + SIGNALE `BASE_INDISPONIBLE`. Raison : l'énoncé dit « à ne pas utiliser comme source du rapprochement », et une base absente ne doit pas arrêter le contrôle.
- **Piste** : cite le n° d'opération et calcule si le net signé (achats − ventes en attente) explique l'écart : entièrement, partiellement (« reste X ») ou pas du tout. « Explication possible seulement » si le fonds détient le titre chez plusieurs conservateurs, puisque `mouvements` n'a pas de colonne conservateur.
- **Oublis ajoutés** : opération EN_ATTENTE dont la date de dénouement est passée → SIGNALE `DENOUEMENT_DEPASSE` (risque CSDR) ; position nulle = absence (pas d'ABS_DEP pour 0 titre) ; ligne en double chez PMS, A ou B → additionnée mais SIGNALE `DOUBLON` (durci ensuite en BLOQUANT, voir « Revue de code finale ») ; deux fichiers pour une même source → BLOQUANT `FICHIERS_MULTIPLES`.
- **Limites non traitées** : unités (nominal vs nombre de titres selon le conservateur), titre trouvé dans un *autre fonds* (probable erreur de transco, 2 suspens non fusionnés), ancienneté des suspens d'un jour sur l'autre.

## Revue étape 2 (10/10)
- **Une donnée ne sort pas de nulle part et ne disparaît pas sans trace** : une ligne vraiment vide est ignorée ; une ligne partiellement remplie (A : compte, ISIN ou quantité vide ; PMS : ISIN vide ; C : Dim vide) ou d'un type inconnu (B : ni H, ni D, ni T) → BLOQUANT. Avant, A et B jetaient ces lignes sans rien dire, d'où des faux négatifs invisibles.
- **ACTION inconnue chez C** → SIGNALE, et l'item est **additionné** : une erreur ressort alors en QTE visible (faux positif), au lieu d'un suspens caché (faux négatif, le pire cas).
- **Quantité suspecte** → SIGNALE : négative, non entière, ou texte brut avec un séparateur suivi de 3 chiffres (« 10.000 » se lit 10). Piège trouvé par le test : `Decimal("10.000")` est entier, donc le contrôle doit porter sur le texte brut, pas sur la valeur.
- **Paramétrage contrôlé** : feuille absente, code absent de TYPES_ECARTS ou transco contradictoire (même clé, deux fonds) → BLOQUANT `PARAMETRAGE`. Avant, le programme plantait, ou le dernier fonds lu gagnait en silence.
- **Blocage total mais actionnable** : tout BLOQUANT porte un `remede` (« Ajouter « SC-XXX-01 » à la table TRANSCO_SOUS_COMPTES… »). Alternative écartée : blocage par fonds. Un sous-compte inconnu, c'est un fonds inconnu, donc aucun fonds n'est garanti.
- Traces ajoutées : décodage latin-1 (NORMALISE `ENCODAGE`), colonnes CSV absentes (BLOQUANT `FORMAT` lisible, au lieu d'un `KeyError`).
- Limites acceptées (revue étape 2) : le motif `\d[.,]\d{3}$` signale à tort un nominal légitime noté « 2.500 » (faux positif accepté) ; les remèdes des BLOQUANT sont rédigés par nous et **à valider avec le middle office d'Orsay** (procédure réelle de relance d'un conservateur).

## Étape 3 : choix
- Rate limit maison (fenêtre glissante en mémoire, par IP) plutôt que `slowapi` : aucune dépendance ajoutée ; suffisant pour un process unique (limite : non partagé entre plusieurs workers).
- Contrat d'API écrit d'abord (`docs/API.md`), puis back et front développés en parallèle par deux sous-agents à partir de ce contrat.
- Export CSV et point de situation exposés dès l'étape 3 (une partie de l'étape 4 avancée), car le front en a besoin.
- Front prêt pour le besoin 2 : la vue « Questions sur la base » et la route `POST /api/questions` (501 pour l'instant) sont réservées, avec le format de réponse (chiffre + requête + lignes sources) déjà défini.
- **Architecture en 3 couches** (refactor du 10/10, demandé après lecture d'un `api.py` de 650 lignes) : `reco/domaine/` (métier pur : sources, rapprochement, situation ; aucun HTTP), `reco/api/` (HTTP : `config`, `schemas`, `erreurs`, `limiteur`, `middleware`, `services/`, `routes/`, `app.py` qui assemble, dépendances injectées via `app.state` et `Depends`), `reco/web/` (front). Le besoin 2 s'y branchera en `domaine/questions` + `api/routes/questions.py`. Refactor sans changement de comportement : les 95 tests passent sans modification (seul le chemin d'un monkeypatch change).
- Limite citée : les noms des conservateurs (CACEIS, Euroclear, BNP Paribas) sont codés en dur dans `api/services/referentiel.py`, car ni le paramétrage ni la base ne les portent.

## Besoin 2 : décisions du 10/10
- **Q1 : catalogue de requêtes en liste blanche.** Le LLM ne fait que comprendre la question (intention parmi le catalogue + paramètres), et sa sortie est validée par pydantic. Le SQL est écrit et testé par nous, les chiffres sont calculés en `Decimal`, **la phrase de réponse est un gabarit**. Le LLM ne peut donc inventer aucun chiffre. Alternative écartée : le text-to-SQL (couverture plus large, mais un risque de chiffre faux, c'est-à-dire un incident RCCI). Une question hors catalogue reçoit « je ne sais pas répondre » et la liste de ce que l'outil sait faire.
- **Q2 : Claude Haiku 5.5** pour la compréhension (sortie JSON forcée), avec un **repli par mots-clés sans LLM** si l'API ne répond pas ou si la clé est absente.
- **Q3 : date de référence = date d'arrêté (25/09/2026)**, affichée dans chaque réponse.
- **Q4 : horizon des échéances de 12 mois par défaut**, modifiable dans la question. **Question ouverte à poser au client** : quel horizon les gérants utilisent-ils vraiment (3 mois de trésorerie ? 12 mois glissants ?).
- **Q5 : sous le seuil de confiance, aucune réponse chiffrée.** On affiche un message « Attention » et 2 ou 3 reformulations proposées.
- Garanties de lecture seule (« personne ne doit pouvoir modifier l'inventaire ») en 3 couches : `mode=ro`, `PRAGMA query_only = ON`, et un autorisateur SQLite qui refuse tout ce qui n'est pas une lecture.
- Revue 2.1 : **total partiel accepté s'il est bien étiqueté** (« partiel », confiance basse, lignes non valorisées citées). L'encours suit la **vue PMS** (date de négociation, opérations non dénouées incluses), et un avertissement le signale.
- Étape 2.2 : échéances (horizon 12 mois par défaut, borne affichée ; montant = nominal au pair), concentration par émetteur (par fonds uniquement, en % de l'encours valorisé, **sans jugement réglementaire 5/10/40**), opérations non dénouées (montant obligataire = nominal × prix / 100 ; date prévue dépassée → risque CSDR), origine d'un suspens (pont avec le besoin 1 : suspens du dernier rapprochement + lignes sources + mouvements du titre). Oracles à la main : 2 tombées pour 45 000 de nominal ; AFD 33,46 % d'OBL ; Kering 87,54 % de PAT ; ops n°19 (10 948 000,00) et n°20 (217 730,00).
- Revue 2.2 (validée) : montant obligataire = nominal × prix / 100 ; concentration fonds par fonds (sans fonds : on demande de préciser) ; statut EN_ATTENTE lu dans la base, avec un avertissement.
- **Règles de vigilance** (`reco/domaine/questions/vigilance.py`) : seuils internes simples, rassemblés au même endroit, modifiables et présentables dans l'outil. Par défaut : un émetteur > 10 % de l'encours ; cumul des émetteurs > 5 % au-delà de 40 % (inspiré du 5/10/40 mais **sans verdict réglementaire** : pas de dérogation pour les émetteurs publics, libellé « seuil de vigilance interne »). Le cumul se calcule sur les montants exacts : additionner les pourcentages arrondis donne 89,35 % au lieu de 89,34 % pour OBL. Évolution possible : seuils lus dans le paramétrage client et édités depuis l'outil.
- Revue 2.2 : les 4 points ont été validés par l'utilisateur.
- **Étape 2.3 (compréhension)** : `client.messages.parse(model="claude-haiku-5-5", output_format=IntentionLLM)`. Le LLM ne reçoit **que la question et la date de référence**, jamais de données de la base ; il renvoie une intention typée (pydantic). Repli par mots-clés si pas de client, erreur de connexion, 429, 5xx, refus ou sortie non conforme (la raison est tracée dans `comprehension.detail`). Chaque réponse porte la question et la compréhension retenue (intention, paramètres, source, confiance).
- **Essai réel avec Haiku 5.5** (7 questions formulées comme un jury, hors des mots-clés), qui a révélé 4 défauts invisibles avec des faux clients : (1) « d'ici la fin de l'année » se résolvait sur 12 mois → la date de référence est maintenant dans le prompt, ce qui donne 4 mois et seulement le BTF du 17/12 ; (2) « Supprime la position LVMH » recevait « pas compris » → message explicite « outil en lecture seule » ; (3) une question hors catalogue mais bien comprise (« performance YTD ») recevait aussi « pas compris » → « je ne sais pas calculer ça de façon fiable », testé avant la confiance ; (4) le LLM proposait des reformulations hors catalogue → chaque reformulation est revérifiée de façon déterministe par les mots-clés avant d'être proposée.
- Limite : seuil de confiance fixé à 0,7 sur la confiance auto-déclarée par le LLM, signal faible. « Pourquoi Schneider ne tombe pas juste ? » est bloqué (0,6) avec une bonne reformulation. À calibrer sur un jeu de questions réelles des gérants (eval).
- **Étape 2.4 (branchement)** : `POST /api/questions` (JSON) et `POST /api/questions/flux` (SSE). Le flux porte sur les **étapes** (analyse → intention → calcul → réponse) et non sur du texte de LLM, puisque la réponse est un gabarit. Encadrement de la clé dans un seul fichier (`api/services/llm.py`, `ClientEncadre`) : modèle imposé, budget de 300 appels/jour, 4 appels simultanés, timeout de 10 s, 1 nouvelle tentative, cache des questions identiques, interrupteur `RECO_LLM_ACTIF=0`, consommation journalisée (jetons, durée, compteur), jamais la clé ni la question. Toute limite atteinte → repli par mots-clés, sans erreur pour l'utilisateur. Rate limit dédié de 10 questions/min/IP. `conftest.py` coupe le LLM pour toute la suite de tests. Essai réel : 11 questions → 2 appels LLM (cache), 429 à la 11ᵉ, premier événement SSE immédiat, LLM ≈ 2 à 3 s, calcul < 5 ms, aucune trace de la clé dans les logs. Limite : compteurs en mémoire (process unique, remis à zéro au redémarrage).
- **Date d'arrêté lue dans les données** (plus de constante `DATE_ARRETE`) : rapprochement = date unique du PMS, que les 3 conservateurs doivent porter ; PMS absent ou multi-dates → BLOQUE avec `date_arrete = null` ; réglage `date_arrete_attendue` (production : J-1 ouvré) pour refuser les fichiers périmés. Questions : date de référence = dernières positions de `orsay.db` (503 `BASE_INDISPONIBLE` si illisible). Démonstration « demain matin » : les mêmes fichiers datés du 26/09 font passer SCHNEIDER en **critique** (op. n°19, dénouement prévu le 26/09, toujours EN_ATTENTE : risque CSDR).
- Revue du découpage du back (10/10), défauts restants assumés : le domaine importe le SDK Anthropic (un port « classifieur » serait plus propre) ; les gabarits de phrases sont mêlés aux requêtes dans `catalogue.py`.
- **Renommage `reco` → `middle_office`** (10/10) : le paquet porte désormais les deux besoins ; `reco` ne décrivait que le rapprochement. Le domaine devient symétrique : `domaine/rapprochement/` (sources, moteur, situation) et `domaine/questions/`. Écartés : `orsay` (lie le code au client), `backend` (ne dit rien du métier). Commandes : `uv run uvicorn middle_office.api:app`, `uv run python -m middle_office data/donnees`.
- **Nettoyage du dépôt** : exports de session rangés dans `docs/sessions/`, `visualisation/` → `exploration/` (CSV générés hors git), 6 dépendances inutilisées retirées (langgraph, langchain-anthropic, pdfplumber, rapidfuzz, rank-bm25 ; pandas dans le groupe `exploration`), `httpx` dans le groupe `dev`. Clone neuf vérifié : `uv sync` puis 186 tests verts, sans `.env`.
- **Front React livré** (sous-agent, vérifié par moi) : typage, lint (0 avertissement) et format verts, build reproductible, CSP inchangée (sans `'unsafe-inline'`, les composants Radix qui injectent des `<style>` sont évités), aucun fichier source au-delà de 150 lignes hors types. Commité en couches (outillage, fondations, composants, coquille, une fonctionnalité par commit, build seul) : l'ancienne page HTML est supprimée. La CI vérifie que le build commité correspond aux sources.
- **Clé API révoquée** (401 constaté le 10/10 au soir, comme l'énoncé le prévoyait) : l'outil bascule sur les mots-clés et trace la raison (`LLM indisponible (HTTP 401)`) ; l'essai réel avec Haiku avait été fait avant, quand la clé était active. Variable `RECO_LLM_ACTIF` renommée `LLM_ACTIF`.

## Revue de code finale (10/10, avant livraison)
Relecture complète, chaque défaut reproduit par un script avant d'être corrigé (test rouge, puis vert).
- **Doublons et ACTION inconnue : BLOQUANT** (étaient additionnés et seulement SIGNALE). Reproduit : un LOT SFIL dupliqué chez C, ou un item `ACTION=X`, portait C à 100 000 = PMS et **le suspens SFIL disparaissait** (aucune trace pour le LOT, qui n'était pas lu). Le même risque valait pour une ligne en double chez PMS, A ou B. Désormais : `LOT` est obligatoire et (compte, ISIN, lot) unique chez C ; (compte, ISIN) unique ailleurs ; une ACTION autre que C/S refuse le fichier. Garder une seule ligne aurait été deviner ; additionner peut masquer un écart.
- **Origine d'un suspens après un rapprochement bloqué** : la question lisait le rapprochement le plus récent, même `BLOQUE` (donc sans suspens), et répondait « Aucun suspens sur FR0000051641 » (reproduit). Elle lit désormais le dernier rapprochement `OK` (requête `LIMIT 1`, au lieu de désérialiser les 20 derniers), cite sa date d'arrêté, et signale en confiance basse un rapprochement plus récent bloqué. Au passage : les mouvements d'un ISIN en suspens dans deux fonds sont cités pour les deux, plus pour le premier seul.
- **Alertes structurées jusqu'au front** : le back décidait déjà la priorité sur des codes, mais l'API n'exposait que le texte des signalements, et le front redétectait le CSDR par regex (`isCsdr`). Un signalement est maintenant un couple `{code, message}` ; `alertes` (codes) et `explication` sont exposés ; `isCsdr` est supprimé. Côté domaine, `alertes` est dérivé des signalements : les deux ne peuvent plus diverger.
- **Absences entièrement expliquées → en attente** : un `ABS_DEP` dont l'`explication` est `totale` (achat d'une ligne nouvelle, non dénoué : le cas le plus courant d'écart temporaire) restait « à relever », car seul `QTE` était explicable. Reproduit avec un achat EDF en attente. `ABS_DEP` et `ABS_INT` suivent maintenant la règle du `QTE` ; `DEP` reste à relever (un mauvais conservateur n'est jamais expliqué par une opération).
- **Export CSV : formules neutralisées** : un libellé `=1+2` venu d'un fichier déposé ressortait tel quel et Excel l'exécutait (reproduit). Les cellules texte commençant par `= + - @` (ou tabulation, retour chariot) sont préfixées d'une apostrophe ; les colonnes de quantités ne le sont pas, un écart négatif reste un nombre.
- **Reconnaissance des fichiers unique et insensible à la casse** (`source_du_fichier`) : le front acceptait `Depositaire_A…`, le back répondait 422 (reproduit). Dépôt, exemple et CLI passent par la même fonction que la règle du front.
- **Exceptions de lecture resserrées** (`ERREURS_DE_FORMAT`) : un `except Exception` transformait aussi nos propres bugs en « FORMAT_ILLISIBLE : redéposez le fichier », et l'opérateur aurait redéposé en boucle. On n'attrape plus que ce qu'un fichier mal formé lève (relevé sur des fichiers vides, binaires, tronqués, UTF-16, zip non classeur) ; le reste remonte en 500 tracé avec l'identifiant de requête. Classeurs openpyxl fermés après lecture (en `read_only`, le fichier restait ouvert). Paramétrage : un libellé ou une action attendue vide bloque (plantait plus loin).
- **Garde-fou des fichiers périmés activable** : le réglage `date_arrete_attendue` existait mais rien ne le renseignait, donc des fichiers d'avant-hier, cohérents entre eux, passaient sans alerte. Variable `DATE_ARRETE_ATTENDUE` (`auto` = J-1 ouvré TARGET2, recalculé à chaque dépôt ; ou une date fixe ; vide par défaut pour la démo). Valeur invalide : le serveur refuse de démarrer. `.env` est maintenant chargé avant les réglages (il ne l'était que pour le LLM) ; les tests neutralisent la variable.
- **Décision du LLM tracée côté serveur** : la seule ligne qui journalisait l'intention comprise était dans `repondre()`, que seuls les tests appelaient ; les deux routes dupliquaient compréhension et exécution sans rien tracer (règle « sortie justifiée et tracée » non tenue). Un service unique (`services/questions.py`) sert la route JSON et le flux SSE, et écrit une ligne `audit question` par question : identifiant de requête, empreinte SHA-256 de la question (jamais le texte), intention, source (llm ou mots-clés), confiance, paramètres, confiance de la réponse, nombre de chiffres, raison d'un repli.
- **Besoin 2 : ne jamais répondre à côté** (reproduit : « Encours de LVMH » → total des 3 fonds ; « au 01/01/2025 » → encours du 25/09 ; « suspens sur SFIL » → titre non reconnu). Titres reconnus par alias en mots entiers (libellé, libellé sans coupon ni échéance, émetteur), ambiguïté signalée avec une reformulation par candidat ; date citée (explicite ou relative) lue de façon déterministe et demandée au LLM (`date_demandee`), refusée si elle diffère de la date de référence ; encours d'un titre seul refusé ; échéances et opérations non dénouées filtrées par titre, sans borne de fin pour un titre sans horizon (EDF tombe en 2031) ; « d'ici le 31/12 » utilisé tel quel (un arrondi au mois inclurait des tombées non demandées). Incohérence corrigée au passage : un ordre d'écriture (« Corrige l'encours d'OBL ») n'était refusé que hors catalogue, il recevait donc l'encours.
- **Doublons supprimés** : formats d'affichage réunis dans `domaine/formats.py` (`formater_quantite`, `montant`, `pourcentage`, `date_fr`, `CENTIME` existaient en double, parfois sous deux noms) ; accès à `orsay.db` réuni dans `domaine/base_gestion.py` (déplacé de `questions/`), que le rapprochement et le référentiel utilisent aussi, et qui leur apporte l'autorisateur de lecture seule ; version lue dans `pyproject.toml` seul (elle était écrite à trois endroits) ; paramètre `ClientEncadre.timeout` jamais utilisé retiré ; paquet front renommé `middle-office-front` (restait `reco-front`).
- **Formateur respecté partout** : 135 `# fmt: skip` contournaient `ruff format` (lignes jusqu'à 160 colonnes) et E501 était ignoré. Tous retirés ; le formateur coupe à 100, E501 est actif avec une limite dure à 120 pour les chaînes et commentaires qu'il ne coupe pas.
- **Typage statique (pyright, mode standard) sur le code et les tests**, dans `make lint` et la CI. Il a trouvé 17 erreurs, corrigées sans `type: ignore`, dont une vraie : dans `operations_non_denouees`, la variable de boucle `isin` masquait le nouveau paramètre `isin`. Les autres : `None` possibles non traités (`decimal`, `quantite_texte` surchargés ; date d'arrêté garantie par une assertion commentée une fois les blocages écartés).
- **Statut de traitement partagé et tracé** : il ne vivait que dans le `localStorage` du navigateur (le responsable ne voyait pas ce qui était traité, rien n'était auditable, et la clé utilisait le code fonds, vide sans `orsay.db`). Il est stocké dans `historique.db` avec une clé stable (date, entité, ISIN, conservateur, type) et un journal des changements (identifiant de requête) ; routes `GET …/statuts` et `PUT …/suspens/{sid}/statut` ; le front garde une mise à jour optimiste, annulée avec un toast en cas de refus. Limite : pas d'authentification, donc « qui » est un identifiant de requête, pas une personne.
- **Une question finit toujours** : une question remplacée par une nouvelle restait « en cours » pour toujours dans le rail (l'abandon fait sortir la boucle SSE sans exception), de même qu'un flux coupé sans événement `reponse` ni `erreur`. Elles passent en « Annulée » ou « Interrompue ».
- **Tests du front (vitest)** : 21 tests sur la logique pure, dont des cas qui comptent ici : décimaux sans flottant (grand nombre, jamais « −0 », tri exact), événement SSE coupé entre deux paquets au milieu d'un caractère accentué, reconnaissance des fichiers insensible à la casse comme le back, état des fichiers reçus calculé sur la vraie réponse du back (`docs/exemple_rapprochement.json`, qui sert donc aussi de test de contrat avec les types TypeScript). Dans `make front-check` et la CI. Les caractères invisibles de `decimal.ts` (espace fine, signe moins) sont maintenant écrits en échappements.
