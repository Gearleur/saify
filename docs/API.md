# Contrat d'API : rapprochement Orsay Gestion

Source de vérité partagée entre le back (`middle_office/api/`) et le front (sources React dans `front/`, build servi depuis `middle_office/web/`).
Toute évolution du contrat passe par ce fichier d'abord.

Lancement : `uv run uvicorn middle_office.api:app --reload` puis http://127.0.0.1:8000

## Conventions
- JSON en UTF-8, champs en anglais, `snake_case`. Les valeurs codées restent celles du métier (`QTE`, `BLOQUANT`, `critique`, `a_traiter`…) ; les textes destinés à un humain (`reason`, `remedy`, `action`, `answer`…) sont en français.
- **Quantités et écarts : chaînes décimales** (`"250000"`, `"-1000"`, `"5000.5"`), jamais des nombres JSON : on ne repasse pas par `float`. `null` = absent de ce côté.
- Dates : ISO `YYYY-MM-DD` ; horodatages : ISO 8601 UTC (`2026-10-10T14:03:22Z`).
- Toute erreur renvoie `{"error": {"code": "...", "message": "...", "details": ...}}` avec le statut HTTP adapté. Jamais de trace Python.
- Chaque réponse porte un en-tête `X-Request-ID` (repris de la requête s'il est fourni, sinon généré).

## Garde-fous
| Garde-fou | Valeur | Réponse si dépassé |
|---|---|---|
| Rate limit `POST` | 20 requêtes / minute / IP | `429 RATE_LIMIT` + en-tête `Retry-After` (secondes) |
| Rate limit `GET` | 120 requêtes / minute / IP | idem |
| Rate limit `PUT` (statuts de traitement) | 120 requêtes / minute / IP, quota à part | idem |
| Rate limit questions (`POST /api/questions*`) | 10 requêtes / minute / IP, quota à part | idem |
| Usage du LLM (clé API) | modèle imposé `claude-haiku-5-5`, 300 appels réels / jour, 4 simultanés, timeout 10 s, 1 nouvelle tentative, cache des questions identiques, interrupteur `LLM_ENABLED=0` | **pas d'erreur** : repli par mots-clés, raison dans `understanding.detail` |
| Question | 3 à 500 caractères, caractères de contrôle retirés, champs inconnus refusés | `422 VALIDATION` |
| Taille du corps | 15 Mo | `413 CORPS_TROP_GROS` |
| Taille d'un fichier décodé | 5 Mo | `413 FICHIER_TROP_GROS` |
| Nombre de fichiers | 1 à 8 | `422 VALIDATION` |
| Nom de fichier | nom de base seul (pas de `/`, `\`, `..`), extensions `.csv .xlsx .txt .xml` | `422 VALIDATION` |
| Base64 | décodage strict | `422 VALIDATION` |
| Source non reconnue | préfixes `positions_internes`, `depositaire_A`, `depositaire_B`, `depositaire_C` | `422 FICHIER_NON_RECONNU` (le message liste les préfixes attendus) |
| XML | refus de `<!DOCTYPE` / `<!ENTITY>` (entités externes, billion laughs) | rapprochement `BLOQUE`, règle `FORMAT` |
| `orsay.db` | ouverte en lecture seule (`mode=ro`) | — |
| En-têtes de sécurité | CSP stricte : `default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'` (polices servies par l'application : aucune requête vers un tiers) (donc **ni script inline, ni `<style>` inline, ni attribut `style=""`, ni `onclick=`** côté front), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` | — |
| Historique persistant | SQLite séparé `var/history.db` (hors git : positions du client), jamais `orsay.db` ; réponse JSON, CSV et point de situation figés à la création | `GET /api/reconciliations` liste les 20 plus récents ; `GET /api/reconciliations/{id}` (et ses exports) relit tout l'historique, sans suppression automatique |

Un fichier refusé par le *métier* (date, total de contrôle…) n'est **pas** une erreur HTTP : la réponse est `200` avec `statut: "BLOQUE"` et le journal explique quoi faire (`remedy`).

Autres codes : `503 BASE_INDISPONIBLE` (questions, base de gestion illisible), `404 INTROUVABLE`, `405 METHODE_NON_AUTORISEE`, `503 PARAMETRAGE_INDISPONIBLE` (`/api/client-config` si `parametrage.xlsx` est illisible), `503 PAGE_INDISPONIBLE` (`GET /` sans `index.html`), `500 ERREUR_INTERNE` (sans trace). Swagger (`/docs`) est désactivé : incompatible avec la CSP stricte.

## Routes

### `GET /` → la page HTML (`middle_office/web/index.html`)
### `GET /static/assets/…` → fichiers du build (`middle_office/web/assets/`, noms hachés par Vite)

### `GET /api/health`
`as_of_date` : date de référence de la **base de gestion** (dernières positions de `orsay.db`), `null` si illisible. C'est la date des réponses aux questions et celle des fichiers d'exemple.
```json
{"status": "ok", "version": "0.3.0", "as_of_date": "2026-09-25", "db_available": true,
 "llm": {"enabled": true, "model": "claude-haiku-5-5", "calls_today": 2, "daily_budget": 300}}
```

### `GET /api/client-config`
Référentiel pour les filtres et la vue Paramétrage (lecture seule).
```json
{
  "as_of_date": "2026-09-25",
  "fund": [{"entity": "ORSAY OBLIGATIONS", "code": "OBL"}],
  "custodians": [{"code": "A", "name": "CACEIS"}, {"code": "B", "name": "Euroclear"}, {"code": "C", "name": "BNP Paribas (BP2S)"}],
  "break_types": [{"code": "QTE", "label": "Quantité différente", "expected_action": "Vérifier les opérations de la veille non dénouées"}],
  "mappings": {"TRANSCO_SOUS_COMPTES": [{"key": "SC-PAT-01", "entity": "ORSAY PATRIMOINE"}], "TRANSCO_DEPOSITAIRE_A": [], "TRANSCO_DEPOSITAIRE_B": [], "TRANSCO_DEPOSITAIRE_C": []},
  "exclusions": ["Sous-compte P3G (compte technique de passage)", "Ligne sans sous-compte (saisie incomplète)", "Item conservateur C annulé (ACTION=S)"]
}
```

### `POST /api/reconciliations`
Corps :
```json
{"files": [{"name": "positions_internes.csv", "content_b64": "ZGF0ZV9h..."}]}
```
→ `201` + objet **Reconciliation** (ci-dessous) si `status = "OK"` ; `200` si `status = "BLOQUE"` (le rapprochement est quand même enregistré dans l'historique).

### `POST /api/reconciliations/sample`
Rapproche les fichiers du 25/09 fournis (`data/donnees`). Pas de corps. → `201` (ou `200` si BLOQUE) + **Reconciliation**.

### `GET /api/reconciliations` → `[ReconciliationSummary]`, le plus récent d'abord
```json
[{"id": "r_8f3a2c", "created_at": "2026-10-10T14:03:22Z", "as_of_date": "2026-09-25", "status": "OK", "break_count": 7, "open_count": 5}]
```

### `GET /api/reconciliations/{id}` → **Reconciliation** · `404 INTROUVABLE`

### `GET /api/reconciliations/{id}/breaks.csv`
CSV `;`, UTF-8 avec BOM (ouverture directe dans Excel), quantités en texte. Colonnes :
`priorite;fonds;entite;isin;titre;conservateur;type;libelle_type;qte_pms;qte_conservateur;ecart;action;piste;signalements;sources`.
En-tête `Content-Disposition: attachment; filename="suspens_2026-09-25.csv"`.

### `GET /api/reconciliations/{id}/status-report`
```json
{"text": "Point de situation · rapprochement du 25/09/2026\n..."}
```
Texte brut, prêt à coller dans un mail : statut, synthèse par fonds et conservateur, suspens par priorité avec action attendue, exclusions et signalements.

### `GET /api/reconciliations/{id}/statuses` · `PUT /api/reconciliations/{id}/breaks/{break_id}/status`
Statut de traitement des suspens, **partagé entre les postes** : `{"statuses": {"S1": "en_cours"}}` (un suspens absent est `a_traiter`). `PUT` avec `{"status": "a_traiter" | "en_cours" | "traite"}` → `200` `{"break_id", "status", "updated_at"}` ; suspens inconnu `404 INTROUVABLE`, statut invalide `422 VALIDATION`. La clé ne dépend pas du rapprochement (date d'arrêté, entité, ISIN, conservateur, type) : relancer le rapprochement du jour garde le travail fait. Chaque changement est conservé dans `history.db` (table `status_log`, avec l'identifiant de requête) et tracé dans le log d'audit.

### `POST /api/questions` (besoin 2)
Corps `{"question": "Combien pèse le fonds obligataire ?"}` → `200` + **QuestionAnswer**.
Le LLM (Haiku 5.5) ne fait que **classer** la question dans le catalogue (encours, échéances, concentration,
opérations non dénouées, origine d'un suspens) ; il ne reçoit aucune donnée de la base. Les chiffres viennent
de requêtes SQL fixes, en lecture seule, calculées en `Decimal` ; la phrase est un gabarit.
**Jamais de réponse à côté** (un vrai chiffre, mais d'une autre question) : une demande d'écriture formulée comme un ordre, une autre date que la date de référence pour un encours, une concentration ou des opérations (`understanding.requested_date`), l'encours d'un titre seul, ou un titre ambigu (« l'OAT » : 4 titres) donnent un « Attention » sans chiffre et des reformulations. Un titre est reconnu par son ISIN, son libellé, son nom court (« SFIL ») ou son émetteur ; les échéances et les opérations non dénouées se filtrent sur lui (paramètre SQL `isin`). « D'ici le 31/12/2026 » borne les échéances à cette date exacte.
« Origine d'un suspens » répond sur le **dernier rapprochement `OK`**, cité avec sa date d'arrêté. Si un rapprochement plus récent est bloqué, la réponse le signale dans `warnings` et passe en `confiance: "basse"` (elle ne dit jamais « aucun suspens » sur la foi d'un rapprochement bloqué).
```json
{
  "question": "Combien pèse le fonds obligataire ?",
  "answer": "L'encours valorisé d'ORSAY OBLIGATIONS au 25/09/2026 est de 724 836,00 EUR (10 lignes valorisées au cours de clôture du 25/09/2026).",
  "figures": [{"label": "Encours valorisé", "value": "724836.00", "unit": "EUR"}],
  "sql_query": "SELECT p.portefeuille, f.nom, p.isin, ... WHERE p.date_arrete = :date AND (:fonds IS NULL OR p.portefeuille = :fonds) ...",
  "sql_params": {"date": "2026-09-25", "fund": "OBL"},
  "source_rows": [{"table": "positions × titres × cours", "values": {"isin": "FR0000015927", "quantite": "250000", "cours": "97.0", "valorisation": "242500.00"}}],
  "confidence": "haute",
  "warnings": ["Obligations valorisées au pied de coupon (cours en % du nominal), sans coupon couru."],
  "vigilances": [],
  "suggestions": [],
  "understanding": {"intent": "ENCOURS", "fund": "OBL", "horizon_months": null, "isin": null, "source": "llm", "confidence": 0.95, "detail": ""}
}
```
- `vigilances` (concentration uniquement) : `[{"code": "EMETTEUR_AU_DESSUS_DU_SEUIL", "message": "...", "issuers": ["Kering"], "value": "87.54"}]`, seuils **internes** (10 % par émetteur ; cumul des > 5 % au-delà de 40 %), jamais un verdict réglementaire.
- Pas de réponse sûre (confiance < 0,7, hors catalogue, fonds ou titre manquant, demande d'écriture) : `answer` commence par **« Attention : »**, `chiffres = []`, `confiance = "basse"`, et `suggestions` propose 2 ou 3 questions qui mènent au catalogue.
- `sql_query` + `sql_params` : la requête exacte exécutée, rejouable telle quelle.

### `POST /api/questions/stream` (même corps, réponse en flux SSE)
`Content-Type: text/event-stream`. L'entrée est validée **avant** l'ouverture du flux (422 normal). Événements, dans l'ordre :
```
event: step           data: {"step": "understanding", "message": "Analyse de la question…"}
event: understanding  data: {"intent": "ENCOURS", "fund": "OBL", ..., "source": "llm"}
event: step           data: {"step": "computing", "message": "Requête en lecture seule sur la base de gestion…"}
event: answer         data: <QuestionAnswer, identique à la route JSON>
event: end            data: {}
```
En cas de panne : `event: error` (`{"code": "ERREUR_INTERNE", "message": ...}`, sans trace), puis `end`.
Côté navigateur : `fetch` en `POST` et lecture de `response.body` (pas d'`EventSource`, qui ne fait que du `GET`).
Le premier événement part immédiatement ; le LLM prend environ 2 à 3 s ; le calcul quelques millisecondes.

## Date d'arrêté d'un rapprochement
Elle n'est **jamais codée en dur** : elle est lue dans le PMS déposé (colonne `as_of_date`, une seule date admise), et les trois relevés conservateurs doivent porter la même. Si le PMS est absent ou porte plusieurs dates, le rapprochement est `BLOQUE` et `as_of_date` vaut `null`. La variable `EXPECTED_AS_OF_DATE` refuse en plus des fichiers périmés (`BLOQUANT DATE_ARRETE`, « fichiers arrêtés au X, attendu le Y ») : `auto` exige J-1 ouvré (calendrier TARGET2, recalculé à chaque dépôt), `AAAA-MM-JJ` une date fixe ; vide (par défaut, pour la démo du 25/09), seule la cohérence entre les 4 fichiers est contrôlée. Une valeur invalide empêche le serveur de démarrer.

## Objets

### Reconciliation
```json
{
  "id": "r_8f3a2c",
  "created_at": "2026-10-10T14:03:22Z",
  "as_of_date": "2026-09-25",
  "status": "OK",
  "files": [{"name": "positions_internes.csv", "source": "PMS", "size": 2345, "sha256": "ab12…"}],
  "summary": {
    "break_count": 7,
    "by_priority": {"critique": 0, "a_relever": 5, "en_attente": 2},
    "by_type": {"QTE": 3, "ABS_DEP": 2, "ABS_INT": 1, "DEP": 1},
    "by_fund": [{"code": "OBL", "entity": "ORSAY OBLIGATIONS", "break_count": 5}],
    "by_custodian": {"A": 3, "B": 2, "C": 1, "A→B": 1},
    "cleaning_log": {"BLOQUANT": 0, "SIGNALE": 2, "EXCLU": 3, "NORMALISE": 69}
  },
  "breaks": [Break],
  "cleaning_log": [Anomaly]
}
```
Si `status = "BLOQUE"` : `suspens = []`, les compteurs de suspens valent 0, et le journal contient au moins un `BLOQUANT` avec son `remedy`.

### Break (suspens)
```json
{
  "id": "S1",
  "priority": "a_relever",
  "fund": "OBL",
  "entity": "ORSAY OBLIGATIONS",
  "isin": "FR0000015927",
  "security_name": "AFD 3.5% 2035",
  "custodian": "A→B",
  "type": "DEP",
  "break_type_label": "Titre détenu chez un autre dépositaire que prévu",
  "pms_qty": "250000",
  "custodian_qty": "250000",
  "difference": "0",
  "action": "Corriger le référentiel dépositaire",
  "lead": "",
  "explanation": "aucune",
  "alerts": [],
  "flags": [],
  "sources": ["positions_internes.csv:36", "depositaire_B_20260925.txt:10"]
}
```
`explanation` ∈ `aucune`, `totale`, `partielle`, `contraire` : ce que les opérations en attente de `orsay.db` expliquent de l'écart, par un calcul signé. `flags` : liste de `{"code", "message"}`, où `code` ∈ `CSDR`, `DEP_AMBIGU`, `ISIN_INVALIDE`, `PISTE_MULTI_CONSERVATEURS` ; `alerts` reprend ces codes, triés. **Un client lit les codes, jamais le texte des messages** (rédigé pour l'opérateur, il peut changer).
`id` : `S1…Sn` dans l'ordre de la liste (tri : priorité, puis entité, type, ISIN).

**Priorité** (règle métier, calculée côté back) :
- `critique` : alerte `CSDR` (opération non dénouée à sa date prévue).
- `en_attente` : `QTE`, `ABS_DEP` ou `ABS_INT` d'`explanation` `totale`, sans aucune alerte : il suffit d'attendre le dénouement (achat d'une ligne nouvelle, vente totale…). Un `DEP` n'est jamais expliqué par une opération.
- `a_relever` : tout le reste (absences, DEP, écarts non ou partiellement expliqués, signalements).

### Anomaly (ligne du journal de nettoyage)
```json
{"file": "positions_internes.csv", "line": 18, "level": "EXCLU", "rule": "SANS_SOUS_COMPTE", "raw": "2026-09-25;;FR0000011850;SANOFI;12345;EUROCLEAR FRANCE", "kept": "", "reason": "ligne sans sous-compte : anomalie de saisie", "remedy": ""}
```
`level` ∈ `NORMALISE`, `EXCLU`, `SIGNALE`, `BLOQUANT`. `remedy` est non vide pour tout `BLOQUANT`.

Exemple complet, données réelles du 25/09 : [`docs/sample_reconciliation.json`](sample_reconciliation.json).
