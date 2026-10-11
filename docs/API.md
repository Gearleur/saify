# Contrat d'API : rapprochement Orsay Gestion

Source de vérité partagée entre le back (`middle_office/api/`) et le front (sources React dans `front/`, build servi depuis `middle_office/web/`).
Toute évolution du contrat passe par ce fichier d'abord.

Lancement : `uv run uvicorn middle_office.api:app --reload` puis http://127.0.0.1:8000

## Conventions
- JSON en UTF-8, champs en français, `snake_case`.
- **Quantités et écarts : chaînes décimales** (`"250000"`, `"-1000"`, `"5000.5"`), jamais des nombres JSON : on ne repasse pas par `float`. `null` = absent de ce côté.
- Dates : ISO `YYYY-MM-DD` ; horodatages : ISO 8601 UTC (`2026-10-10T14:03:22Z`).
- Toute erreur renvoie `{"erreur": {"code": "...", "message": "...", "details": ...}}` avec le statut HTTP adapté. Jamais de trace Python.
- Chaque réponse porte un en-tête `X-Request-ID` (repris de la requête s'il est fourni, sinon généré).

## Garde-fous
| Garde-fou | Valeur | Réponse si dépassé |
|---|---|---|
| Rate limit `POST` | 20 requêtes / minute / IP | `429 RATE_LIMIT` + en-tête `Retry-After` (secondes) |
| Rate limit `GET` | 120 requêtes / minute / IP | idem |
| Rate limit questions (`POST /api/questions*`) | 10 requêtes / minute / IP, quota à part | idem |
| Usage du LLM (clé API) | modèle imposé `claude-haiku-5-5`, 300 appels réels / jour, 4 simultanés, timeout 10 s, 1 nouvelle tentative, cache des questions identiques, interrupteur `LLM_ACTIF=0` | **pas d'erreur** : repli par mots-clés, raison dans `comprehension.detail` |
| Question | 3 à 500 caractères, caractères de contrôle retirés, champs inconnus refusés | `422 VALIDATION` |
| Taille du corps | 15 Mo | `413 CORPS_TROP_GROS` |
| Taille d'un fichier décodé | 5 Mo | `413 FICHIER_TROP_GROS` |
| Nombre de fichiers | 1 à 8 | `422 VALIDATION` |
| Nom de fichier | nom de base seul (pas de `/`, `\`, `..`), extensions `.csv .xlsx .txt .xml` | `422 VALIDATION` |
| Base64 | décodage strict | `422 VALIDATION` |
| Source non reconnue | préfixes `positions_internes`, `depositaire_A`, `depositaire_B`, `depositaire_C` | `422 FICHIER_NON_RECONNU` (le message liste les préfixes attendus) |
| XML | refus de `<!DOCTYPE` / `<!ENTITY>` (entités externes, billion laughs) | rapprochement `BLOQUE`, règle `FORMAT` |
| `orsay.db` | ouverte en lecture seule (`mode=ro`) | — |
| En-têtes de sécurité | CSP stricte : `default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'` (donc **ni script inline, ni `<style>` inline, ni attribut `style=""`, ni `onclick=`** côté front), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` | — |
| Historique persistant | SQLite séparé `var/historique.db` (hors git : positions du client), jamais `orsay.db` ; réponse JSON, CSV et point de situation figés à la création | `GET /api/rapprochements` liste les 20 plus récents ; `GET /api/rapprochements/{id}` (et ses exports) relit tout l'historique, sans suppression automatique |

Un fichier refusé par le *métier* (date, total de contrôle…) n'est **pas** une erreur HTTP : la réponse est `200` avec `statut: "BLOQUE"` et le journal explique quoi faire (`remede`).

Autres codes : `503 BASE_INDISPONIBLE` (questions, base de gestion illisible), `404 INTROUVABLE`, `405 METHODE_NON_AUTORISEE`, `503 PARAMETRAGE_INDISPONIBLE` (`/api/parametrage` si `parametrage.xlsx` est illisible), `503 PAGE_INDISPONIBLE` (`GET /` sans `index.html`), `500 ERREUR_INTERNE` (sans trace). Swagger (`/docs`) est désactivé : incompatible avec la CSP stricte.

## Routes

### `GET /` → la page HTML (`middle_office/web/index.html`)
### `GET /static/assets/…` → fichiers du build (`middle_office/web/assets/`, noms hachés par Vite)

### `GET /api/sante`
`date_arrete` : date de référence de la **base de gestion** (dernières positions de `orsay.db`), `null` si illisible. C'est la date des réponses aux questions et celle des fichiers d'exemple.
```json
{"statut": "ok", "version": "0.3.0", "date_arrete": "2026-09-25", "base_disponible": true,
 "llm": {"actif": true, "modele": "claude-haiku-5-5", "appels_aujourdhui": 2, "budget_jour": 300}}
```

### `GET /api/parametrage`
Référentiel pour les filtres et la vue Paramétrage (lecture seule).
```json
{
  "date_arrete": "2026-09-25",
  "fonds": [{"entite": "ORSAY OBLIGATIONS", "code": "OBL"}],
  "conservateurs": [{"code": "A", "nom": "CACEIS"}, {"code": "B", "nom": "Euroclear"}, {"code": "C", "nom": "BNP Paribas (BP2S)"}],
  "types_ecarts": [{"code": "QTE", "libelle": "Quantité différente", "action_attendue": "Vérifier les opérations de la veille non dénouées"}],
  "transcos": {"TRANSCO_SOUS_COMPTES": [{"cle": "SC-PAT-01", "entite": "ORSAY PATRIMOINE"}], "TRANSCO_DEPOSITAIRE_A": [], "TRANSCO_DEPOSITAIRE_B": [], "TRANSCO_DEPOSITAIRE_C": []},
  "exclusions": ["Sous-compte P3G (compte technique de passage)", "Ligne sans sous-compte (saisie incomplète)", "Item conservateur C annulé (ACTION=S)"]
}
```

### `POST /api/rapprochements`
Corps :
```json
{"fichiers": [{"nom": "positions_internes.csv", "contenu_b64": "ZGF0ZV9h..."}]}
```
→ `201` + objet **Rapprochement** (ci-dessous) si `statut = "OK"` ; `200` si `statut = "BLOQUE"` (le rapprochement est quand même enregistré dans l'historique).

### `POST /api/rapprochements/exemple`
Rapproche les fichiers du 25/09 fournis (`data/donnees`). Pas de corps. → `201` (ou `200` si BLOQUE) + **Rapprochement**.

### `GET /api/rapprochements` → `[RapprochementResume]`, le plus récent d'abord
```json
[{"id": "r_8f3a2c", "cree_le": "2026-10-10T14:03:22Z", "date_arrete": "2026-09-25", "statut": "OK", "nb_suspens": 7, "nb_a_traiter": 5}]
```

### `GET /api/rapprochements/{id}` → **Rapprochement** · `404 INTROUVABLE`

### `GET /api/rapprochements/{id}/suspens.csv`
CSV `;`, UTF-8 avec BOM (ouverture directe dans Excel), quantités en texte. Colonnes :
`priorite;fonds;entite;isin;titre;conservateur;type;libelle_type;qte_pms;qte_conservateur;ecart;action;piste;signalements;sources`.
En-tête `Content-Disposition: attachment; filename="suspens_2026-09-25.csv"`.

### `GET /api/rapprochements/{id}/point-de-situation`
```json
{"texte": "Point de situation · rapprochement du 25/09/2026\n..."}
```
Texte brut, prêt à coller dans un mail : statut, synthèse par fonds et conservateur, suspens par priorité avec action attendue, exclusions et signalements.

### `POST /api/questions` (besoin 2)
Corps `{"question": "Combien pèse le fonds obligataire ?"}` → `200` + **ReponseQuestion**.
Le LLM (Haiku 5.5) ne fait que **classer** la question dans le catalogue (encours, échéances, concentration,
opérations non dénouées, origine d'un suspens) ; il ne reçoit aucune donnée de la base. Les chiffres viennent
de requêtes SQL fixes, en lecture seule, calculées en `Decimal` ; la phrase est un gabarit.
**Jamais de réponse à côté** (un vrai chiffre, mais d'une autre question) : une demande d'écriture formulée comme un ordre, une autre date que la date de référence pour un encours, une concentration ou des opérations (`comprehension.date_demandee`), l'encours d'un titre seul, ou un titre ambigu (« l'OAT » : 4 titres) donnent un « Attention » sans chiffre et des reformulations. Un titre est reconnu par son ISIN, son libellé, son nom court (« SFIL ») ou son émetteur ; les échéances et les opérations non dénouées se filtrent sur lui (paramètre SQL `isin`). « D'ici le 31/12/2026 » borne les échéances à cette date exacte.
« Origine d'un suspens » répond sur le **dernier rapprochement `OK`**, cité avec sa date d'arrêté. Si un rapprochement plus récent est bloqué, la réponse le signale dans `avertissements` et passe en `confiance: "basse"` (elle ne dit jamais « aucun suspens » sur la foi d'un rapprochement bloqué).
```json
{
  "question": "Combien pèse le fonds obligataire ?",
  "reponse": "L'encours valorisé d'ORSAY OBLIGATIONS au 25/09/2026 est de 724 836,00 EUR (10 lignes valorisées au cours de clôture du 25/09/2026).",
  "chiffres": [{"libelle": "Encours valorisé", "valeur": "724836.00", "unite": "EUR"}],
  "requete_sql": "SELECT p.portefeuille, f.nom, p.isin, ... WHERE p.date_arrete = :date AND (:fonds IS NULL OR p.portefeuille = :fonds) ...",
  "parametres_sql": {"date": "2026-09-25", "fonds": "OBL"},
  "lignes_sources": [{"table": "positions × titres × cours", "valeurs": {"isin": "FR0000015927", "quantite": "250000", "cours": "97.0", "valorisation": "242500.00"}}],
  "confiance": "haute",
  "avertissements": ["Obligations valorisées au pied de coupon (cours en % du nominal), sans coupon couru."],
  "vigilances": [],
  "reformulations": [],
  "comprehension": {"intention": "ENCOURS", "fonds": "OBL", "horizon_mois": null, "isin": null, "source": "llm", "confiance": 0.95, "detail": ""}
}
```
- `vigilances` (concentration uniquement) : `[{"code": "EMETTEUR_AU_DESSUS_DU_SEUIL", "message": "...", "emetteurs": ["Kering"], "valeur": "87.54"}]`, seuils **internes** (10 % par émetteur ; cumul des > 5 % au-delà de 40 %), jamais un verdict réglementaire.
- Pas de réponse sûre (confiance < 0,7, hors catalogue, fonds ou titre manquant, demande d'écriture) : `reponse` commence par **« Attention : »**, `chiffres = []`, `confiance = "basse"`, et `reformulations` propose 2 ou 3 questions qui mènent au catalogue.
- `requete_sql` + `parametres_sql` : la requête exacte exécutée, rejouable telle quelle.

### `POST /api/questions/flux` (même corps, réponse en flux SSE)
`Content-Type: text/event-stream`. L'entrée est validée **avant** l'ouverture du flux (422 normal). Événements, dans l'ordre :
```
event: etape          data: {"etape": "comprehension", "message": "Analyse de la question…"}
event: comprehension  data: {"intention": "ENCOURS", "fonds": "OBL", ..., "source": "llm"}
event: etape          data: {"etape": "calcul", "message": "Requête en lecture seule sur la base de gestion…"}
event: reponse        data: <ReponseQuestion, identique à la route JSON>
event: fin            data: {}
```
En cas de panne : `event: erreur` (`{"code": "ERREUR_INTERNE", "message": ...}`, sans trace), puis `fin`.
Côté navigateur : `fetch` en `POST` et lecture de `response.body` (pas d'`EventSource`, qui ne fait que du `GET`).
Le premier événement part immédiatement ; le LLM prend environ 2 à 3 s ; le calcul quelques millisecondes.

## Date d'arrêté d'un rapprochement
Elle n'est **jamais codée en dur** : elle est lue dans le PMS déposé (colonne `date_arrete`, une seule date admise), et les trois relevés conservateurs doivent porter la même. Si le PMS est absent ou porte plusieurs dates, le rapprochement est `BLOQUE` et `date_arrete` vaut `null`. La variable `DATE_ARRETE_ATTENDUE` refuse en plus des fichiers périmés (`BLOQUANT DATE_ARRETE`, « fichiers arrêtés au X, attendu le Y ») : `auto` exige J-1 ouvré (calendrier TARGET2, recalculé à chaque dépôt), `AAAA-MM-JJ` une date fixe ; vide (par défaut, pour la démo du 25/09), seule la cohérence entre les 4 fichiers est contrôlée. Une valeur invalide empêche le serveur de démarrer.

## Objets

### Rapprochement
```json
{
  "id": "r_8f3a2c",
  "cree_le": "2026-10-10T14:03:22Z",
  "date_arrete": "2026-09-25",
  "statut": "OK",
  "fichiers": [{"nom": "positions_internes.csv", "source": "PMS", "taille": 2345, "sha256": "ab12…"}],
  "synthese": {
    "nb_suspens": 7,
    "par_priorite": {"critique": 0, "a_relever": 5, "en_attente": 2},
    "par_type": {"QTE": 3, "ABS_DEP": 2, "ABS_INT": 1, "DEP": 1},
    "par_fonds": [{"code": "OBL", "entite": "ORSAY OBLIGATIONS", "nb_suspens": 5}],
    "par_conservateur": {"A": 3, "B": 2, "C": 1, "A→B": 1},
    "journal": {"BLOQUANT": 0, "SIGNALE": 2, "EXCLU": 3, "NORMALISE": 69}
  },
  "suspens": [Suspens],
  "journal": [Anomalie]
}
```
Si `statut = "BLOQUE"` : `suspens = []`, les compteurs de suspens valent 0, et le journal contient au moins un `BLOQUANT` avec son `remede`.

### Suspens
```json
{
  "id": "S1",
  "priorite": "a_relever",
  "fonds": "OBL",
  "entite": "ORSAY OBLIGATIONS",
  "isin": "FR0000015927",
  "libelle_titre": "AFD 3.5% 2035",
  "conservateur": "A→B",
  "type": "DEP",
  "libelle_type": "Titre détenu chez un autre dépositaire que prévu",
  "qte_pms": "250000",
  "qte_dep": "250000",
  "ecart": "0",
  "action": "Corriger le référentiel dépositaire",
  "piste": "",
  "explication": "aucune",
  "alertes": [],
  "signalements": [],
  "sources": ["positions_internes.csv:36", "depositaire_B_20260925.txt:10"]
}
```
`explication` ∈ `aucune`, `totale`, `partielle`, `contraire` : ce que les opérations en attente de `orsay.db` expliquent de l'écart, par un calcul signé. `signalements` : liste de `{"code", "message"}`, où `code` ∈ `CSDR`, `DEP_AMBIGU`, `ISIN_INVALIDE`, `PISTE_MULTI_CONSERVATEURS` ; `alertes` reprend ces codes, triés. **Un client lit les codes, jamais le texte des messages** (rédigé pour l'opérateur, il peut changer).
`id` : `S1…Sn` dans l'ordre de la liste (tri : priorité, puis entité, type, ISIN).

**Priorité** (règle métier, calculée côté back) :
- `critique` : alerte `CSDR` (opération non dénouée à sa date prévue).
- `en_attente` : `QTE`, `ABS_DEP` ou `ABS_INT` d'`explication` `totale`, sans aucune alerte : il suffit d'attendre le dénouement (achat d'une ligne nouvelle, vente totale…). Un `DEP` n'est jamais expliqué par une opération.
- `a_relever` : tout le reste (absences, DEP, écarts non ou partiellement expliqués, signalements).

### Anomalie (ligne du journal de nettoyage)
```json
{"fichier": "positions_internes.csv", "ligne": 18, "niveau": "EXCLU", "regle": "SANS_SOUS_COMPTE", "brut": "2026-09-25;;FR0000011850;SANOFI;12345;EUROCLEAR FRANCE", "retenu": "", "motif": "ligne sans sous-compte : anomalie de saisie", "remede": ""}
```
`niveau` ∈ `NORMALISE`, `EXCLU`, `SIGNALE`, `BLOQUANT`. `remede` est non vide pour tout `BLOQUANT`.

Exemple complet, données réelles du 25/09 : [`docs/exemple_rapprochement.json`](exemple_rapprochement.json).
