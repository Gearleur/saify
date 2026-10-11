"""Garde-fous : aucun test n'appelle le vrai LLM (clé plafonnée, coût, déterminisme), ni ne dépend du `.env`."""

import os

os.environ["LLM_ENABLED"] = "0"
# Le `.env` du poste ne doit rien changer aux tests : une variable déjà définie n'est pas écrasée.
os.environ["EXPECTED_AS_OF_DATE"] = ""
