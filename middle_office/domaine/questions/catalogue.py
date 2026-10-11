"""Catalogue des requêtes autorisées. Chaque entrée : SQL fixe et paramétré, calcul en Decimal, gabarit.

Rien ici ne vient d'un LLM : il choisit seulement l'entrée du catalogue et ses paramètres.
"""

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domaine.base_gestion import connexion_lecture_seule, decimal
from middle_office.domaine.formats import CENTIME, date_fr, formater_quantite, montant, pourcentage
from middle_office.domaine.questions.modeles import (
    Chiffre,
    ContexteRapprochement,
    LigneSource,
    Reponse,
)
from middle_office.domaine.questions.vigilance import REGLES_PAR_DEFAUT, ReglesVigilance

HORIZON_DEFAUT_MOIS = 12  # à valider avec le client (NOTES.md, Q4)
AVERTISSEMENT_PMS = "Positions de la base de gestion (vue PMS, en date de négociation) : opérations non dénouées incluses."  # fmt: skip

SQL_ENCOURS = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.emetteur, t.type_titre, t.mode_cotation,
       p.quantite, c.cours, c.date_cours
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
LEFT JOIN cours c ON c.isin = p.isin AND c.date_cours = :date
WHERE p.date_arrete = :date AND (:fonds IS NULL OR p.portefeuille = :fonds)
ORDER BY p.portefeuille, p.isin
""".strip()

SQL_ECHEANCES = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.type_titre, t.date_echeance, p.quantite
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
WHERE p.date_arrete = :date AND p.quantite > 0
  AND t.date_echeance > :date AND t.date_echeance <= :fin
  AND (:fonds IS NULL OR p.portefeuille = :fonds) AND (:isin IS NULL OR p.isin = :isin)
ORDER BY t.date_echeance, p.portefeuille, p.isin
""".strip()

SQL_NON_DENOUEES = """
SELECT m.id, m.date_operation, m.date_denouement, m.portefeuille, m.isin, t.libelle,
       t.mode_cotation, m.sens, m.quantite, m.prix, m.contrepartie
FROM mouvements m
LEFT JOIN titres t ON t.isin = m.isin
WHERE m.statut = 'EN_ATTENTE' AND (:fonds IS NULL OR m.portefeuille = :fonds)
  AND (:isin IS NULL OR m.isin = :isin)
ORDER BY m.date_denouement, m.id
""".strip()

SQL_MOUVEMENTS_TITRE = """
SELECT id, portefeuille, date_operation, date_denouement, sens, quantite, statut
FROM mouvements
WHERE isin = :isin
ORDER BY id
""".strip()


def _valoriser(quantite: Decimal, cours: Decimal, mode_cotation: str | None) -> Decimal | None:
    """Quantité en nominal pour les obligations (cours en % du nominal), en titres pour les actions."""
    if mode_cotation == "POURCENTAGE":
        return (
            quantite * cours / 100
        )  # surtout pas × valeur_nominale : la quantité est déjà un nominal
    if mode_cotation == "UNITAIRE":
        return quantite * cours
    return None  # mode inconnu : on ne devine pas


@dataclass
class _Valorisation:
    """Positions valorisées ligne à ligne : base commune de l'encours et de la concentration."""

    parametres: dict[str, str | None]
    lignes: list[tuple]
    valeurs: list[Decimal | None]  # None : ligne non valorisée (cours absent, mode inconnu)
    sources: list[LigneSource]
    avertissements: list[str]

    @property
    def exclues(self) -> int:
        return sum(v is None for v in self.valeurs)


