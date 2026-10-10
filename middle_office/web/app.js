/* Rapprochement de positions titres · Orsay Gestion · front natif.
 *
 * Contrat : docs/API.md. Aucun framework, aucun build.
 * CSP stricte : pas de style inline, pas de gestionnaire inline. Tout le HTML généré
 * passe par esc() ; les événements sont délégués depuis #view et le document.
 * Quantités : chaînes décimales, formatées sans parseFloat (fmtDec, cmpDec).
 */
(function () {
  "use strict";

  /* ======================================================================
   * Utilitaires
   * ==================================================================== */

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function esc(v) {
    if (v === null || v === undefined) return "";
    return String(v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const NNBSP = " "; // espace fine insécable, séparateur de milliers
  const MINUS = "−";
  const DEC_RE = /^[-+]?\d+(\.\d+)?$/;

  /* Formate une chaîne décimale « 250000 » → « 250 000 », « -1000.5 » → « −1 000,5 ».
   * signed : ajoute « + » aux valeurs positives (écarts). Aucun passage par float. */
  function fmtDec(s, signed) {
    if (s === null || s === undefined || s === "") return "";
    let str = String(s).trim();
    if (!DEC_RE.test(str)) return str;
    let sign = "";
    if (str[0] === "-") { sign = MINUS; str = str.slice(1); }
    else if (str[0] === "+") { str = str.slice(1); }
    let [ip, fp] = str.split(".");
    ip = ip.replace(/^0+(?=\d)/, "");
    if (fp !== undefined) fp = fp.replace(/0+$/, "");
    const zero = /^0+$/.test(ip) && !fp;
    if (zero) sign = "";
    else if (signed && !sign) sign = "+";
    ip = ip.replace(/\B(?=(\d{3})+(?!\d))/g, NNBSP);
    return sign + ip + (fp ? "," + fp : "");
  }

  function decSign(s) {
    if (s === null || s === undefined || !DEC_RE.test(String(s).trim())) return 0;
    const t = String(s).trim();
    if (/^[-+]?0+(\.0+)?$/.test(t)) return 0;
    return t[0] === "-" ? -1 : 1;
  }

  /* Comparaison de deux chaînes décimales, sans float. null en dernier. */
  function cmpDec(a, b) {
    const na = a === null || a === undefined || a === "";
    const nb = b === null || b === undefined || b === "";
    if (na || nb) return na === nb ? 0 : na ? 1 : -1;
    const pa = parseDec(a), pb = parseDec(b);
    if (pa.neg !== pb.neg) return pa.neg ? -1 : 1;
    const abs = cmpAbs(pa, pb);
    return pa.neg ? -abs : abs;
  }
  function parseDec(s) {
    let t = String(s).trim();
    let neg = t[0] === "-";
    t = t.replace(/^[-+]/, "");
    let [i, f] = t.split(".");
    i = (i || "0").replace(/^0+/, "") || "0";
    f = (f || "").replace(/0+$/, "");
    if (i === "0" && !f) neg = false;
    return { neg, i, f };
  }
  function cmpAbs(a, b) {
    if (a.i.length !== b.i.length) return a.i.length < b.i.length ? -1 : 1;
    if (a.i !== b.i) return a.i < b.i ? -1 : 1;
    const len = Math.max(a.f.length, b.f.length);
    const fa = a.f.padEnd(len, "0"), fb = b.f.padEnd(len, "0");
    return fa === fb ? 0 : fa < fb ? -1 : 1;
  }

  function fmtDate(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? `${m[3]}/${m[2]}/${m[1]}` : (iso || "");
  }
  function fmtDateShort(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? `${m[3]}/${m[2]}` : (iso || "");
  }
  function fmtTime(iso) {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }
  function fmtStamp(iso) {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }) + " à " + fmtTime(iso);
  }
  function fmtSize(n) {
    if (typeof n !== "number") return "";
    if (n < 1024) return n + " o";
    if (n < 1024 * 1024) return (Math.round(n / 102.4) / 10).toString().replace(".", ",") + " Ko";
    return (Math.round(n / 104857.6) / 10).toString().replace(".", ",") + " Mo";
  }
  function norm(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  function plural(n, one, many) { return n + " " + (n > 1 ? many : one); }

  const store = {
    get(key, fallback) {
      try {
        const raw = window.localStorage.getItem(key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (e) { return fallback; }
    },
    set(key, value) {
      try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* poste sans stockage */ }
    },
  };

  /* ======================================================================
   * Icônes (style lucide, trait 1.5)
   * ==================================================================== */

  const ICONS = {
    inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    rows: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
    scroll: '<path d="m3 17 2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8"/>',
    folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    chevrons: '<path d="m7 15 5 5 5-5M7 9l5-5 5 5"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4M12 17h.01"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    "check-circle": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "chevron-up": '<path d="m18 15-6-6-6 6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    blocked: '<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><path d="m15 9-6 6M9 9l6 6"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    loader: '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
    send: '<path d="m5 12 7-7 7 7M12 19V5"/>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "arrow-right": '<path d="M5 12h14M12 5l7 7-7 7"/>',
    command: '<path d="M15 6v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3"/>',
  };
  function svg(name) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || "") + "</svg>";
  }
  function ico(name, extra) {
    return '<span class="ico' + (extra ? " " + extra : "") + '">' + svg(name) + "</span>";
  }
  function hydrateIcons(root) {
    $$("[data-icon]", root).forEach((el) => {
      if (!el.firstChild) el.innerHTML = svg(el.getAttribute("data-icon"));
    });
  }

  /* ======================================================================
   * Référentiels d'affichage
   * ==================================================================== */

  const VIEWS = {
    "a-traiter": { title: "À traiter", group: "Rapprochement", icon: "inbox" },
    suspens: { title: "Suspens", group: "Rapprochement", icon: "rows" },
    point: { title: "Point de situation", group: "Rapprochement", icon: "file-text" },
    journal: { title: "Journal de nettoyage", group: "Rapprochement", icon: "scroll" },
    fichiers: { title: "Fichiers", group: "Rapprochement", icon: "folder" },
    questions: { title: "Questions", group: "Base de gestion", icon: "message" },
    parametrage: { title: "Paramétrage", group: "Référentiel", icon: "sliders" },
  };

  const PRIO = {
    critique: { label: "Critique", pill: "pill-crit", order: 0 },
    a_relever: { label: "À relever", pill: "pill-warn", order: 1 },
    en_attente: { label: "En attente", pill: "pill-ok", order: 2 },
  };
  const TYPES_FALLBACK = {
    QTE: "Quantité différente",
    ABS_DEP: "Position interne absente chez le dépositaire",
    ABS_INT: "Position dépositaire absente du livre interne",
    DEP: "Titre détenu chez un autre dépositaire que prévu",
  };
  const CONS_FALLBACK = { A: "CACEIS", B: "Euroclear", C: "BNP Paribas (BP2S)" };
  const LEVELS = ["BLOQUANT", "SIGNALE", "EXCLU", "NORMALISE"];
  const LEVEL_INFO = {
    BLOQUANT: { pill: "pill-crit", label: "Bloquant", text: "Fichier refusé : rien n'est rapproché tant qu'il n'est pas corrigé." },
    SIGNALE: { pill: "pill-warn", label: "Signalé", text: "Ligne conservée mais douteuse : à vérifier par un humain." },
    EXCLU: { pill: "pill-neutral", label: "Exclu", text: "Ligne retirée en application d'une règle du client." },
    NORMALISE: { pill: "pill-ok", label: "Normalisé", text: "Valeur remise en forme sans en changer le sens." },
  };
  const LOCAL_STATUS = {
    a_traiter: { label: "À traiter", pill: "pill-neutral" },
    en_cours: { label: "En cours", pill: "pill-warn", seg: "s-encours" },
    traite: { label: "Traité", pill: "pill-ok", seg: "s-traite" },
  };
  const EXPECTED = [
    { src: "PMS", prefix: "positions_internes", label: "Inventaire interne (PMS)", fmt: "CSV" },
    { src: "A", prefix: "depositaire_A", label: "Conservateur A · CACEIS", fmt: "XLSX" },
    { src: "B", prefix: "depositaire_B", label: "Conservateur B · Euroclear", fmt: "TXT largeur fixe" },
    { src: "C", prefix: "depositaire_C", label: "Conservateur C · BNP / BP2S", fmt: "XML" },
  ];
  const MAX_FILE = 5 * 1024 * 1024;
  const MAX_FILES = 8;

  function sourceOf(name) {
    if (/^positions_internes/i.test(name)) return "PMS";
    const m = /^depositaire_([abc])/i.exec(name);
    return m ? m[1].toUpperCase() : null;
  }
  function consName(code) {
    const list = state.param && state.param.conservateurs;
    const hit = list && list.find((c) => c.code === code);
    return hit ? hit.nom : CONS_FALLBACK[code] || code;
  }
  function typeLabel(code) {
    const t = state.param && state.param.types_ecarts && state.param.types_ecarts.find((x) => x.code === code);
    return t ? t.libelle : TYPES_FALLBACK[code] || code;
  }
  function isCsdr(text) { return /csdr|d[ée]nouement d[ée]pass|denouement_depasse/i.test(text || ""); }

  /* ======================================================================
   * État
   * ==================================================================== */

  const prefs = Object.assign(
    {
      view: "a-traiter",
      sFilters: { fonds: [], cons: [], type: [], prio: [], statut: [] },
      sQuery: "",
      sSort: { key: "priorite", dir: 1 },
      jLevels: ["BLOQUANT", "SIGNALE", "EXCLU"],
      jQuery: "",
    },
    store.get("reco.prefs", {})
  );
  function savePrefs() { store.set("reco.prefs", prefs); }

  const state = {
    view: "a-traiter",
    rapp: null,            // Rapprochement courant
    liste: [],             // historique
    param: null,
    paramError: null,
    sante: null,
    santeOk: null,
    point: {},             // cache texte du point de situation par id
    pointError: null,
    staged: [],            // fichiers sélectionnés, en attente d'envoi
    uploadError: null,
    busy: false,
    cursor: 0,             // ligne active de la grille des suspens
    sheet: { open: false, id: null, list: [] },
    blockedDone: {},       // cases cochées du bandeau bloquant (session)
    statuts: store.get("reco.statuts", {}),
    booting: true,
    q: { text: "", status: "idle", data: null, error: null, preview: false },
  };

  function localKey(s) {
    const r = state.rapp;
    return [r ? r.date_arrete : "", s.fonds, s.isin, s.conservateur, s.type].join("|");
  }
  function getStatut(s) { return state.statuts[localKey(s)] || "a_traiter"; }
  function setStatut(s, v) {
    const k = localKey(s);
    if (v === "a_traiter") delete state.statuts[k];
    else state.statuts[k] = v;
    store.set("reco.statuts", state.statuts);
  }

  /* ======================================================================
   * API
   * ==================================================================== */

  class ApiError extends Error {
    constructor(status, code, message, details, retryAfter) {
      super(message);
      this.status = status;
      this.code = code;
      this.details = details;
      this.retryAfter = retryAfter;
    }
  }

  async function api(path, opts) {
    const o = Object.assign({ method: "GET", headers: {} }, opts || {});
    if (o.json !== undefined) {
      o.body = JSON.stringify(o.json);
      o.headers["Content-Type"] = "application/json";
      delete o.json;
    }
    o.headers.Accept = "application/json";
    let res;
    try {
      res = await fetch(path, o);
    } catch (e) {
      throw new ApiError(0, "RESEAU", "API injoignable. Vérifiez que le serveur tourne (uv run uvicorn reco.api:app).");
    }
    const ra = res.headers.get("Retry-After");
    let body = null;
    const text = await res.text();
    if (text) { try { body = JSON.parse(text); } catch (e) { body = null; } }
    if (!res.ok) {
      const err = body && body.erreur ? body.erreur : {};
      throw new ApiError(res.status, err.code || "HTTP_" + res.status, err.message || defaultMessage(res.status), err.details, ra);
    }
    return body;
  }
  function defaultMessage(status) {
    if (status === 413) return "Fichiers trop volumineux : 5 Mo par fichier et 15 Mo au total.";
    if (status === 422) return "Requête refusée par le contrôle des entrées.";
    if (status === 429) return "Trop de requêtes en peu de temps.";
    if (status === 404) return "Ressource introuvable.";
    if (status === 501) return "Fonction pas encore disponible.";
    return "Erreur du serveur (HTTP " + status + ").";
  }
  function errorTitle(err) {
    if (err.status === 413) return "Fichier trop volumineux";
    if (err.status === 422) return err.code === "FICHIER_NON_RECONNU" ? "Fichier non reconnu" : "Envoi refusé";
    if (err.status === 429) return "Trop de requêtes";
    if (err.status === 0) return "API injoignable";
    return "Erreur";
  }
  function errorSub(err) {
    let s = err.message;
    if (err.status === 429 && err.retryAfter) s += " Réessayez dans " + err.retryAfter + " s.";
    return s;
  }

  /* ======================================================================
   * Toasts
   * ==================================================================== */

  function toast(msg, kind, sub) {
    const box = $("#toasts");
    const el = document.createElement("div");
    el.className = "toast t-" + (kind || "ok");
    const icon = kind === "err" ? "alert" : kind === "info" ? "info" : "check-circle";
    el.innerHTML = ico(icon) + "<div>" + esc(msg) + (sub ? '<span class="t-sub">' + esc(sub) + "</span>" : "") + "</div>";
    while (box.children.length >= 3) box.firstElementChild.remove();
    box.appendChild(el);
    const ttl = kind === "err" ? 6500 : 3200;
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 180);
    }, ttl);
  }

  /* ======================================================================
   * Chargements
   * ==================================================================== */

  async function loadSante() {
    try {
      state.sante = await api("/api/sante");
      state.santeOk = state.sante && state.sante.statut === "ok";
    } catch (e) {
      state.santeOk = false;
    }
    renderHealth();
    renderTopbar();
  }

  async function loadParam() {
    try {
      state.param = await api("/api/parametrage");
      state.paramError = null;
    } catch (e) {
      state.paramError = e;
    }
  }

  async function loadListe() {
    try {
      const l = await api("/api/rapprochements");
      state.liste = Array.isArray(l) ? l : [];
    } catch (e) {
      state.liste = [];
    }
    renderHistory();
  }

  async function loadRapp(id, quiet) {
    try {
      const r = await api("/api/rapprochements/" + encodeURIComponent(id));
      setRapp(r);
      if (!quiet) toast("Rapprochement du " + fmtDate(r.date_arrete) + " chargé", "info", "Lancé le " + fmtStamp(r.cree_le));
    } catch (e) {
      toast(errorTitle(e), "err", errorSub(e));
      if (e.status === 404) loadListe();
    }
  }

  function setRapp(r) {
    state.rapp = r;
    state.cursor = 0;
    state.blockedDone = {};
    state.pointError = null;
    closeSheet();
    renderChrome();
    renderView();
  }

  async function runExemple() {
    if (state.busy) return;
    setBusy(true, "#act-exemple");
    try {
      const r = await api("/api/rapprochements/exemple", { method: "POST" });
      afterRun(r);
    } catch (e) {
      toast(errorTitle(e), "err", errorSub(e));
    } finally {
      setBusy(false, "#act-exemple");
    }
  }

  async function runUpload() {
    if (state.busy || !state.staged.length) return;
    state.uploadError = null;
    setBusy(true, "#run-upload");
    try {
      const fichiers = [];
      for (const f of state.staged) {
        fichiers.push({ nom: f.file.name, contenu_b64: await toBase64(f.file) });
      }
      const r = await api("/api/rapprochements", { method: "POST", json: { fichiers } });
      state.staged = [];
      afterRun(r);
    } catch (e) {
      state.uploadError = e;
      toast(errorTitle(e), "err", errorSub(e));
      if (state.view === "fichiers") renderView();
    } finally {
      setBusy(false, "#run-upload");
    }
  }

  function afterRun(r) {
    if (r.statut === "BLOQUE") {
      const n = (r.journal || []).filter((j) => j.niveau === "BLOQUANT").length;
      toast("Rapprochement bloqué", "err", plural(n, "point bloquant", "points bloquants") + " à corriger avant de rapprocher.");
    } else {
      const s = r.synthese || {};
      const p = s.par_priorite || {};
      toast("Rapprochement terminé", "ok", plural(s.nb_suspens || 0, "suspens", "suspens") + ", dont " + ((p.critique || 0) + (p.a_relever || 0)) + " à traiter.");
    }
    setRapp(r);
    loadListe();
    navigate("a-traiter");
  }

  function setBusy(on, sel) {
    state.busy = on;
    const b = sel && $(sel);
    if (b) {
      b.classList.toggle("is-busy", on);
      const i = $(".ico", b);
      if (i) i.innerHTML = svg(on ? "loader" : i.getAttribute("data-icon") || "play");
    }
  }

  function toBase64(file) {
    return file.arrayBuffer().then((buf) => {
      const bytes = new Uint8Array(buf);
      let bin = "";
      const CHUNK = 0x8000;
      for (let i = 0; i < bytes.length; i += CHUNK) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
      }
      return btoa(bin);
    });
  }

  async function getPoint() {
    const r = state.rapp;
    if (!r) return null;
    if (state.point[r.id]) return state.point[r.id];
    const res = await api("/api/rapprochements/" + encodeURIComponent(r.id) + "/point-de-situation");
    state.point[r.id] = res && res.texte ? res.texte : "";
    return state.point[r.id];
  }

  async function copyPoint() {
    if (!state.rapp) { toast("Aucun rapprochement chargé", "err", "Lancez d'abord un rapprochement."); return; }
    try {
      const t = await getPoint();
      await copyText(t);
      toast("Point de situation copié", "ok", "Prêt à coller dans un mail.");
    } catch (e) {
      toast(e instanceof ApiError ? errorTitle(e) : "Copie impossible", "err", e.message);
    }
  }

  async function copyText(t) {
    try {
      await navigator.clipboard.writeText(t);
      return;
    } catch (e) { /* repli ci-dessous */ }
    const ta = document.createElement("textarea");
    ta.value = t;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    if (!ok) throw new Error("Le navigateur a refusé l'accès au presse-papiers.");
  }

  function csvUrl() {
    return state.rapp ? "/api/rapprochements/" + encodeURIComponent(state.rapp.id) + "/suspens.csv" : "#";
  }

  /* ======================================================================
   * Fichiers sélectionnés
   * ==================================================================== */

  function stageFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    for (const f of files) {
      const i = state.staged.findIndex((x) => x.file.name === f.name);
      const entry = { file: f, source: sourceOf(f.name) };
      if (i >= 0) state.staged[i] = entry; else state.staged.push(entry);
    }
    state.uploadError = null;
    toast(plural(files.length, "fichier sélectionné", "fichiers sélectionnés"), "info", "Vérifiez la liste puis lancez le rapprochement.");
    if (state.view !== "fichiers") navigate("fichiers"); else renderView();
  }

  function stagedWarnings() {
    const w = [];
    if (state.staged.length > MAX_FILES) w.push("Plus de " + MAX_FILES + " fichiers : l'envoi sera refusé.");
    const seen = {};
    for (const s of state.staged) {
      const n = s.file.name;
      if (!s.source) w.push("« " + n + " » : nom non reconnu, préfixes attendus positions_internes, depositaire_A, _B ou _C.");
      if (!/\.(csv|xlsx|txt|xml)$/i.test(n)) w.push("« " + n + " » : extension refusée (.csv, .xlsx, .txt, .xml).");
      if (s.file.size > MAX_FILE) w.push("« " + n + " » dépasse 5 Mo.");
      if (s.source) {
        if (seen[s.source]) w.push("Deux fichiers pour la source " + s.source + " : le rapprochement sera bloqué.");
        seen[s.source] = true;
      }
    }
    return w;
  }

  /* ======================================================================
   * Navigation
   * ==================================================================== */

  function navigate(view) {
    if (location.hash !== "#/" + view) location.hash = "#/" + view;
    else route();
  }

  function route() {
    const m = /^#\/([\w-]+)/.exec(location.hash);
    let v = m ? m[1] : prefs.view;
    if (!VIEWS[v]) v = "a-traiter";
    const changed = state.view !== v;
    state.view = v;
    prefs.view = v;
    savePrefs();
    if (changed) closeSheet();
    $("#app").classList.remove("sb-open");
    renderChrome();
    renderView();
    if (changed) $("#view").scrollTop = 0;
  }

  /* ======================================================================
   * Chrome : sidebar, topbar
   * ==================================================================== */

  function renderChrome() {
    renderNav();
    renderRunStatus();
    renderHistory();
    renderTopbar();
  }

  function counts() {
    const r = state.rapp;
    const s = (r && r.synthese) || {};
    const p = s.par_priorite || {};
    const j = s.journal || {};
    return {
      total: s.nb_suspens || 0,
      crit: p.critique || 0,
      rel: p.a_relever || 0,
      att: p.en_attente || 0,
      bloq: j.BLOQUANT || 0,
      sig: j.SIGNALE || 0,
      excl: j.EXCLU || 0,
      normal: j.NORMALISE || 0,
    };
  }

  function renderNav() {
    $$(".nav-item").forEach((a) => {
      const on = a.getAttribute("data-view") === state.view;
      a.classList.toggle("is-active", on);
      if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    const bT = $("#badge-a-traiter"), bS = $("#badge-suspens"), bJ = $("#badge-journal");
    bT.className = "nav-badge badge-alert";
    bJ.className = "nav-badge";
    if (!state.rapp) { bT.textContent = ""; bS.textContent = ""; bJ.textContent = ""; return; }
    const c = counts();
    if (state.rapp.statut === "BLOQUE") {
      bT.textContent = "!";
      bT.classList.add("has-crit");
    } else {
      bT.textContent = String(c.crit + c.rel);
      bT.classList.add(c.crit ? "has-crit" : c.rel ? "has-warn" : "is-zero");
    }
    bS.textContent = String(c.total);
    bJ.textContent = c.bloq + c.sig ? String(c.bloq + c.sig) : "";
    if (c.bloq) bJ.classList.add("badge-block");
  }

  function renderRunStatus() {
    const r = state.rapp;
    const dateIso = r ? r.date_arrete : (state.sante && state.sante.date_arrete) || (state.param && state.param.date_arrete);
    $("#rs-date").textContent = dateIso ? fmtDate(dateIso) : "—";
    const pill = $("#rs-pill");
    if (!r) {
      pill.className = "pill pill-neutral";
      pill.textContent = "Aucun rapprochement";
      $("#rs-time").textContent = "";
    } else if (r.statut === "BLOQUE") {
      pill.className = "pill pill-crit";
      pill.textContent = "Bloqué";
      $("#rs-time").textContent = "à " + fmtTime(r.cree_le);
    } else {
      pill.className = "pill pill-ok";
      pill.textContent = "OK";
      $("#rs-time").textContent = "à " + fmtTime(r.cree_le);
    }
  }

  function renderHistory() {
    const ul = $("#history");
    if (!state.liste.length) {
      ul.innerHTML = '<li class="hist-empty">Aucun rapprochement pour l\'instant</li>';
      return;
    }
    ul.innerHTML = state.liste.slice(0, 20).map((h) => {
      const cur = state.rapp && state.rapp.id === h.id;
      const pill = h.statut === "BLOQUE" ? '<span class="pill pill-crit">Bloqué</span>' : '<span class="pill pill-ok">OK</span>';
      const sub = h.statut === "BLOQUE" ? "à corriger" : plural(h.nb_suspens || 0, "suspens", "suspens") + ", " + (h.nb_a_traiter || 0) + " à traiter";
      return '<li><button type="button" class="' + (cur ? "is-current" : "") + '" data-hist="' + esc(h.id) + '"' + (cur ? ' aria-current="true"' : "") + ">" +
        '<span class="hist-main"><span class="num">Arrêté ' + esc(fmtDateShort(h.date_arrete)) + " · " + esc(fmtTime(h.cree_le)) + "</span>" +
        '<span class="hist-sub">' + esc(sub) + "</span></span>" + pill + "</button></li>";
    }).join("");
  }

  function renderHealth() {
    const dot = $("#health-dot"), txt = $("#health-text");
    dot.className = "dot" + (state.santeOk === true ? " is-ok" : state.santeOk === false ? " is-ko" : "");
    if (state.santeOk === true) {
      txt.textContent = "API v" + (state.sante.version || "?") + (state.sante.base_disponible === false ? ", base indisponible" : "");
    } else if (state.santeOk === false) {
      txt.textContent = "API injoignable";
    } else {
      txt.textContent = "API…";
    }
  }

  function renderTopbar() {
    const v = VIEWS[state.view];
    const r = state.rapp;
    let crumbs = '<span>' + esc(v.group) + "</span>" + ico("chevron-right");
    crumbs += "<span>" + (r ? "Arrêté du " + esc(fmtDate(r.date_arrete)) : "Aucun rapprochement") + "</span>";
    if (state.view === "questions" || state.view === "parametrage") crumbs = "<span>" + esc(v.group) + "</span>";
    $("#crumbs").innerHTML = crumbs;
    $("#tb-title").textContent = v.title;
    document.title = v.title + " · Rapprochement Orsay Gestion";

    const dateIso = (state.sante && state.sante.date_arrete) || (state.param && state.param.date_arrete) || "2026-09-25";
    $("#act-exemple-label").textContent = "Lancer sur les fichiers du " + fmtDateShort(dateIso);

    const csv = $("#act-csv");
    const csvOk = r && r.statut !== "BLOQUE";
    csv.setAttribute("href", csvOk ? csvUrl() : "#");
    csv.setAttribute("aria-disabled", csvOk ? "false" : "true");
    csv.setAttribute("title", csvOk ? "Télécharger les suspens (CSV ; pour Excel)" : "Aucun suspens à exporter");
    const cp = $("#act-copier");
    cp.disabled = !r;
  }

  /* ======================================================================
   * Fragments communs
   * ==================================================================== */

  function prioPill(p) {
    const x = PRIO[p] || { label: p, pill: "pill-neutral" };
    return '<span class="pill ' + x.pill + '">' + esc(x.label) + "</span>";
  }
  function typeTag(t) {
    const cls = TYPES_FALLBACK[t] ? "t-" + t : "t-other";
    return '<span class="type-tag ' + cls + '" title="' + esc(typeLabel(t)) + '">' + esc(t) + "</span>";
  }
  function fundTag(code, entite) {
    return '<span class="fund-tag" title="' + esc(entite || "") + '">' + esc(code) + "</span>";
  }
  function consHtml(c, withName) {
    const parts = String(c || "").split("→");
    if (parts.length === 2) {
      return '<span class="cons" title="Attendu chez ' + esc(consName(parts[0])) + ", trouvé chez " + esc(consName(parts[1])) + '">' +
        '<span class="cons-code">' + esc(parts[0]) + '</span><span class="cons-arrow">→</span><span class="cons-code">' + esc(parts[1]) + "</span>" +
        (withName ? '<span class="cons-name">' + esc(consName(parts[0])) + " → " + esc(consName(parts[1])) + "</span>" : "") + "</span>";
    }
    return '<span class="cons" title="' + esc(consName(c)) + '"><span class="cons-code">' + esc(c) + "</span>" +
      (withName ? '<span class="cons-name">' + esc(consName(c)) + "</span>" : "") + "</span>";
  }
  function qtyHtml(s) {
    return s === null || s === undefined ? '<span class="q-absent">absent</span>' : '<span class="num">' + esc(fmtDec(s)) + "</span>";
  }
  function ecartHtml(s) {
    const sg = decSign(s);
    const cls = sg > 0 ? "is-pos" : sg < 0 ? "is-neg" : "is-zero";
    return '<span class="ecart ' + cls + '">' + esc(fmtDec(s, true)) + "</span>";
  }
  function statutPill(s) {
    const st = getStatut(s);
    if (st === "a_traiter") return "";
    const x = LOCAL_STATUS[st];
    return '<span class="pill ' + x.pill + '">' + esc(x.label) + "</span>";
  }

  /* Piste : « op. n°19 ACHAT 25 000 dén. 26/09/2026 → écart entièrement expliqué » */
  function parsePiste(p) {
    if (!p) return null;
    const m = /op\.?\s*n°\s*(\S+)\s+(ACHAT|VENTE)\s+([\d\s  .,]+?)\s+d[ée]n\.?\s*(\d{2}\/\d{2}\/\d{4})(?:\s*→\s*(.+))?/i.exec(p);
    if (!m) return { raw: p };
    return { raw: p, op: m[1], sens: m[2].toUpperCase(), qte: m[3].trim(), den: m[4], verdict: (m[5] || "").trim() };
  }
  function verdictClass(v) {
    if (/enti[èe]rement/i.test(v)) return "verdict-ok";
    if (/partiel|reste|possible/i.test(v)) return "verdict-part";
    return "";
  }

  function emptyRapp(title) {
    return '<div class="state-card">' + ico("inbox") + "<div><h3>" + esc(title || "Aucun rapprochement chargé") + "</h3>" +
      "<p>Lancez le rapprochement sur les fichiers du jour, ou déposez vos propres relevés.</p>" +
      '<div class="state-actions"><button class="btn btn-primary btn-sm" type="button" data-act="exemple">' + ico("play") + "<span>Lancer sur les fichiers du 25/09</span></button> " +
      '<button class="btn btn-sm" type="button" data-act="pick">' + ico("upload") + "<span>Déposer des fichiers</span></button></div></div></div>";
  }

  function expectedList() {
    const cur = {};
    if (state.rapp && state.rapp.fichiers) state.rapp.fichiers.forEach((f) => { cur[f.source] = f.nom; });
    const staged = {};
    state.staged.forEach((s) => { if (s.source) staged[s.source] = s.file.name; });
    const n = Object.keys(staged).length;
    return '<div class="expected"><div class="expected-head"><span>Fichiers attendus</span><span class="num">' + n + " / 4 sélectionnés</span></div>" +
      '<ul class="expected-list">' + EXPECTED.map((e) => {
        const has = staged[e.src];
        const hint = has ? '<span class="mono">' + esc(has) + "</span>" : cur[e.src] ? '<span class="faint">courant : <span class="mono">' + esc(cur[e.src]) + "</span></span>" : '<span class="faint">' + esc(e.fmt) + "</span>";
        return '<li class="' + (has ? "is-checked" : "") + '"><span class="exp-box">' + (has ? ico("check") : "") + "</span>" +
          '<span class="exp-name"><span>' + esc(e.label) + '</span><span class="mono">' + esc(e.prefix) + "…</span></span>" +
          '<span class="exp-file">' + hint + "</span></li>";
      }).join("") + "</ul></div>";
  }

  /* ======================================================================
   * Vue : À traiter
   * ==================================================================== */

  function viewATraiter() {
    const r = state.rapp;
    if (!r && state.booting) return '<div class="loading-block"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>';
    if (!r) return viewWelcome();
    let html = "";
    const c = counts();

    if (r.statut === "BLOQUE") {
      const bl = (r.journal || []).filter((j) => j.niveau === "BLOQUANT");
      const done = bl.filter((_, i) => state.blockedDone[i]).length;
      html += '<section class="blocked" aria-labelledby="blocked-title"><div class="blocked-head">' + ico("blocked") +
        '<div><h2 id="blocked-title">Rapprochement bloqué : ' + esc(plural(bl.length, "point à corriger", "points à corriger")) + "</h2>" +
        "<p>Aucun suspens n'est calculé tant qu'un fichier est refusé : un rapprochement partiel cacherait de vrais suspens. Corrigez puis relancez." +
        (bl.length ? ' <span class="num">' + done + " / " + bl.length + " fait" + (done > 1 ? "s" : "") + "</span>" : "") + "</p></div></div>" +
        '<ul class="blocked-list">' + bl.map((b, i) => {
          const isDone = !!state.blockedDone[i];
          return '<li class="blocked-item' + (isDone ? " is-done" : "") + '"><input class="check" type="checkbox" data-blk="' + i + '"' + (isDone ? " checked" : "") + ' aria-label="Marquer comme corrigé">' +
            '<div><div class="bi-meta"><span class="mono">' + esc(b.fichier) + ":" + esc(b.ligne) + '</span><span class="mono faint">' + esc(b.regle) + "</span></div>" +
            '<p class="bi-motif">' + esc(b.motif) + "</p>" +
            (b.brut ? '<p class="mono faint">' + esc(b.brut) + "</p>" : "") +
            '<div class="remede"><div class="remede-label">Remède</div><div class="remede-text">' + esc(b.remede || "Corriger le fichier source puis relancer.") + "</div></div></div></li>";
        }).join("") + "</ul></section>";
    }

    html += '<div class="kpis">' +
      kpi("Suspens", c.total, "", "suspens", r.statut === "BLOQUE" ? "non calculés" : plural(((r.synthese && r.synthese.par_fonds) || []).length, "fonds touché", "fonds touchés")) +
      kpi("Critiques", c.crit, "k-crit" + (c.crit ? " is-hot" : ""), "sec-critique", "risque CSDR") +
      kpi("À relever", c.rel, "k-warn", "sec-a_relever", "à corriger aujourd'hui") +
      kpi("En attente", c.att, "k-ok", "sec-en_attente", "dénouement à venir") +
      kpi("Signalements", c.sig, "k-warn", "journal-SIGNALE", "lignes douteuses") +
      kpi("Exclusions", c.excl, "", "journal-EXCLU", "règles du client") +
      "</div>";

    if (r.statut !== "BLOQUE") {
      const sus = r.suspens || [];
      html += triSection("critique", "sec-crit", "Critique : risque CSDR", "Opération non dénouée à sa date prévue : pénalités possibles, à traiter en premier.", sus, "Aucun risque CSDR détecté");
      html += triSection("a_relever", "sec-warn", "À relever maintenant", "Absences, mauvais dépositaire, écarts non expliqués ou signalés.", sus, "Rien à relever : tous les écarts sont expliqués");
      html += triSection("en_attente", "sec-ok", "En attente de dénouement", "Écart entièrement expliqué par une opération en attente : surveiller le dénouement.", sus, "Aucun écart en attente de dénouement");
    }

    const hors = (r.journal || []).filter((j) => j.niveau === "SIGNALE" || j.niveau === "EXCLU");
    if (hors.length) {
      html += '<section class="section"><div class="section-head"><span class="section-mark"></span><h3>Anomalies hors suspens</h3><span class="count">' + hors.length + "</span>" +
        '<p><button class="link-btn" type="button" data-go="journal">Ouvrir le journal de nettoyage</button></p></div>' +
        '<div class="grid-wrap"><table class="grid grid-compact"><thead><tr><th>Source</th><th>Niveau</th><th>Règle</th><th>Motif</th></tr></thead><tbody>' +
        hors.map((j) => '<tr><td class="mono nowrap">' + esc(j.fichier) + ":" + esc(j.ligne) + '</td><td><span class="pill ' + LEVEL_INFO[j.niveau].pill + '">' + esc(LEVEL_INFO[j.niveau].label) + '</span></td><td class="mono nowrap">' + esc(j.regle) + "</td><td>" + esc(j.motif) + "</td></tr>").join("") +
        "</tbody></table></div></section>";
    }
    return '<div class="view-narrow">' + html + "</div>";
  }

  function kpi(label, value, cls, target, sub) {
    return '<button type="button" class="kpi ' + cls + '" data-kpi="' + esc(target) + '"><span class="kpi-label"><span class="kdot"></span>' + esc(label) + '</span><span class="kpi-value">' + esc(value) + '</span><span class="kpi-sub">' + esc(sub) + "</span></button>";
  }

  function triSection(prio, cls, title, desc, all, emptyText) {
    const list = all.filter((s) => s.priorite === prio);
    const done = list.filter((s) => getStatut(s) === "traite").length;
    let html = '<section class="section ' + cls + '" id="sec-' + prio + '"><div class="section-head"><span class="section-mark"></span><h3>' + esc(title) + '</h3><span class="count">' + list.length + "</span>" +
      (done ? '<span class="pill pill-ok no-dot">' + done + " traité" + (done > 1 ? "s" : "") + "</span>" : "") +
      "<p>" + esc(desc) + "</p></div>";
    if (!list.length) {
      return html + '<div class="empty">' + ico("check-circle") + "<div><strong>" + esc(emptyText) + "</strong></div></div></section>";
    }
    const ids = list.map((s) => s.id).join(",");
    html += '<div class="triage">' + list.map((s) => triRow(s, ids)).join("") + "</div></section>";
    return html;
  }

  function triRow(s, ids) {
    const flags = (s.signalements || []);
    const sub = flags.length
      ? '<span class="a-flag' + (flags.some(isCsdr) ? " is-csdr" : "") + '">' + ico(flags.some(isCsdr) ? "shield" : "alert") + "<span>" + esc(flags.join(" ; ")) + "</span></span>"
      : s.piste ? '<span class="a-piste">' + esc(s.piste) + "</span>" : "";
    return '<button type="button" class="tri-row' + (getStatut(s) === "traite" ? " is-done" : "") + '" data-open="' + esc(s.id) + '" data-list="' + esc(ids) + '">' +
      "<span>" + typeTag(s.type) + "</span>" +
      "<span>" + fundTag(s.fonds, s.entite) + "</span>" +
      '<span class="cell-title"><span class="t-name">' + esc(s.libelle_titre) + '</span><span class="t-isin mono">' + esc(s.isin) + "</span></span>" +
      "<span>" + consHtml(s.conservateur) + "</span>" +
      '<span class="qty-flow">' + qtyHtml(s.qte_pms) + '<span class="q-arrow">→</span>' + qtyHtml(s.qte_dep) + "</span>" +
      ecartHtml(s.ecart) +
      '<span class="cell-action"><span class="a-text">' + esc(s.action) + "</span>" + sub + "</span>" +
      '<span class="cell-status">' + statutPill(s) + "</span></button>";
  }

  function viewWelcome() {
    return '<div class="welcome">' +
      "<h2>Rapprochement du jour</h2>" +
      "<p>Comparez l'inventaire interne (PMS) aux relevés des trois conservateurs. L'outil liste d'abord ce qu'il faut relever et corriger tout de suite ; chaque suspens remonte jusqu'à ses lignes sources.</p>" +
      '<div class="welcome-actions"><button class="btn btn-primary" type="button" data-act="exemple">' + ico("play") + "<span>Lancer sur les fichiers du 25/09</span></button>" +
      '<button class="btn" type="button" data-act="pick">' + ico("upload") + "<span>Déposer des fichiers</span></button></div>" +
      expectedList() +
      '<div class="steps">' +
      '<div class="step"><span class="step-n">1</span><h4>Nettoyage tracé</h4><p>Chaque correction, exclusion ou blocage est inscrit au journal, ligne par ligne.</p></div>' +
      '<div class="step"><span class="step-n">2</span><h4>Rapprochement exact</h4><p>Par fonds, ISIN et conservateur, tolérance nulle, sans approximation.</p></div>' +
      '<div class="step"><span class="step-n">3</span><h4>Point de situation</h4><p>Un texte prêt à envoyer au responsable, et l\'export CSV pour Excel.</p></div>' +
      "</div></div>";
  }

  /* ======================================================================
   * Vue : Suspens (grille)
   * ==================================================================== */

  const S_COLS = [
    { key: "priorite", label: "Priorité" },
    { key: "type", label: "Type" },
    { key: "fonds", label: "Fonds" },
    { key: "libelle_titre", label: "Titre" },
    { key: "isin", label: "ISIN" },
    { key: "conservateur", label: "Cons." },
    { key: "qte_pms", label: "Qté PMS", num: true },
    { key: "qte_dep", label: "Qté cons.", num: true },
    { key: "ecart", label: "Écart", num: true },
    { key: "action", label: "Action attendue" },
    { key: "piste", label: "Piste" },
    { key: "statut", label: "Statut" },
  ];

  function viewSuspens() {
    const r = state.rapp;
    if (!r) return emptyRapp();
    if (r.statut === "BLOQUE") return blockedNotice();
    const sus = r.suspens || [];
    const uniq = (k) => Array.from(new Set(sus.map((s) => s[k]))).sort();
    const f = prefs.sFilters;
    const groups = [
      { k: "fonds", label: "Fonds", vals: uniq("fonds").map((v) => [v, v]) },
      { k: "cons", label: "Cons.", vals: uniq("conservateur").map((v) => [v, v]) },
      { k: "type", label: "Type", vals: uniq("type").map((v) => [v, v]) },
      { k: "prio", label: "Priorité", vals: Object.keys(PRIO).filter((p) => sus.some((s) => s.priorite === p)).map((p) => [p, PRIO[p].label]) },
      { k: "statut", label: "Statut", vals: Object.keys(LOCAL_STATUS).map((p) => [p, LOCAL_STATUS[p].label]) },
    ];
    const fieldOf = { fonds: "fonds", cons: "conservateur", type: "type", prio: "priorite" };
    const chips = groups.map((g) => '<span class="chip-group"><span class="chip-group-label">' + esc(g.label) + "</span>" + g.vals.map(([v, l]) => {
      const n = g.k === "statut" ? sus.filter((s) => getStatut(s) === v).length : sus.filter((s) => s[fieldOf[g.k]] === v).length;
      const on = (f[g.k] || []).indexOf(v) >= 0;
      return '<button type="button" class="chip' + (on ? " is-on" : "") + '" data-chip="' + esc(g.k) + '" data-val="' + esc(v) + '" aria-pressed="' + on + '">' + esc(l) + '<span class="chip-n">' + n + "</span></button>";
    }).join("") + "</span>").join("");

    const head = S_COLS.map((c) => {
      const on = prefs.sSort.key === c.key;
      return '<th class="sortable' + (c.num ? " r" : "") + '" data-sort="' + c.key + '" aria-sort="' + (on ? (prefs.sSort.dir > 0 ? "ascending" : "descending") : "none") + '">' + esc(c.label) + '<span class="sort-ind">' + (on ? (prefs.sSort.dir > 0 ? "↑" : "↓") : "") + "</span></th>";
    }).join("");

    return '<div class="toolbar"><label class="search">' + ico("search") + '<input id="s-q" type="search" placeholder="Rechercher un titre, un ISIN, une action…" value="' + esc(prefs.sQuery) + '" aria-label="Rechercher dans les suspens"></label>' +
      chips + '<span class="toolbar-right" id="s-count"></span></div>' +
      '<div class="grid-wrap" id="s-wrap"><table class="grid" id="s-grid"><thead><tr>' + head + '</tr></thead><tbody id="s-body"></tbody></table></div>' +
      '<p class="sheet-foot-hint"><span><kbd>↑</kbd> <kbd>↓</kbd> se déplacer</span><span><kbd>Entrée</kbd> ouvrir</span><span><kbd>Échap</kbd> fermer</span><span><kbd>/</kbd> rechercher</span></p>';
  }

  function filteredSuspens() {
    const r = state.rapp;
    if (!r) return [];
    const f = prefs.sFilters;
    const q = norm(prefs.sQuery).trim();
    let list = (r.suspens || []).filter((s) => {
      if (f.fonds.length && f.fonds.indexOf(s.fonds) < 0) return false;
      if (f.cons.length && f.cons.indexOf(s.conservateur) < 0) return false;
      if (f.type.length && f.type.indexOf(s.type) < 0) return false;
      if (f.prio.length && f.prio.indexOf(s.priorite) < 0) return false;
      if (f.statut.length && f.statut.indexOf(getStatut(s)) < 0) return false;
      if (q) {
        const hay = norm([s.id, s.isin, s.libelle_titre, s.fonds, s.entite, s.conservateur, s.type, s.libelle_type, s.action, s.piste, (s.signalements || []).join(" "), (s.sources || []).join(" ")].join(" "));
        if (q.split(/\s+/).some((t) => hay.indexOf(t) < 0)) return false;
      }
      return true;
    });
    const { key, dir } = prefs.sSort;
    const num = key === "qte_pms" || key === "qte_dep" || key === "ecart";
    list = list.slice().sort((a, b) => {
      let c;
      if (num) c = cmpDec(a[key], b[key]);
      else if (key === "priorite") c = (PRIO[a.priorite] || { order: 9 }).order - (PRIO[b.priorite] || { order: 9 }).order;
      else if (key === "statut") c = getStatut(a).localeCompare(getStatut(b));
      else c = String(a[key] || "").localeCompare(String(b[key] || ""), "fr");
      if (c === 0) c = idNum(a.id) - idNum(b.id);
      return c * dir;
    });
    return list;
  }
  function idNum(id) { const m = /\d+/.exec(id || ""); return m ? parseInt(m[0], 10) : 0; }

  function renderSuspensRows() {
    const body = $("#s-body");
    if (!body) return;
    const list = filteredSuspens();
    const total = (state.rapp.suspens || []).length;
    $("#s-count").textContent = list.length === total ? plural(total, "suspens", "suspens") : list.length + " sur " + total;
    if (state.cursor >= list.length) state.cursor = Math.max(0, list.length - 1);
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="' + S_COLS.length + '" class="grid-empty">Aucun suspens ne correspond. <button class="link-btn" type="button" data-act="reset-filters">Effacer les filtres</button></td></tr>';
      return;
    }
    const ids = list.map((s) => s.id).join(",");
    body.innerHTML = list.map((s, i) => {
      const flags = s.signalements || [];
      const p = parsePiste(s.piste);
      const piste = p ? (p.op ? '<span class="' + verdictClass(p.verdict) + '">op. n°' + esc(p.op) + "</span>" : '<span class="clip">' + esc(p.raw) + "</span>") : '<span class="faint">—</span>';
      const flag = flags.length ? ' <span class="flag-cell" title="' + esc(flags.join(" ; ")) + '">' + ico("alert", "ico-sm") + flags.length + "</span>" : "";
      const st = getStatut(s);
      return '<tr class="clickable' + (i === state.cursor ? " is-cursor" : "") + (st === "traite" ? " is-done" : "") + '" data-open="' + esc(s.id) + '" data-list="' + esc(ids) + '" data-idx="' + i + '">' +
        "<td>" + prioPill(s.priorite) + "</td><td>" + typeTag(s.type) + "</td><td>" + fundTag(s.fonds, s.entite) + "</td>" +
        '<td class="clip">' + esc(s.libelle_titre) + '</td><td class="mono nowrap">' + esc(s.isin) + "</td><td>" + consHtml(s.conservateur) + "</td>" +
        '<td class="r nowrap">' + qtyHtml(s.qte_pms) + '</td><td class="r nowrap">' + qtyHtml(s.qte_dep) + '</td><td class="r">' + ecartHtml(s.ecart) + "</td>" +
        '<td class="clip clip-action" title="' + esc(s.action) + '">' + esc(s.action) + '</td><td class="nowrap">' + piste + flag + "</td>" +
        '<td class="nowrap">' + (statutPill(s) || '<span class="faint">—</span>') + "</td></tr>";
    }).join("");
  }

  function moveCursor(delta) {
    const rows = $$("#s-body tr[data-idx]");
    if (!rows.length) return;
    state.cursor = Math.min(rows.length - 1, Math.max(0, state.cursor + delta));
    rows.forEach((tr, i) => tr.classList.toggle("is-cursor", i === state.cursor));
    rows[state.cursor].scrollIntoView({ block: "nearest" });
    if (state.sheet.open) openSheet(rows[state.cursor].getAttribute("data-open"), rows[state.cursor].getAttribute("data-list").split(","));
  }

  function blockedNotice() {
    return '<div class="state-card">' + ico("blocked") + "<div><h3>Rapprochement bloqué</h3><p>Aucun suspens n'est calculé tant qu'un fichier est refusé. La liste des corrections est dans À traiter.</p>" +
      '<div class="state-actions"><button class="btn btn-sm" type="button" data-go="a-traiter">Voir les points bloquants</button></div></div></div>';
  }

  /* ======================================================================
   * Panneau latéral (sheet)
   * ==================================================================== */

  function findSuspens(id) {
    return state.rapp && (state.rapp.suspens || []).find((s) => s.id === id);
  }

  function openSheet(id, list) {
    const s = findSuspens(id);
    if (!s) return;
    const wasOpen = state.sheet.open;
    state.sheet = { open: true, id, list: list && list.length ? list : [id], opener: wasOpen ? state.sheet.opener : document.activeElement };
    renderSheet();
    $("#sheet").hidden = false;
    $("#sheet-backdrop").hidden = false;
    if (!wasOpen) $("#sheet-close").focus();
  }

  function closeSheet() {
    if (!state.sheet.open) return;
    const opener = state.sheet.opener;
    state.sheet = { open: false, id: null, list: [] };
    $("#sheet").hidden = true;
    $("#sheet-backdrop").hidden = true;
    if (opener && document.body.contains(opener)) opener.focus();
  }

  function stepSheet(delta) {
    const { list, id } = state.sheet;
    const i = list.indexOf(id);
    const n = i + delta;
    if (n < 0 || n >= list.length) return;
    state.sheet.id = list[n];
    if (state.view === "suspens") {
      state.cursor = n;
      $$("#s-body tr[data-idx]").forEach((tr, k) => tr.classList.toggle("is-cursor", k === n));
    }
    renderSheet();
  }

  function renderSheet() {
    const s = findSuspens(state.sheet.id);
    if (!s) return;
    const { list, id } = state.sheet;
    const i = list.indexOf(id);
    $("#sheet-prev").disabled = i <= 0;
    $("#sheet-next").disabled = i >= list.length - 1;
    $("#sheet-tags").innerHTML = prioPill(s.priorite) + typeTag(s.type) + '<span class="faint num">' + esc(s.id) + (list.length > 1 ? " · " + (i + 1) + " sur " + list.length : "") + "</span>";
    $("#sheet-title").textContent = s.libelle_titre || s.isin;

    const parts = String(s.conservateur).split("→");
    const isDep = parts.length === 2;
    const consLabel = isDep ? "Chez " + parts[1] + " (attendu " + parts[0] + ")" : "Conservateur " + s.conservateur;
    const flags = s.signalements || [];
    const p = parsePiste(s.piste);
    const st = getStatut(s);

    let html = '<div class="sheet-sub"><span class="mono">' + esc(s.isin) + "</span>" + fundTag(s.fonds, s.entite) + "<span>" + esc(s.entite) + "</span>" + consHtml(s.conservateur, true) + "</div>";

    html += '<div class="compare"><div><div class="c-label">PMS</div><div class="c-value' + (s.qte_pms == null ? " is-absent" : "") + '">' + (s.qte_pms == null ? "absent" : esc(fmtDec(s.qte_pms))) + '</div><div class="c-hint">inventaire interne</div></div>' +
      '<div><div class="c-label">' + esc(consLabel) + '</div><div class="c-value' + (s.qte_dep == null ? " is-absent" : "") + '">' + (s.qte_dep == null ? "absent" : esc(fmtDec(s.qte_dep))) + '</div><div class="c-hint">' + esc(isDep ? consName(parts[1]) : consName(s.conservateur)) + "</div></div>" +
      '<div class="c-ecart"><div class="c-label">Écart</div><div class="c-value">' + ecartHtml(s.ecart) + '</div><div class="c-hint">PMS − conservateur</div></div></div>';

    html += '<div class="sheet-section"><h4>Action attendue</h4><div class="action-box">' + ico("target") + "<div><strong>" + esc(s.action) + "</strong><p>" + esc(s.libelle_type || typeLabel(s.type)) + "</p></div></div></div>";

    html += '<div class="sheet-section"><h4>Piste explicative</h4>';
    if (!p) {
      html += '<p class="muted">Aucune opération en attente dans la base de gestion n\'explique cet écart.</p>';
    } else if (!p.op) {
      html += "<p>" + esc(p.raw) + "</p>";
    } else {
      html += '<dl class="kv"><dt>Opération</dt><dd class="num">n°' + esc(p.op) + "</dd><dt>Sens</dt><dd>" + esc(p.sens === "ACHAT" ? "Achat" : "Vente") + '</dd><dt>Quantité</dt><dd class="num">' + esc(p.qte) + '</dd><dt>Dénouement</dt><dd class="num">' + esc(p.den) + "</dd>" +
        (p.verdict ? '<dt>Verdict</dt><dd class="' + verdictClass(p.verdict) + '">' + esc(p.verdict.charAt(0).toUpperCase() + p.verdict.slice(1)) + "</dd>" : "") + "</dl>";
    }
    html += "</div>";

    html += '<div class="sheet-section"><h4>Signalements</h4>' + (flags.length
      ? '<ul class="flags">' + flags.map((f) => '<li class="' + (isCsdr(f) ? "is-csdr" : "") + '">' + ico(isCsdr(f) ? "shield" : "alert") + "<span>" + esc(f) + "</span></li>").join("") + "</ul>"
      : '<p class="muted">Aucun signalement.</p>') + "</div>";

    html += '<div class="sheet-section"><h4>Traçabilité : lignes sources</h4><ul class="trace">' + (s.sources || []).map((src) => {
      const k = String(src).lastIndexOf(":");
      const file = k > 0 ? src.slice(0, k) : src;
      const line = k > 0 ? src.slice(k + 1) : "";
      const kind = sourceOf(file) || "?";
      return '<li><span class="src-kind"><span class="cons-code">' + esc(kind === "PMS" ? "P" : kind) + '</span></span><span class="src-file mono" title="' + esc(file) + '">' + esc(file) + "</span>" +
        (line ? '<span class="src-line mono">ligne ' + esc(line) + "</span>" : "") + "</li>";
    }).join("") + "</ul></div>";

    html += '<div class="sheet-section"><h4>Statut de traitement (sur ce poste)</h4><div class="seg" role="group" aria-label="Statut de traitement">' +
      Object.keys(LOCAL_STATUS).map((k) => '<button type="button" class="' + (LOCAL_STATUS[k].seg || "") + (st === k ? " is-on" : "") + '" data-statut="' + k + '" aria-pressed="' + (st === k) + '">' + esc(LOCAL_STATUS[k].label) + "</button>").join("") + "</div></div>";

    html += '<p class="sheet-foot-hint"><span><kbd>↑</kbd> <kbd>↓</kbd> suspens précédent ou suivant</span><span><kbd>Échap</kbd> fermer</span></p>';
    const body = $("#sheet-body");
    body.innerHTML = html;
  }

  /* ======================================================================
   * Vue : Point de situation
   * ==================================================================== */

  function viewPoint() {
    const r = state.rapp;
    if (!r) return emptyRapp();
    const cached = state.point[r.id];
    if (cached === undefined && !state.pointError) {
      getPoint().then(() => { if (state.view === "point") renderView(); }).catch((e) => { state.pointError = e; if (state.view === "point") renderView(); });
    }
    let text;
    if (state.pointError) text = '<div class="err-box">' + ico("alert") + "<div><strong>" + esc(errorTitle(state.pointError)) + "</strong><p>" + esc(errorSub(state.pointError)) + '</p><p><button class="link-btn" type="button" data-act="retry-point">Réessayer</button></p></div></div>';
    else if (cached === undefined) text = '<div class="loading-block"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>';
    else text = "<pre>" + esc(cached) + "</pre>";

    const csvOk = r.statut !== "BLOQUE";
    const left = '<div class="point-text"><div class="point-text-head"><span>Texte prêt à coller dans un mail</span><span>' +
      '<button class="btn btn-sm" type="button" data-act="copy-point">' + ico("copy") + "<span>Copier</span></button> " +
      '<a class="btn btn-sm" href="' + esc(csvOk ? csvUrl() : "#") + '" aria-disabled="' + !csvOk + '" download>' + ico("download") + "<span>Exporter CSV</span></a></span></div>" + text + "</div>";

    return '<div class="point-grid">' + left + "<div>" + matrixCard() + typeCard() + journalCard() + "</div></div>";
  }

  function matrixCard() {
    const r = state.rapp;
    const sus = r.suspens || [];
    const fonds = [];
    const seen = {};
    const addF = (code, entite) => { if (code && !seen[code]) { seen[code] = true; fonds.push({ code, entite }); } };
    ((state.param && state.param.fonds) || []).forEach((f) => addF(f.code, f.entite));
    ((r.synthese && r.synthese.par_fonds) || []).forEach((f) => addF(f.code, f.entite));
    sus.forEach((s) => addF(s.fonds, s.entite));
    const cols = ((state.param && state.param.conservateurs) || [{ code: "A" }, { code: "B" }, { code: "C" }]).map((c) => c.code);
    sus.forEach((s) => { if (cols.indexOf(s.conservateur) < 0) cols.push(s.conservateur); });

    const head = "<tr><th>Fonds</th>" + cols.map((c) => '<th title="' + esc(c.indexOf("→") > 0 ? "Mauvais dépositaire (DEP)" : consName(c)) + '">' + esc(c) + "</th>").join("") + "</tr>";
    const rows = fonds.map((f) => "<tr><td title=\"" + esc(f.entite || "") + "\">" + esc(f.code) + "</td>" + cols.map((c) => {
      const cell = sus.filter((s) => s.fonds === f.code && s.conservateur === c);
      if (!cell.length) return '<td><div class="mcell is-zero"><span class="mc-n">0</span></div></td>';
      const sorted = cell.slice().sort((a, b) => (PRIO[a.priorite] || { order: 9 }).order - (PRIO[b.priorite] || { order: 9 }).order);
      return '<td><button type="button" class="mcell" data-matrix-f="' + esc(f.code) + '" data-matrix-c="' + esc(c) + '" title="Voir ces suspens"><span class="mc-n">' + cell.length + '</span><span class="mc-dots">' +
        sorted.map((s) => '<span class="mc-dot p-' + esc(s.priorite) + '"></span>').join("") + "</span></button></td>";
    }).join("") + "</tr>").join("");

    return '<div class="side-card"><h3>Suspens par fonds et conservateur</h3>' +
      (r.statut === "BLOQUE" ? '<p class="muted">Non calculés : rapprochement bloqué.</p>' :
        '<table class="matrix">' + head + rows + "</table>" +
        '<div class="legend"><span><span class="mc-dot p-critique"></span>critique</span><span><span class="mc-dot p-a_relever"></span>à relever</span><span><span class="mc-dot p-en_attente"></span>en attente</span></div>') +
      "</div>";
  }

  function typeCard() {
    const pt = (state.rapp.synthese && state.rapp.synthese.par_type) || {};
    const keys = Object.keys(pt);
    if (!keys.length) return "";
    return '<div class="side-card"><h3>Par type d\'écart</h3><ul class="stat-list">' + keys.map((k) => "<li><span>" + typeTag(k) + ' <span class="muted">' + esc(typeLabel(k)) + '</span></span><span class="num">' + esc(pt[k]) + "</span></li>").join("") + "</ul></div>";
  }

  function journalCard() {
    const j = (state.rapp.synthese && state.rapp.synthese.journal) || {};
    return '<div class="side-card"><h3>Journal de nettoyage</h3><ul class="stat-list">' + LEVELS.map((l) => '<li><span class="pill ' + LEVEL_INFO[l].pill + '">' + esc(LEVEL_INFO[l].label) + '</span><span class="num">' + esc(j[l] || 0) + "</span></li>").join("") + "</ul></div>";
  }

  /* ======================================================================
   * Vue : Journal de nettoyage
   * ==================================================================== */

  function viewJournal() {
    const r = state.rapp;
    if (!r) return emptyRapp();
    const j = r.journal || [];
    const chips = LEVELS.map((l) => {
      const n = j.filter((x) => x.niveau === l).length;
      const on = prefs.jLevels.indexOf(l) >= 0;
      return '<button type="button" class="chip lvl-' + l + (on ? " is-on" : "") + '" data-level="' + l + '" aria-pressed="' + on + '">' + esc(LEVEL_INFO[l].label) + '<span class="chip-n">' + n + "</span></button>";
    }).join("");
    return '<div class="lvl-legend">' + LEVELS.map((l) => '<div><span class="pill ' + LEVEL_INFO[l].pill + '">' + esc(LEVEL_INFO[l].label) + "</span><br>" + esc(LEVEL_INFO[l].text) + "</div>").join("") + "</div>" +
      '<div class="toolbar"><label class="search">' + ico("search") + '<input id="j-q" type="search" placeholder="Rechercher un fichier, une règle, une valeur…" value="' + esc(prefs.jQuery) + '" aria-label="Rechercher dans le journal"></label>' +
      '<span class="chip-group"><span class="chip-group-label">Niveau</span>' + chips + '</span><span class="toolbar-right" id="j-count"></span></div>' +
      '<div class="grid-wrap"><table class="grid"><thead><tr><th>Fichier : ligne</th><th>Niveau</th><th>Règle</th><th>Brut → retenu</th><th>Motif</th><th>Remède</th></tr></thead><tbody id="j-body"></tbody></table></div>';
  }

  function renderJournalRows() {
    const body = $("#j-body");
    if (!body) return;
    const all = state.rapp.journal || [];
    const q = norm(prefs.jQuery).trim();
    const list = all.filter((x) => {
      if (prefs.jLevels.indexOf(x.niveau) < 0) return false;
      if (!q) return true;
      const hay = norm([x.fichier, x.ligne, x.niveau, x.regle, x.brut, x.retenu, x.motif, x.remede].join(" "));
      return q.split(/\s+/).every((t) => hay.indexOf(t) >= 0);
    }).sort((a, b) => LEVELS.indexOf(a.niveau) - LEVELS.indexOf(b.niveau) || String(a.fichier).localeCompare(String(b.fichier)) || (a.ligne || 0) - (b.ligne || 0));
    $("#j-count").textContent = list.length + " sur " + all.length + " lignes";
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="6" class="grid-empty">Aucune ligne pour ces niveaux.</td></tr>';
      return;
    }
    body.innerHTML = list.map((x) => {
      const info = LEVEL_INFO[x.niveau] || { pill: "pill-neutral", label: x.niveau };
      return '<tr><td class="mono nowrap">' + esc(x.fichier) + ":" + esc(x.ligne) + '</td><td><span class="pill ' + info.pill + '">' + esc(info.label) + '</span></td><td class="mono nowrap">' + esc(x.regle) + "</td>" +
        '<td><div class="brut-ret mono"><span class="b" title="' + esc(x.brut) + '">' + esc(x.brut || "—") + '</span><span class="rt" title="' + esc(x.retenu) + '">' + esc(x.retenu === "" ? "(retirée)" : x.retenu) + "</span></div></td>" +
        '<td class="wrap">' + esc(x.motif) + '</td><td class="wrap remede-cell">' + esc(x.remede) + "</td></tr>";
    }).join("");
  }

  /* ======================================================================
   * Vue : Fichiers
   * ==================================================================== */

  function viewFichiers() {
    const r = state.rapp;
    const warns = stagedWarnings();
    let staged = "";
    if (state.staged.length) {
      staged = '<div class="grid-wrap"><table class="grid grid-compact"><thead><tr><th>Source</th><th>Fichier sélectionné</th><th class="r">Taille</th><th></th></tr></thead><tbody>' +
        state.staged.map((s, i) => "<tr><td>" + (s.source ? '<span class="cons-code">' + esc(s.source === "PMS" ? "P" : s.source) + "</span>" : '<span class="pill pill-crit">inconnue</span>') + '</td><td class="mono">' + esc(s.file.name) + '</td><td class="r num nowrap">' + esc(fmtSize(s.file.size)) + '</td><td class="r"><button class="x-btn" type="button" data-unstage="' + i + '" aria-label="Retirer ' + esc(s.file.name) + '">' + ico("x", "ico-sm") + "</button></td></tr>").join("") +
        "</tbody></table>" +
        '<div class="staged-actions"><span class="muted">' + esc(plural(state.staged.length, "fichier", "fichiers")) + ", envoyés en base64 puis rapprochés</span>" +
        '<button class="btn btn-ghost btn-sm" type="button" data-act="clear-staged">Vider</button>' +
        '<button class="btn btn-primary btn-sm" id="run-upload" type="button" data-act="upload">' + '<span class="ico" data-icon="play">' + svg("play") + "</span><span>Rapprocher ces fichiers</span></button></div></div>" +
        (warns.length ? '<ul class="warn-box warn-list">' + warns.map((w) => "<li>" + ico("alert") + "<span>" + esc(w) + "</span></li>").join("") + "</ul>" : "");
    }
    let err = "";
    if (state.uploadError) {
      const e = state.uploadError;
      const det = Array.isArray(e.details) ? "<ul>" + e.details.map((d) => "<li>" + esc(typeof d === "string" ? d : JSON.stringify(d)) + "</li>").join("") + "</ul>" : e.details && typeof e.details === "object" ? '<p class="mono">' + esc(JSON.stringify(e.details)) + "</p>" : "";
      err = '<div class="err-box" role="alert">' + ico("alert") + "<div><strong>" + esc(errorTitle(e)) + ' <span class="mono faint">' + esc(e.code) + (e.status ? " · HTTP " + e.status : "") + "</span></strong><p>" + esc(errorSub(e)) + "</p>" + det + "</div></div>";
    }

    const current = r ? '<div class="grid-wrap"><table class="grid grid-compact"><thead><tr><th>Source</th><th>Fichier</th><th class="r">Taille</th><th>SHA-256</th></tr></thead><tbody>' +
      (r.fichiers || []).map((f) => "<tr><td><span class=\"cons-code\">" + esc(f.source === "PMS" ? "P" : f.source) + '</span></td><td class="mono">' + esc(f.nom) + '</td><td class="r num nowrap">' + esc(fmtSize(f.taille)) + '</td><td class="mono faint" title="' + esc(f.sha256) + '">' + esc(String(f.sha256 || "").slice(0, 12)) + "…</td></tr>").join("") +
      "</tbody></table></div>" : '<p class="muted">Aucun rapprochement chargé.</p>';

    return '<div class="view-narrow"><div class="dropzone" id="dropzone" role="button" tabindex="0" data-act="pick">' + ico("upload", "ico-lg") +
      "<strong>Glissez les fichiers du jour ici, ou cliquez pour les choisir</strong>" +
      '<span>Jusqu\'à 8 fichiers .csv, .xlsx, .txt ou .xml, 5 Mo chacun. Rien n\'est envoyé avant votre validation.</span></div>' +
      err +
      '<div class="files-grid"><div>' + expectedList() + (staged ? '<div class="sheet-section">' + staged + "</div>" : "") + "</div>" +
      '<div><div class="section-head"><h3>Fichiers du rapprochement courant</h3>' + (r ? '<span class="count">' + esc(fmtStamp(r.cree_le)) + "</span>" : "") + "</div>" + current +
      '<p class="sheet-foot-hint">L\'empreinte SHA-256 identifie exactement le fichier rapproché : utile pour retrouver la version reçue du conservateur.</p></div></div></div>';
  }

  /* ======================================================================
   * Vue : Questions sur la base de gestion (besoin 2)
   * ======================================================================
   *
   * Comment brancher le besoin 2 :
   *  1. Côté back, implémenter POST /api/questions (docs/API.md) : il renvoie
   *     aujourd'hui 501 NON_DISPONIBLE. Dès qu'il répond 200 avec l'objet
   *     { question, reponse, chiffres[], requete_sql, lignes_sources[], confiance,
   *       avertissements[] }, askQuestion() le stocke dans state.q.data et
   *     renderAnswer() l'affiche. Aucun changement front n'est nécessaire.
   *  2. Les valeurs de « chiffres » sont des chaînes décimales : fmtDec() les
   *     formate sans float. « confiance » ∈ haute | moyenne | basse ; sous « haute »
   *     la réponse est présentée comme à vérifier (revue humaine).
   *  3. Pour ajouter une question d'exemple, compléter Q_EXAMPLES.
   *  4. Retirer le badge « bientôt » de la navigation dans index.html.
   */

  const Q_EXAMPLES = [
    "Encours valorisé du fonds OBL au cours de clôture",
    "Tombées d'échéances à venir",
    "Concentration par émetteur",
    "Opérations non dénouées",
    "Origine d'un suspens",
  ];

  /* Exemple tiré du contrat : sert uniquement à prévisualiser le rendu. Chiffres fictifs. */
  const Q_PREVIEW = {
    question: "Encours valorisé du fonds OBL ?",
    reponse: "L'encours valorisé d'ORSAY OBLIGATIONS au 25/09/2026 est de 1 234 567,89 EUR.",
    chiffres: [{ libelle: "Encours valorisé", valeur: "1234567.89", unite: "EUR" }],
    requete_sql: "SELECT ... FROM positions JOIN cours ...",
    lignes_sources: [{ table: "positions", valeurs: { isin: "FR0000011488", quantite: "40000" } }],
    confiance: "haute",
    avertissements: ["Obligations valorisées au pied de coupon, sans coupon couru."],
  };

  function viewQuestions() {
    const q = state.q;
    let out = "";
    if (q.status === "loading") out = '<div class="answer"><div class="answer-body"><div class="loading-block"><div class="skeleton"></div><div class="skeleton"></div></div></div></div>';
    else if (q.status === "answer" && q.data) out = renderAnswer(q.data);
    else if (q.status === "unavailable") {
      out = '<div class="state-card">' + ico("database") + "<div><h3>Module en préparation</h3>" +
        "<p>Les questions sur la base de gestion arrivent dans une prochaine version. Chaque chiffre sera affiché avec la requête SQL qui l'a produit et les lignes sources, pour être vérifiable par le RCCI.</p>" +
        (q.error && q.error.message ? '<p class="faint">Réponse du serveur : ' + esc(q.error.message) + "</p>" : "") +
        '<div class="state-actions"><button class="btn btn-sm" type="button" data-act="q-preview">' + ico("file-text") + "<span>" + (q.preview ? "Masquer" : "Voir") + " le format de réponse prévu</span></button></div></div></div>";
    } else if (q.status === "error" && q.error) {
      out = '<div class="err-box">' + ico("alert") + "<div><strong>" + esc(errorTitle(q.error)) + "</strong><p>" + esc(errorSub(q.error)) + "</p></div></div>";
    }
    if (q.preview) out += '<p class="preview-flag">' + ico("info", "ico-sm") + "Aperçu du format, avec l'exemple du contrat d'API : chiffres fictifs.</p>" + renderAnswer(Q_PREVIEW);

    return '<div class="ask"><div class="page-intro"><div><h2>Interroger la base de gestion</h2><p>Pour les gérants et le RCCI. Posez une question en français : la réponse cite ses chiffres, la requête SQL exécutée en lecture seule et les lignes sources.</p></div></div>' +
      '<form class="ask-form" id="ask-form"><textarea id="q-input" rows="2" placeholder="Par exemple : encours valorisé du fonds OBL au cours de clôture" aria-label="Votre question">' + esc(q.text) + "</textarea>" +
      '<button class="btn btn-primary" type="submit" id="q-send"' + (q.status === "loading" ? " disabled" : "") + ">" + ico("send") + "<span>Demander</span></button></form>" +
      '<div class="examples">' + Q_EXAMPLES.map((e) => '<button type="button" class="chip" data-example="' + esc(e) + '">' + esc(e) + "</button>").join("") + "</div>" +
      out + "</div>";
  }

  function renderAnswer(a) {
    const conf = String(a.confiance || "").toLowerCase();
    const confPill = conf === "haute" ? "pill-ok" : conf === "moyenne" ? "pill-warn" : "pill-crit";
    const figures = (a.chiffres || []).length ? '<div class="figures">' + a.chiffres.map((c) => '<div class="figure"><div class="f-label">' + esc(c.libelle) + '</div><div class="f-value">' + esc(fmtDec(c.valeur)) + '<span class="f-unit">' + esc(c.unite || "") + "</span></div></div>").join("") + "</div>" : "";
    const lines = a.lignes_sources || [];
    let srcTable = "";
    if (lines.length) {
      const cols = [];
      lines.forEach((l) => Object.keys(l.valeurs || {}).forEach((k) => { if (cols.indexOf(k) < 0) cols.push(k); }));
      srcTable = '<div><div class="sheet-section"><h4>Lignes sources (' + lines.length + ')</h4></div><div class="grid-wrap"><table class="grid grid-compact"><thead><tr><th>Table</th>' + cols.map((c) => "<th>" + esc(c) + "</th>").join("") + "</tr></thead><tbody>" +
        lines.map((l) => '<tr><td class="mono">' + esc(l.table) + "</td>" + cols.map((c) => { const v = (l.valeurs || {})[c]; return '<td class="mono">' + esc(v === undefined ? "" : v) + "</td>"; }).join("") + "</tr>").join("") +
        "</tbody></table></div></div>";
    }
    const warns = (a.avertissements || []).length ? '<ul class="warn-list">' + a.avertissements.map((w) => "<li>" + ico("alert") + "<span>" + esc(w) + "</span></li>").join("") + "</ul>" : "";
    return '<article class="answer"><div class="answer-head"><span class="answer-q">' + esc(a.question) + '</span><span class="pill ' + confPill + '">Confiance ' + esc(conf || "inconnue") + "</span></div>" +
      '<div class="answer-body"><p class="answer-text">' + esc(a.reponse) + "</p>" +
      (conf && conf !== "haute" ? '<p class="warn-line">Confiance insuffisante : réponse à faire valider par un humain avant diffusion.</p>' : "") +
      figures + warns +
      (a.requete_sql ? '<details class="sql"><summary>' + ico("chevron-right", "ico-sm") + "Requête SQL exécutée (lecture seule)</summary><pre class=\"mono\">" + esc(a.requete_sql) + "</pre></details>" : "") +
      srcTable + "</div></article>";
  }

  async function askQuestion(text) {
    const t = String(text || "").trim();
    if (!t) return;
    state.q = { text: t, status: "loading", data: null, error: null, preview: state.q.preview };
    renderView();
    try {
      const res = await api("/api/questions", { method: "POST", json: { question: t } });
      state.q.status = "answer";
      state.q.data = res;
    } catch (e) {
      state.q.error = e;
      state.q.status = e.status === 501 ? "unavailable" : "error";
      if (e.status !== 501) toast(errorTitle(e), "err", errorSub(e));
    }
    if (state.view === "questions") renderView();
  }

  /* ======================================================================
   * Vue : Paramétrage
   * ==================================================================== */

  function viewParam() {
    const p = state.param;
    if (!p) {
      if (state.paramError) return '<div class="err-box">' + ico("alert") + "<div><strong>Paramétrage indisponible</strong><p>" + esc(errorSub(state.paramError)) + '</p><p><button class="link-btn" type="button" data-act="retry-param">Réessayer</button></p></div></div>';
      return '<div class="loading-block"><div class="skeleton"></div><div class="skeleton"></div></div>';
    }
    const pt = (state.rapp && state.rapp.synthese && state.rapp.synthese.par_type) || {};
    const types = '<div class="param-block param-wide"><h3>Types d\'écarts et action attendue <span class="faint">lus dans TYPES_ECARTS, jamais codés en dur</span></h3><div class="grid-wrap"><table class="grid grid-compact"><thead><tr><th>Code</th><th>Libellé</th><th>Action attendue</th>' + (state.rapp ? '<th class="r">Dans ce rapprochement</th>' : "") + "</tr></thead><tbody>" +
      (p.types_ecarts || []).map((t) => "<tr><td>" + typeTag(t.code) + "</td><td>" + esc(t.libelle) + "</td><td>" + esc(t.action_attendue) + "</td>" + (state.rapp ? '<td class="r num">' + esc(pt[t.code] || 0) + "</td>" : "") + "</tr>").join("") +
      "</tbody></table></div></div>";

    const ref = '<div class="param-block"><h3>Fonds <span class="faint">' + esc((p.fonds || []).length) + "</span></h3>" + simpleTable(["Code", "Entité"], (p.fonds || []).map((f) => [fundTag(f.code, f.entite), esc(f.entite)])) + "</div>" +
      '<div class="param-block"><h3>Conservateurs <span class="faint">' + esc((p.conservateurs || []).length) + "</span></h3>" + simpleTable(["Code", "Nom"], (p.conservateurs || []).map((c) => ['<span class="cons-code">' + esc(c.code) + "</span>", esc(c.nom)])) + "</div>";

    const transcos = Object.keys(p.transcos || {}).map((name) => {
      const rows = p.transcos[name] || [];
      const cols = [];
      rows.forEach((r) => Object.keys(r).forEach((k) => { if (cols.indexOf(k) < 0) cols.push(k); }));
      return '<div class="param-block"><h3><span class="mono">' + esc(name) + '</span> <span class="faint">' + rows.length + " entrée" + (rows.length > 1 ? "s" : "") + "</span></h3>" +
        (rows.length ? simpleTable(cols, rows.map((r) => cols.map((c) => '<span class="' + (c === "cle" || c === "compte" ? "mono" : "") + '">' + esc(r[c] === undefined ? "" : r[c]) + "</span>"))) : '<p class="muted">Table vide.</p>') + "</div>";
    }).join("");

    const excl = '<div class="param-block param-wide"><h3>Règles d\'exclusion <span class="faint">appliquées avant rapprochement, chaque ligne exclue est tracée au journal</span></h3><ul class="excl-list">' +
      (p.exclusions || []).map((e) => "<li>" + ico("ban") + "<span>" + esc(e) + "</span></li>").join("") + "</ul></div>";

    return '<div class="page-intro"><div><h2>Référentiel du rapprochement</h2><p>Lecture seule, tiré de parametrage.xlsx. Arrêté du ' + esc(fmtDate(p.date_arrete)) + ". Pour modifier une règle, mettez à jour le fichier de paramétrage.</p></div></div>" +
      '<div class="param-grid">' + types + ref + transcos + excl + "</div>";
  }

  function simpleTable(head, rows) {
    return '<div class="grid-wrap"><table class="grid grid-compact"><thead><tr>' + head.map((h) => "<th>" + esc(h) + "</th>").join("") + "</tr></thead><tbody>" +
      rows.map((r) => "<tr>" + r.map((c) => "<td>" + c + "</td>").join("") + "</tr>").join("") + "</tbody></table></div>";
  }

  /* ======================================================================
   * Rendu de la vue
   * ==================================================================== */

  function renderView() {
    const v = $("#view");
    let html;
    switch (state.view) {
      case "suspens": html = viewSuspens(); break;
      case "point": html = viewPoint(); break;
      case "journal": html = viewJournal(); break;
      case "fichiers": html = viewFichiers(); break;
      case "questions": html = viewQuestions(); break;
      case "parametrage": html = viewParam(); break;
      default: html = viewATraiter();
    }
    v.innerHTML = html;
    if (state.view === "suspens") renderSuspensRows();
    if (state.view === "journal") renderJournalRows();
  }

  /* ======================================================================
   * Palette de commandes
   * ==================================================================== */

  const pal = { items: [], active: 0 };

  function openPalette() {
    $("#palette-backdrop").hidden = false;
    const inp = $("#palette-input");
    inp.value = "";
    renderPalette();
    inp.focus();
  }
  function closePalette() {
    $("#palette-backdrop").hidden = true;
  }
  function paletteOpen() { return !$("#palette-backdrop").hidden; }

  function paletteItems(q) {
    const nq = norm(q).trim();
    const match = (s) => !nq || nq.split(/\s+/).every((t) => norm(s).indexOf(t) >= 0);
    const items = [];
    Object.keys(VIEWS).forEach((k) => {
      const label = "Aller à " + VIEWS[k].title;
      if (match(label + " " + VIEWS[k].group)) items.push({ group: "Vues", icon: VIEWS[k].icon, label, hint: VIEWS[k].group, run: () => navigate(k) });
    });
    const acts = [
      { label: $("#act-exemple-label").textContent, icon: "play", run: runExemple },
      { label: "Déposer des fichiers", icon: "upload", run: () => $("#file-input").click() },
      { label: "Copier le point de situation", icon: "copy", run: copyPoint, off: !state.rapp },
      { label: "Exporter les suspens en CSV", icon: "download", run: () => { window.location.href = csvUrl(); }, off: !state.rapp || state.rapp.statut === "BLOQUE" },
    ];
    acts.forEach((a) => { if (!a.off && match(a.label)) items.push({ group: "Actions", icon: a.icon, label: a.label, run: a.run }); });
    if (state.rapp && nq) {
      (state.rapp.suspens || []).forEach((s) => {
        if (match([s.isin, s.libelle_titre, s.fonds, s.type, s.conservateur, s.id].join(" "))) {
          items.push({ group: "Suspens", icon: "rows", label: s.libelle_titre + "  " + s.isin, hint: s.fonds + " · " + s.type + " · " + s.conservateur, run: () => openSheet(s.id, [s.id]) });
        }
      });
    }
    return items;
  }

  function renderPalette() {
    pal.items = paletteItems($("#palette-input").value);
    pal.active = Math.min(pal.active, Math.max(0, pal.items.length - 1));
    const ul = $("#palette-list");
    if (!pal.items.length) { ul.innerHTML = '<li class="pal-empty">Aucun résultat</li>'; return; }
    let last = "";
    ul.innerHTML = pal.items.map((it, i) => {
      const g = it.group !== last ? '<li class="pal-group" role="presentation">' + esc(it.group) + "</li>" : "";
      last = it.group;
      return g + '<li class="pal-item' + (i === pal.active ? " is-active" : "") + '" role="option" aria-selected="' + (i === pal.active) + '" data-pal="' + i + '">' + ico(it.icon) + '<span class="pal-label">' + esc(it.label) + "</span>" + (it.hint ? '<span class="pal-hint">' + esc(it.hint) + "</span>" : "") + "</li>";
    }).join("");
    const act = $(".pal-item.is-active", ul);
    if (act) act.scrollIntoView({ block: "nearest" });
  }

  function runPalette(i) {
    const it = pal.items[i];
    if (!it) return;
    closePalette();
    it.run();
  }

  /* ======================================================================
   * Événements
   * ==================================================================== */

  function bind() {
    window.addEventListener("hashchange", route);

    $("#act-exemple").addEventListener("click", runExemple);
    $("#act-deposer").addEventListener("click", () => $("#file-input").click());
    $("#act-copier").addEventListener("click", copyPoint);
    $("#act-csv").addEventListener("click", (e) => {
      if ($("#act-csv").getAttribute("aria-disabled") === "true") e.preventDefault();
      else toast("Export CSV lancé", "ok", "Séparateur « ; », ouverture directe dans Excel.");
    });
    $("#file-input").addEventListener("change", (e) => { stageFiles(e.target.files); e.target.value = ""; });
    $("#open-palette").addEventListener("click", openPalette);
    $("#sb-toggle").addEventListener("click", () => $("#app").classList.toggle("sb-open"));
    $("#sb-scrim").addEventListener("click", () => $("#app").classList.remove("sb-open"));
    $("#workspace").addEventListener("click", () => toast("Orsay Gestion, middle office", "info", "Un seul espace configuré sur ce poste."));

    $("#history").addEventListener("click", (e) => {
      const b = e.target.closest("[data-hist]");
      if (b) loadRapp(b.getAttribute("data-hist"));
    });

    // Sheet
    $("#sheet-close").addEventListener("click", closeSheet);
    $("#sheet-backdrop").addEventListener("click", closeSheet);
    $("#sheet-prev").addEventListener("click", () => stepSheet(-1));
    $("#sheet-next").addEventListener("click", () => stepSheet(1));
    $("#sheet-body").addEventListener("click", (e) => {
      const b = e.target.closest("[data-statut]");
      if (!b) return;
      const s = findSuspens(state.sheet.id);
      if (!s) return;
      setStatut(s, b.getAttribute("data-statut"));
      renderSheet();
      if (state.view === "suspens") renderSuspensRows();
      else if (state.view === "a-traiter") { const sc = $("#view").scrollTop; renderView(); $("#view").scrollTop = sc; }
      toast("Statut : " + LOCAL_STATUS[b.getAttribute("data-statut")].label, "ok", "Enregistré sur ce poste uniquement.");
    });

    // Palette
    $("#palette-backdrop").addEventListener("click", (e) => { if (e.target === e.currentTarget) closePalette(); });
    $("#palette-input").addEventListener("input", () => { pal.active = 0; renderPalette(); });
    $("#palette-input").addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); pal.active = Math.min(pal.items.length - 1, pal.active + 1); renderPalette(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); pal.active = Math.max(0, pal.active - 1); renderPalette(); }
      else if (e.key === "Enter") { e.preventDefault(); runPalette(pal.active); }
      else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
    });
    $("#palette-list").addEventListener("mousemove", (e) => {
      const li = e.target.closest("[data-pal]");
      if (!li) return;
      const i = +li.getAttribute("data-pal");
      if (i !== pal.active) { pal.active = i; $$(".pal-item", $("#palette-list")).forEach((x) => x.classList.toggle("is-active", +x.getAttribute("data-pal") === i)); }
    });
    $("#palette-list").addEventListener("click", (e) => {
      const li = e.target.closest("[data-pal]");
      if (li) runPalette(+li.getAttribute("data-pal"));
    });

    // Vue : délégation
    const view = $("#view");
    view.addEventListener("click", onViewClick);
    view.addEventListener("input", onViewInput);
    view.addEventListener("change", (e) => {
      const c = e.target.closest("[data-blk]");
      if (c) {
        state.blockedDone[c.getAttribute("data-blk")] = c.checked;
        const sc = view.scrollTop; renderView(); view.scrollTop = sc;
      }
    });
    view.addEventListener("submit", (e) => {
      if (e.target.id === "ask-form") { e.preventDefault(); askQuestion($("#q-input").value); }
    });
    view.addEventListener("keydown", (e) => {
      if (e.target.id === "q-input" && e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askQuestion(e.target.value); }
      if (e.target.id === "dropzone" && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); $("#file-input").click(); }
    });

    // Glisser-déposer global
    let depth = 0;
    const hasFiles = (e) => e.dataTransfer && Array.from(e.dataTransfer.types || []).indexOf("Files") >= 0;
    window.addEventListener("dragenter", (e) => { if (!hasFiles(e)) return; e.preventDefault(); depth++; $("#drop-overlay").hidden = false; const dz = $("#dropzone"); if (dz) dz.classList.add("is-over"); });
    window.addEventListener("dragover", (e) => { if (hasFiles(e)) e.preventDefault(); });
    window.addEventListener("dragleave", (e) => { if (!hasFiles(e)) return; depth = Math.max(0, depth - 1); if (!depth) hideDrop(); });
    window.addEventListener("drop", (e) => { if (!hasFiles(e)) return; e.preventDefault(); depth = 0; hideDrop(); stageFiles(e.dataTransfer.files); });

    document.addEventListener("keydown", onKey);
  }

  function hideDrop() {
    $("#drop-overlay").hidden = true;
    const dz = $("#dropzone");
    if (dz) dz.classList.remove("is-over");
  }

  function onViewClick(e) {
    const t = e.target;
    const open = t.closest("[data-open]");
    if (open) {
      const list = (open.getAttribute("data-list") || "").split(",").filter(Boolean);
      if (open.hasAttribute("data-idx")) {
        state.cursor = +open.getAttribute("data-idx");
        $$("#s-body tr[data-idx]").forEach((tr, i) => tr.classList.toggle("is-cursor", i === state.cursor));
      }
      openSheet(open.getAttribute("data-open"), list);
      return;
    }
    const sort = t.closest("[data-sort]");
    if (sort) {
      const k = sort.getAttribute("data-sort");
      prefs.sSort = prefs.sSort.key === k ? { key: k, dir: -prefs.sSort.dir } : { key: k, dir: 1 };
      savePrefs();
      renderView();
      return;
    }
    const chip = t.closest("[data-chip]");
    if (chip) {
      const g = chip.getAttribute("data-chip"), v = chip.getAttribute("data-val");
      const arr = prefs.sFilters[g] || (prefs.sFilters[g] = []);
      const i = arr.indexOf(v);
      if (i >= 0) arr.splice(i, 1); else arr.push(v);
      state.cursor = 0;
      savePrefs();
      renderView();
      return;
    }
    const lvl = t.closest("[data-level]");
    if (lvl) {
      const l = lvl.getAttribute("data-level");
      const i = prefs.jLevels.indexOf(l);
      if (i >= 0) prefs.jLevels.splice(i, 1); else prefs.jLevels.push(l);
      savePrefs();
      lvl.classList.toggle("is-on", i < 0);
      lvl.setAttribute("aria-pressed", String(i < 0));
      renderJournalRows();
      return;
    }
    const kp = t.closest("[data-kpi]");
    if (kp) {
      const target = kp.getAttribute("data-kpi");
      if (target === "suspens") navigate("suspens");
      else if (target.indexOf("journal-") === 0) {
        prefs.jLevels = [target.slice(8)];
        savePrefs();
        navigate("journal");
      } else {
        const sec = document.getElementById(target);
        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      return;
    }
    const mx = t.closest("[data-matrix-f]");
    if (mx) {
      prefs.sFilters = { fonds: [mx.getAttribute("data-matrix-f")], cons: [mx.getAttribute("data-matrix-c")], type: [], prio: [], statut: [] };
      prefs.sQuery = "";
      savePrefs();
      navigate("suspens");
      return;
    }
    const go = t.closest("[data-go]");
    if (go) { navigate(go.getAttribute("data-go")); return; }
    const ex = t.closest("[data-example]");
    if (ex) {
      const inp = $("#q-input");
      inp.value = ex.getAttribute("data-example");
      askQuestion(inp.value);
      return;
    }
    const un = t.closest("[data-unstage]");
    if (un) { state.staged.splice(+un.getAttribute("data-unstage"), 1); renderView(); return; }
    const act = t.closest("[data-act]");
    if (!act) return;
    switch (act.getAttribute("data-act")) {
      case "exemple": runExemple(); break;
      case "pick": $("#file-input").click(); break;
      case "upload": runUpload(); break;
      case "clear-staged": state.staged = []; state.uploadError = null; renderView(); break;
      case "copy-point": copyPoint(); break;
      case "retry-point": state.pointError = null; renderView(); break;
      case "retry-param": state.paramError = null; renderView(); loadParam().then(() => renderView()); break;
      case "reset-filters": prefs.sFilters = { fonds: [], cons: [], type: [], prio: [], statut: [] }; prefs.sQuery = ""; savePrefs(); renderView(); break;
      case "q-preview": state.q.preview = !state.q.preview; renderView(); break;
    }
  }

  function onViewInput(e) {
    if (e.target.id === "s-q") {
      prefs.sQuery = e.target.value;
      state.cursor = 0;
      savePrefs();
      renderSuspensRows();
    } else if (e.target.id === "j-q") {
      prefs.jQuery = e.target.value;
      savePrefs();
      renderJournalRows();
    } else if (e.target.id === "q-input") {
      state.q.text = e.target.value;
    }
  }

  function onKey(e) {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      if (paletteOpen()) closePalette(); else openPalette();
      return;
    }
    if (paletteOpen()) return;
    const tag = (e.target.tagName || "").toLowerCase();
    const typing = tag === "input" || tag === "textarea" || tag === "select";

    if (e.key === "Escape") {
      if (state.sheet.open) { e.preventDefault(); closeSheet(); return; }
      if ($("#app").classList.contains("sb-open")) { $("#app").classList.remove("sb-open"); return; }
      if (typing) e.target.blur();
      return;
    }
    if (e.key === "/" && !typing) {
      const inp = $("#s-q") || $("#j-q");
      if (inp) { e.preventDefault(); inp.focus(); inp.select(); }
      return;
    }
    if (state.sheet.open && (e.key === "ArrowDown" || e.key === "ArrowUp") && !typing) {
      e.preventDefault();
      stepSheet(e.key === "ArrowDown" ? 1 : -1);
      return;
    }
    if (state.view === "suspens" && !state.sheet.open) {
      const inSearch = e.target.id === "s-q";
      if (typing && !inSearch) return;
      if (e.key === "ArrowDown") { e.preventDefault(); moveCursor(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); moveCursor(-1); }
      else if (e.key === "Enter" && (inSearch || !(e.target.closest && e.target.closest("button, a, input")))) {
        const row = $$("#s-body tr[data-idx]")[state.cursor];
        if (row) { e.preventDefault(); openSheet(row.getAttribute("data-open"), row.getAttribute("data-list").split(",")); }
      }
    }
  }

  /* ======================================================================
   * Démarrage
   * ==================================================================== */

  async function boot() {
    hydrateIcons(document);
    if (!/Mac|iPhone|iPad/.test(navigator.platform || "")) $("#kbd-mod").textContent = "Ctrl";
    bind();
    route();
    await Promise.all([loadSante(), loadParam(), loadListe()]);
    if (!state.rapp && state.liste.length) await loadRapp(state.liste[0].id, true);
    state.booting = false;
    renderChrome();
    renderView();
    setInterval(loadSante, 30000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
