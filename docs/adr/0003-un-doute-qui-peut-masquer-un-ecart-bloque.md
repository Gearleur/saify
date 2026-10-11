# ADR 0003 : un doute qui peut masquer un écart bloque ; une question qu'on ne sait pas traiter n'a pas de chiffre

- Statut : accepté
- Date : 2026-10-11

## Contexte
La revue de code finale a reproduit trois cas où l'outil donnait un résultat faux sans le dire :
- **Rapprochement** : un lot dupliqué chez C, ou un item à `ACTION` inconnue, portait la quantité du conservateur au niveau du PMS. Le suspens SFIL disparaissait. Le premier cas ne laissait aucune trace, le second un simple `SIGNALE`. Une ligne en double chez PMS, A ou B présentait le même risque.
- **Questions** : « Encours de LVMH » recevait l'encours des 3 fonds, « au 01/01/2025 » l'encours du 25/09, et après un rapprochement bloqué, « d'où vient le suspens sur X » répondait « aucun suspens ».
- **Suivi** : le statut de traitement des suspens ne vivait que dans le navigateur de l'opérateur.

Pour le client, le pire cas est le faux négatif (pénalités CSDR, RCCI), puis le chiffre inventé.

## Décision
1. **Tout doute qui peut combler un écart est `BLOQUANT`** : une ligne en double (même compte et ISIN ; pour C, même compte, ISIN et lot) ou une `ACTION` inconnue. Additionner peut masquer un écart, écarter peut en créer un, et choisir une ligne serait deviner. Le remède dit quoi demander à l'émetteur.
2. **Une question que le catalogue ne sait pas traiter reçoit un « Attention » sans chiffre** et des reformulations. C'est le cas d'une autre date que la date de référence, de l'encours d'un titre seul, d'un titre ambigu ou d'un ordre d'écriture. « Origine d'un suspens » lit le dernier rapprochement exploitable et signale un rapprochement bloqué plus récent.
3. **Le statut de traitement est partagé côté serveur** (`historique.db`). Sa clé est stable d'un rapprochement à l'autre du même jour, et chaque changement est journalisé.

## Alternatives écartées
- **Additionner et signaler** (comportement d'avant) : le signalement se perd dans le journal alors que le suspens a disparu de la file. C'est précisément le faux négatif invisible.
- **Garder la première ligne d'un doublon** : un choix arbitraire présenté comme une donnée.
- **Répondre quand même en précisant la date dans la phrase** : le chiffre est vrai mais répond à une autre question ; recopié dans un mail, il devient faux.
- **Statut en `localStorage`** (avant) : invisible pour le responsable, non auditable, perdu en changeant de poste.

## Conséquences
- Plus de rapprochements bloqués sur des fichiers douteux. Chacun porte un remède, et c'est le comportement voulu : un rapprochement partiel cacherait des écarts.
- Le besoin 2 refuse davantage de questions. Chaque refus propose une reformulation qui, elle, est reconnue.
- Les statuts n'ont pas d'auteur nominatif tant qu'il n'y a pas d'authentification : le journal garde l'identifiant de requête. En production, il faudra y mettre l'utilisateur authentifié.