def _valoriser_positions(base: Path, fonds: str | None, date_ref: date) -> _Valorisation:
    parametres = {"date": date_ref.isoformat(), "fonds": fonds}
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_ENCOURS, parametres).fetchall()
    valeurs, sources, avertissements = [], [], []
    for (
        code,
        _nom,
        isin,
        libelle,
        emetteur,
        type_titre,
        mode,
        quantite,
        cours,
        date_cours,
    ) in lignes:
        qte, prix = decimal(quantite), decimal(cours)
        valeur = None
        if prix is None:
            avertissements.append(f"{isin} {libelle} : pas de cours au {date_fr(date_ref)}, ligne non valorisée")  # fmt: skip
        else:
            valeur = _valoriser(qte, prix, mode)
            if valeur is None:
                avertissements.append(f"{isin} {libelle} : mode de cotation « {mode} » inconnu, ligne non valorisée")  # fmt: skip
        valeurs.append(valeur)
        sources.append(LigneSource("positions × titres × cours", {
            "portefeuille": code, "isin": isin, "libelle": libelle, "emetteur": emetteur or "",
            "type_titre": type_titre, "mode_cotation": mode or "", "quantite": str(qte),
            "cours": "" if prix is None else str(prix), "date_cours": date_cours or "",
            "valorisation": "" if valeur is None else str(valeur.quantize(CENTIME)),
        }))  # fmt: skip
    if any(ligne[6] == "POURCENTAGE" for ligne in lignes):
        avertissements.append("Obligations valorisées au pied de coupon (cours en % du nominal), sans coupon couru.")  # fmt: skip
    avertissements.append(AVERTISSEMENT_PMS)
    return _Valorisation(parametres, lignes, valeurs, sources, avertissements)


def encours_valorise(base: Path, fonds: str | None, date_ref: date) -> Reponse:
    v = _valoriser_positions(base, fonds, date_ref)
    jour = date_fr(date_ref)
    if not v.lignes:
        return Reponse(f"Aucune position pour {fonds or 'les fonds'} au {jour} dans la base de gestion.",
                       [], SQL_ENCOURS, v.parametres, [], confiance="basse")  # fmt: skip

    totaux: dict[str, Decimal] = defaultdict(Decimal)
    for ligne, valeur in zip(v.lignes, v.valeurs, strict=True):
        if valeur is not None:
            totaux[ligne[1]] += valeur
    partiel = " partiel" if v.exclues else ""
    chiffres = [Chiffre(f"Encours valorisé{partiel}" if fonds else nom, total.quantize(CENTIME), "EUR")
                for nom, total in sorted(totaux.items())]  # fmt: skip
    if fonds is None:
        total = sum(totaux.values(), Decimal(0)).quantize(CENTIME)
        chiffres.append(Chiffre(f"Total des {len(totaux)} fonds{partiel}", total, "EUR"))
        phrase = f"L'encours valorisé{partiel} des {len(totaux)} fonds au {jour} est de {montant(total)} EUR"
    else:
        phrase = f"L'encours valorisé{partiel} d'{v.lignes[0][1]} au {jour} est de {montant(chiffres[0].valeur)} EUR"  # fmt: skip
    phrase += f" ({len(v.lignes) - v.exclues} lignes valorisées au cours de clôture du {jour}"
    phrase += f", {v.exclues} non valorisées)." if v.exclues else ")."
    return Reponse(phrase, chiffres, SQL_ENCOURS, v.parametres, v.sources,
                   confiance="basse" if v.exclues else "haute", avertissements=v.avertissements)  # fmt: skip


