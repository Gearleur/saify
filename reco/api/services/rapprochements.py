"""Exécution d'un rapprochement et traduction du résultat métier en réponse d'API."""

import hashlib
import logging
from collections import Counter
from datetime import UTC, datetime

from reco.api.config import Reglages
from reco.api.schemas import (
    AnomalieSortie,
    FichierSortie,
    FondsSynthese,
    Rapprochement,
    RapprochementResume,
    SuspensSortie,
    Synthese,
)
from reco.api.services.depot import source_de
from reco.api.services.historique import Historique
from reco.domaine.rapprochement import DATE_ARRETE, PRIORITES, Resultat, rapprocher
from reco.domaine.situation import point_de_situation, quantite_texte, suspens_csv
from reco.domaine.sources import TYPES_REQUIS

NIVEAUX = ("BLOQUANT", "SIGNALE", "EXCLU", "NORMALISE")

log = logging.getLogger("reco.api.audit")


def executer(depot: dict[str, bytes], reglages: Reglages, historique: Historique) -> Rapprochement:
    """Rapproche, enregistre dans l'historique et trace l'audit (sha256 des fichiers, jamais leur contenu)."""
    resultat = rapprocher(depot, reglages.parametrage, reglages.base)
    cree_le = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    modele = vers_modele(historique.nouvel_id(), cree_le, depot, resultat)
    # CSV et point de situation figés maintenant : l'historique les relit sans garder `resultat`.
    historique.ajouter(modele, suspens_csv(resultat.suspens), point_de_situation(resultat))
    log.info("audit rapprochement id=%s statut=%s nb_suspens=%d fichiers=%s", modele.id,
             modele.statut, modele.synthese.nb_suspens,
             ",".join(f"{f.nom}:{f.sha256}" for f in modele.fichiers))  # fmt: skip
    return modele


def resume(modele: Rapprochement) -> RapprochementResume:
    priorites = modele.synthese.par_priorite
    return RapprochementResume(
        id=modele.id,
        cree_le=modele.cree_le,
        date_arrete=modele.date_arrete,
        statut=modele.statut,
        nb_suspens=modele.synthese.nb_suspens,
        nb_a_traiter=priorites["critique"] + priorites["a_relever"],
    )


def vers_modele(id_: str, cree_le: str, depot: dict[str, bytes], r: Resultat) -> Rapprochement:
    suspens = [
        SuspensSortie(
            id=f"S{i}",
            priorite=s.priorite,
            fonds=s.fonds,
            entite=s.entite,
            isin=s.isin,
            libelle_titre=s.libelle_titre,
            conservateur=s.conservateur,
            type=s.type,
            libelle_type=s.libelle_type,
            qte_pms=quantite_texte(s.qte_pms),
            qte_dep=quantite_texte(s.qte_dep),
            ecart=quantite_texte(s.ecart),
            action=s.action,
            piste=s.piste,
            signalements=list(s.signalements),
            sources=list(s.sources),
        )
        for i, s in enumerate(r.suspens, start=1)
    ]
    return Rapprochement(
        id=id_,
        cree_le=cree_le,
        date_arrete=DATE_ARRETE.isoformat(),
        statut=r.statut,
        fichiers=[
            FichierSortie(
                nom=nom,
                source=source_de(nom),
                taille=len(contenu),
                sha256=hashlib.sha256(contenu).hexdigest(),
            )  # fmt: skip
            for nom, contenu in depot.items()
        ],
        synthese=_synthese(r, suspens),
        suspens=suspens,
        journal=[AnomalieSortie(**vars(a)) for a in r.journal],
    )


def _synthese(r: Resultat, suspens: list[SuspensSortie]) -> Synthese:
    par_fonds = Counter((s.fonds, s.entite) for s in r.suspens)
    niveaux = Counter(a.niveau for a in r.journal)
    return Synthese(
        nb_suspens=len(suspens),
        par_priorite={p: sum(s.priorite == p for s in suspens) for p in PRIORITES},
        par_type={t: sum(s.type == t for s in suspens) for t in TYPES_REQUIS},
        par_fonds=[
            FondsSynthese(code=code, entite=entite, nb_suspens=n)
            for (code, entite), n in sorted(par_fonds.items())
        ],
        par_conservateur=dict(Counter(s.conservateur for s in suspens)),
        journal={n: niveaux[n] for n in NIVEAUX},
    )
