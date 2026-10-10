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
- **Oublis ajoutés** : opération EN_ATTENTE dont la date de dénouement est passée → SIGNALE `DENOUEMENT_DEPASSE` (risque CSDR) ; position nulle = absence (pas d'ABS_DEP pour 0 titre) ; ligne en double chez PMS, A ou B → additionnée mais SIGNALE `DOUBLON` ; deux fichiers pour une même source → BLOQUANT `FICHIERS_MULTIPLES`.
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