def concentration_emetteurs(base: Path, fonds: str | None, date_ref: date,
                            regles: ReglesVigilance = REGLES_PAR_DEFAUT) -> Reponse:  # fmt: skip
    """Part de chaque émetteur dans l'encours valorisé d'un fonds. Chiffres bruts, sans jugement réglementaire."""
    if fonds is None:
        return Reponse("Précisez le fonds : la concentration par émetteur se lit fonds par fonds (PAT, OBL ou ACT).",
                       [], SQL_ENCOURS, {"date": date_ref.isoformat(), "fonds": None}, [], confiance="basse")  # fmt: skip
    v = _valoriser_positions(base, fonds, date_ref)
    jour = date_fr(date_ref)
    par_emetteur: dict[str, Decimal] = defaultdict(Decimal)
    for ligne, valeur in zip(v.lignes, v.valeurs, strict=True):
        if valeur is not None:
            par_emetteur[ligne[4] or "Émetteur non renseigné"] += valeur
    total = sum(par_emetteur.values(), Decimal(0))
    if not total:
        return Reponse(f"Aucune position valorisée pour {fonds} au {jour} dans la base de gestion.",
                       [], SQL_ENCOURS, v.parametres, v.sources, confiance="basse",
                       avertissements=v.avertissements)  # fmt: skip

    classement = sorted(par_emetteur.items(), key=lambda e: (-e[1], e[0]))
    chiffres = [Chiffre(emetteur, (valeur / total * 100).quantize(CENTIME), "%") for emetteur, valeur in classement]  # fmt: skip
    premier, valeur_premier = classement[0]
    partiel = " partiel" if v.exclues else ""
    phrase = (
        f"Premier émetteur d'{v.lignes[0][1]} au {jour} : {premier}, {pourcentage(chiffres[0].valeur)} "
        f"de l'encours valorisé{partiel} ({montant(valeur_premier.quantize(CENTIME))} EUR sur "
        f"{montant(total.quantize(CENTIME))} EUR, {len(classement)} émetteurs)."
    )
    avertissements = [
        "Aucune appréciation des ratios réglementaires (5/10/40, dérogations des émetteurs publics) : "
        "chiffres bruts, à interpréter par le gérant ou le RCCI.",
        *v.avertissements,
    ]
    return Reponse(phrase, chiffres, SQL_ENCOURS, v.parametres, v.sources,
                   confiance="basse" if v.exclues else "haute", avertissements=avertissements,
                   vigilances=regles.evaluer(classement, total))  # fmt: skip


def _ajouter_mois(d: date, mois: int) -> date:
    annee, mois_0 = divmod(d.month - 1 + mois, 12)
    annee += d.year
    return date(annee, mois_0 + 1, min(d.day, calendar.monthrange(annee, mois_0 + 1)[1]))


def _perimetre(fonds: str | None, isin: str | None) -> str:
    return " ".join(
        filter(
            None, [f"sur {isin}" if isin else "", f"pour {fonds}" if fonds else "pour les 3 fonds"]
        )
    )


def echeances(base: Path, fonds: str | None, date_ref: date, horizon_mois: int | None = None,
              isin: str | None = None, fin: date | None = None) -> Reponse:  # fmt: skip
    """Titres détenus arrivant à échéance après la date de référence, dans l'horizon donné.
    Un titre précis sans horizon : pas de borne de fin (« quand tombe EDF 2031 ? » ne doit pas
    répondre « aucune tombée » parce qu'elle est au-delà de 12 mois)."""
    horizon_par_defaut = horizon_mois is None and fin is None
    sans_borne = horizon_par_defaut and isin is not None
    if sans_borne:
        fin = date(9999, 12, 31)
    elif fin is None:
        fin = _ajouter_mois(date_ref, horizon_mois or HORIZON_DEFAUT_MOIS)
    parametres = {
        "date": date_ref.isoformat(),
        "fin": fin.isoformat(),
        "fonds": fonds,
        "isin": isin,
    }
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_ECHEANCES, parametres).fetchall()
    avertissements = ["Montant remboursé = nominal détenu (remboursement au pair), hors dernier coupon.", AVERTISSEMENT_PMS]  # fmt: skip
    if horizon_par_defaut and not sans_borne:
        avertissements.insert(0, f"Horizon par défaut de {HORIZON_DEFAUT_MOIS} mois (à valider avec le middle office).")  # fmt: skip
    perimetre = _perimetre(fonds, isin)
    borne = (
        f"après le {date_fr(date_ref)}"
        if sans_borne
        else f"entre le {date_fr(date_ref)} et le {date_fr(fin)}"
    )
    if not lignes:
        return Reponse(f"Aucune tombée d'échéance {perimetre} {borne}.", [], SQL_ECHEANCES, parametres,
                       [], avertissements=avertissements)  # fmt: skip

    sources = [
        LigneSource(
            "positions × titres",
            {
                "portefeuille": code,
                "isin": isin,
                "libelle": libelle,
                "type_titre": type_titre,
                "date_echeance": echeance,
                "nominal": str(decimal(quantite)),
            },
        )  # fmt: skip
        for code, _nom, isin, libelle, type_titre, echeance, quantite in lignes
    ]
    nominal = sum((decimal(ligne[6]) for ligne in lignes), Decimal(0))
    detail = ", ".join(
        f"{libelle} ({code}) le {date_fr(date.fromisoformat(echeance))} pour {formater_quantite(decimal(qte))}"
        for code, _n, _i, libelle, _t, echeance, qte in lignes
    )
    phrase = f"{len(lignes)} tombée(s) d'échéance {perimetre} {borne} : {detail}. Nominal remboursé : {montant(nominal)} EUR."  # fmt: skip
    chiffres = [Chiffre("Tombées d'échéance", Decimal(len(lignes)), "lignes"),
                Chiffre("Nominal remboursé", nominal, "EUR")]  # fmt: skip
    return Reponse(
        phrase, chiffres, SQL_ECHEANCES, parametres, sources, avertissements=avertissements
    )


