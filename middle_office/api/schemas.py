"""Modèles d'entrée et de sortie (contrat : docs/API.md). Quantités en chaînes décimales, jamais de float."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from middle_office.api.config import EXTENSIONS

# Entrées : champs inconnus refusés


class Entree(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FichierEntree(Entree):
    nom: str = Field(min_length=1, max_length=255)
    contenu_b64: str

    @field_validator("nom")
    @classmethod
    def nom_de_base(cls, nom: str) -> str:
        if "/" in nom or "\\" in nom or ".." in nom or any(ord(c) < 32 for c in nom):
            raise ValueError("nom de base seul attendu (ni chemin, ni « .. », ni caractère de contrôle)")  # fmt: skip
        if not nom.lower().endswith(EXTENSIONS):
            raise ValueError(f"extension non autorisée (attendu : {', '.join(EXTENSIONS)})")
        return nom


class DemandeRapprochement(Entree):
    fichiers: list[FichierEntree] = Field(min_length=1, max_length=8)


class Question(Entree):
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def texte_propre(cls, question: str) -> str:
        """Caractères de contrôle retirés, espaces normalisés : ce qui part au LLM et aux logs reste propre."""
        nettoyee = " ".join("".join(c if c.isprintable() else " " for c in question).split())
        if len(nettoyee) < 3:
            raise ValueError("question trop courte")
        return nettoyee


# Sorties : rapprochement


class FichierSortie(BaseModel):
    nom: str
    source: str
    taille: int
    sha256: str


class FondsSynthese(BaseModel):
    code: str
    entite: str
    nb_suspens: int


class Synthese(BaseModel):
    nb_suspens: int
    par_priorite: dict[str, int]
    par_type: dict[str, int]
    par_fonds: list[FondsSynthese]
    par_conservateur: dict[str, int]
    journal: dict[str, int]


class SignalementSortie(BaseModel):
    code: str  # CSDR, DEP_AMBIGU, ISIN_INVALIDE, PISTE_MULTI_CONSERVATEURS
    message: str


class SuspensSortie(BaseModel):
    id: str
    priorite: str
    fonds: str
    entite: str
    isin: str
    libelle_titre: str
    conservateur: str
    type: str
    libelle_type: str
    qte_pms: str | None
    qte_dep: str | None
    ecart: str
    action: str
    piste: str
    explication: str  # aucune, totale, partielle, contraire (par les opérations en attente)
    alertes: list[str]  # codes des signalements, triés : ce que lit l'interface, jamais le texte
    signalements: list[SignalementSortie]
    sources: list[str]


class AnomalieSortie(BaseModel):
    fichier: str
    ligne: int
    niveau: str
    regle: str
    brut: str
    retenu: str
    motif: str
    remede: str


class Rapprochement(BaseModel):
    id: str
    cree_le: str
    date_arrete: str | None  # lue dans le PMS ; None si absente ou ambiguë (rapprochement BLOQUE)
    statut: str
    fichiers: list[FichierSortie]
    synthese: Synthese
    suspens: list[SuspensSortie]
    journal: list[AnomalieSortie]


class RapprochementResume(BaseModel):
    id: str
    cree_le: str
    date_arrete: str | None  # lue dans le PMS ; None si absente ou ambiguë (rapprochement BLOQUE)
    statut: str
    nb_suspens: int
    nb_a_traiter: int


class PointDeSituation(BaseModel):
    texte: str


# Sorties : santé et référentiel


class EtatLLM(BaseModel):
    actif: bool
    modele: str
    appels_aujourdhui: int
    budget_jour: int


class Sante(BaseModel):
    statut: str
    version: str
    date_arrete: str | None  # date de référence de la base de gestion (dernières positions)
    base_disponible: bool
    llm: EtatLLM


class Fonds(BaseModel):
    entite: str
    code: str


class Conservateur(BaseModel):
    code: str
    nom: str


class TypeEcart(BaseModel):
    code: str
    libelle: str
    action_attendue: str


class Transco(BaseModel):
    cle: str
    entite: str


class ParametrageSortie(BaseModel):
    date_arrete: str | None
    fonds: list[Fonds]
    conservateurs: list[Conservateur]
    types_ecarts: list[TypeEcart]
    transcos: dict[str, list[Transco]]
    exclusions: list[str]


# Sorties : questions sur la base (besoin 2)


class ChiffreSortie(BaseModel):
    libelle: str
    valeur: str  # décimal en texte
    unite: str


class LigneSourceSortie(BaseModel):
    table: str
    valeurs: dict[str, str]


class VigilanceSortie(BaseModel):
    code: str
    message: str
    emetteurs: list[str]
    valeur: str  # en %


class ComprehensionSortie(BaseModel):
    intention: str
    fonds: str | None
    horizon_mois: int | None
    isin: str | None
    source: str  # llm ou mots_cles
    confiance: float
    detail: str


class ReponseQuestion(BaseModel):
    question: str
    reponse: str
    chiffres: list[ChiffreSortie]
    requete_sql: str
    parametres_sql: dict[str, str | None]
    lignes_sources: list[LigneSourceSortie]
    confiance: str
    avertissements: list[str]
    vigilances: list[VigilanceSortie]
    reformulations: list[str]
    comprehension: ComprehensionSortie
