"""Garde-fou : aucun test n'appelle le vrai LLM (clé plafonnée, coût, déterminisme)."""

import os

os.environ["RECO_LLM_ACTIF"] = "0"