def operations_non_denouees(base: Path, fonds: str | None, date_ref: date,
                            isin: str | None = None) -> Reponse:  # fmt: skip
    """Opérations en attente de dénouement ; une date prévue dépassée est un défaut de règlement (CSDR)."""
    parametres = {"fonds": fonds, "isin": isin}
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_NON_DENOUEES, parametres).fetchall()
    perimetre = _perimetre(fonds, isin)
    avertissements = ["Statut lu dans la base de gestion (opérations de la semaine)."]
    if not lignes:
        return Reponse(f"Aucune opération non dénouée {perimetre}.", [], SQL_NON_DENOUEES, parametres, [],
                       avertissements=avertissements)  # fmt: skip

    sources, details, en_retard = [], [], 0
    for (
        id_,
        date_op,
        date_den,
        code,
        isin,
        libelle,
        mode,
        sens,
        quantite,
        prix,
        contrepartie,
    ) in lignes:
        qte, cours = decimal(quantite), decimal(prix)
        valeur = None if cours is None else _valoriser(qte, cours, mode)
        prevue = date.fromisoformat(date_den)
        if prevue <= date_ref:
            en_retard += 1
            avertissements.insert(0, f"Op. n°{id_} ({libelle or isin}) devait être dénouée le {date_fr(prevue)} : "
                                     "défaut de règlement-livraison, risque CSDR.")  # fmt: skip
        details.append(f"n°{id_} {sens} {formater_quantite(qte)} {libelle or isin} ({code}, dén. prévu {date_fr(prevue)})")  # fmt: skip
        sources.append(LigneSource("mouvements", {
            "id": str(id_), "date_operation": date_op, "date_denouement": date_den, "portefeuille": code,
            "isin": isin, "sens": sens, "quantite": str(qte), "prix": "" if cours is None else str(cours),
            "montant": "" if valeur is None else str(valeur.quantize(CENTIME)), "contrepartie": contrepartie or "",
        }))  # fmt: skip
    retard = f", dont {en_retard} en retard (risque CSDR)" if en_retard else ""
    phrase = f"{len(lignes)} opération(s) non dénouée(s) {perimetre} au {date_fr(date_ref)}{retard} : {', '.join(details)}."  # fmt: skip
    chiffres = [Chiffre("Opérations non dénouées", Decimal(len(lignes)), "opérations")]
    if en_retard:
        chiffres.append(Chiffre("En retard (risque CSDR)", Decimal(en_retard), "opérations"))
    return Reponse(phrase, chiffres, SQL_NON_DENOUEES, parametres, sources,
                   avertissements=avertissements)  # fmt: skip


