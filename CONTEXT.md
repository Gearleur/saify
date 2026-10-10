# Contexte métier

**Saify** : startup qui déploie des agents IA en production pour la finance (banque, trésorerie, gestion de patrimoine). Cas typique : rapprochement automatique des factures fournisseurs. Enjeux : fiabilité, traçabilité, données sensibles.

## Glossaire
- **Rapprochement** : mise en correspondance de deux sources (relevé bancaire et factures/écritures) pour vérifier que tout paiement a sa pièce.
- **Lettrage** : association comptable d'une facture et de son règlement ; une fois lettrés, ils soldent le compte du tiers.
- **Facture fournisseur** : pièce reçue d'un fournisseur (numéro, date, échéance, HT, TVA, TTC, IBAN). Génère une dette.
- **Avoir** : facture négative (remise, retour) qui vient en déduction ; le paiement est souvent facture moins avoir.
- **TVA** : taxe sur la valeur ajoutée (20 % en France) ; TTC = HT + TVA. Les rapprochements se font sur le TTC.
- **Échéance** : date limite de paiement ; un paiement est attendu autour de cette date (écarts fréquents).
- **Relevé bancaire** : liste des mouvements de la banque, avec libellés bruités (« VIR SEPA », « PRLV », abréviations, références tronquées).
- **IBAN** : identifiant international de compte ; sert à identifier le fournisseur de façon fiable (à masquer dans les logs/LLM).
- **Trésorerie** : liquidités disponibles et prévisions d'encaissements/décaissements ; dépend de factures payées à temps.
- **KYC** : Know Your Customer, vérification d'identité et de légitimité d'un client (obligation réglementaire banque/finance).
- **Doublon de paiement** : même paiement enregistré ou exécuté deux fois ; à signaler, jamais à rapprocher deux fois.
- **Écart de montant** : différence facture/paiement (frais bancaires, escompte, paiement partiel, change).

## Pièges des données
Formats FR (`1 234,56`, `dd/mm/yyyy`), séparateur `;`, encodages latin-1, colonnes débit/crédit séparées, noms de fournisseur abrégés, PDF texte vs scan.