def origine_suspens(base: Path, isin: str, contexte: ContexteRapprochement | None) -> Reponse:
    """Pont avec le besoin 1 : le suspens du dernier rapprochement exploitable, ses lignes sources
    et les mouvements du titre. Un rapprochement plus récent mais bloqué est toujours signalé."""
    parametres: dict[str, str | None] = {"isin": isin}
    if contexte is None or contexte.id is None:
        if contexte is not None and contexte.bloque_plus_recent:
            motif = (
                f"Le dernier rapprochement ({contexte.bloque_plus_recent}) est bloqué et aucun "
                "rapprochement exploitable n'existe : corrigez les fichiers, puis relancez."
            )
        else:
            motif = "Aucun rapprochement disponible : lancez d'abord le rapprochement du jour."
        return Reponse(motif, [], SQL_MOUVEMENTS_TITRE, parametres, [], confiance="basse")

    jour = (
        date_fr(date.fromisoformat(contexte.date_arrete))
        if contexte.date_arrete
        else "date inconnue"
    )
    reference = f"le rapprochement {contexte.id} (arrêté du {jour})"
    avertissements = []
    if contexte.bloque_plus_recent:
        avertissements.append(
            f"Le rapprochement le plus récent ({contexte.bloque_plus_recent}) est bloqué : cette réponse "
            f"vient de {reference}, le dernier exploitable. Elle peut ne plus être à jour."
        )
    confiance = "basse" if contexte.bloque_plus_recent else "haute"
    trouves = [s for s in contexte.suspens if s["isin"] == isin]
    if not trouves:
        return Reponse(f"Aucun suspens sur {isin} dans {reference}.", [], SQL_MOUVEMENTS_TITRE,
                       parametres, [], confiance=confiance, avertissements=avertissements)  # fmt: skip

    fonds = {s["fonds"] for s in trouves}
    with connexion_lecture_seule(base) as db:
        mouvements = [m for m in db.execute(SQL_MOUVEMENTS_TITRE, parametres) if m[1] in fonds]

    def qte(valeur: str | None) -> str:
        return "absent" if valeur is None else formater_quantite(Decimal(valeur))

    phrases, sources = [], []
    for s in trouves:
        phrase = (
            f"Suspens {s['type']} ({s['libelle_type']}) sur {s['libelle_titre']} ({s['fonds'] or s['entite']}, "
            f"conservateur {s['conservateur']}) dans {reference} : PMS {qte(s['qte_pms'])}, "
            f"conservateur {qte(s['qte_dep'])}, écart {qte(s['ecart'])}. Action attendue : {s['action']}."
        )
        if s["piste"]:
            phrase += f" Piste : {s['piste']}."
        phrases.append(phrase)
        sources += [LigneSource(ref, {"isin": isin, "suspens": s["id"]}) for ref in s["sources"]]
    sources += [
        LigneSource(
            "mouvements",
            {
                "id": str(id_),
                "portefeuille": pf,
                "date_operation": d_op,
                "date_denouement": d_den,
                "sens": sens,
                "quantite": str(decimal(q)),
                "statut": statut,
            },
        )  # fmt: skip
        for id_, pf, d_op, d_den, sens, q, statut in mouvements
    ]
    chiffres = [Chiffre(f"Écart {s['type']} ({s['conservateur']})", Decimal(s["ecart"]), "titres ou nominal") for s in trouves]  # fmt: skip
    avertissements += [g["message"] for s in trouves for g in s["signalements"]]
    return Reponse(" ".join(phrases), chiffres, SQL_MOUVEMENTS_TITRE, parametres, sources,
                   confiance=confiance, avertissements=avertissements)  # fmt: skip
