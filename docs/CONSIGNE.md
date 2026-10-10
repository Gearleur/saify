# Consigne (extraite de docs/ENONCE.html)

Cas pratique Orsay Gestion 

 Saify · Cas pratique · Énoncé candidat

 Le middle office d'Orsay Gestion 

 Vous êtes consultant chez Saify. Un client vous expose son besoin. Comment y répondre, avec quels outils et sous quelle forme : c'est à vous de le décider et de le défendre. Vous avez une heure pour construire, puis une heure pour nous présenter votre réponse.

 1 h de construction, seul, sur le poste fourni 

 1 h de restitution avec l'équipe Saify 

 Libre solution, technologies, forme du livrable 

 Le client

 Orsay Gestion

 Orsay Gestion est une société de gestion de portefeuille agréée par l'AMF. Elle gère trois FCP : Orsay Patrimoine (diversifié), Orsay Obligations (taux euro, investment grade ) et Orsay Actions Europe (grandes capitalisations). La conservation des actifs est répartie entre trois teneurs de compte-conservateurs, désignés ici A , B et C .

 Le middle office tient l'inventaire des positions dans l'outil de gestion (PMS). Les opérations y sont enregistrées en date de négociation. Chez les conservateurs, elles n'apparaissent qu'au dénouement, dans le cycle de règlement-livraison à J+2.

 Premier besoin

 Le rapprochement quotidien des positions titres

 Chaque matin, un opérateur rapproche à la main l'inventaire du PMS avec les relevés de positions des trois conservateurs, arrêtés à J−1. Cela lui prend environ 1 h 30. Les suspens sont parfois identifiés plusieurs jours après leur apparition, alors que chaque suspens de règlement non traité peut coûter des pénalités CSDR et remonte au RCCI.

 « Je veux déposer mes fichiers du matin et savoir tout de suite quelles lignes ne tombent pas juste, pour quel fonds, chez quel conservateur, et ce que je dois faire pour chacune. Je veux aussi pouvoir envoyer un point de situation à mon responsable sans rien retaper. »

 Responsable middle office, Orsay Gestion 

 Ce que le middle office nous a expliqué de ses règles de gestion :

 La source du rapprochement Le rapprochement part de l'extraction du matin, positions_internes.csv , comparée aux trois relevés des conservateurs. La base de gestion orsay.db sert uniquement à s'informer : elle n'est pas la référence du rapprochement. 

 La maille de rapprochement Une ligne se rapproche par fonds, code ISIN et conservateur. Les quantités s'entendent en nombre de titres pour les actions et en nominal pour les obligations. 

 Les sous-comptes de gestion Un fonds peut porter la même valeur sur plusieurs sous-comptes du PMS. Le conservateur ne voit que le compte-titres du fonds. 

 Ce qui n'entre pas dans l'inventaire Le sous-compte P3G est un compte technique de passage. Une ligne sans sous-compte est une saisie incomplète. Un mouvement annulé par le conservateur n'est plus une position. 

 Les libellés des conservateurs Dans le PMS, les libellés varient : « CACEIS » désigne A, « EUROCLEAR » désigne B, « BNP » ou « BP2S » désigne C. 

 Aucun seuil de tolérance Un écart d'une seule unité de quotité est un suspens. 

 La typologie des suspens Elle figure dans le fichier de paramétrage, avec l'action attendue pour chaque type. Une valeur attendue chez un conservateur mais livrée chez un autre est un seul suspens, pas deux. 

 Second besoin

 Répondre aux gérants et au contrôle

 Toute la journée, les gérants et le RCCI sollicitent le middle office : l'encours valorisé d'un fonds au cours de clôture, les tombées d'échéances à venir, la concentration par émetteur, les opérations non dénouées, l'origine d'un suspens. L'opérateur y répond en fouillant la base de gestion à la main.

 « Je veux que les gérants obtiennent eux-mêmes, en le demandant simplement, une réponse fiable tirée de notre base. Qu'ils sachent d'où vient chaque chiffre. Un chiffre inventé, ici, c'est un incident qui finit chez le RCCI. Et personne ne doit pouvoir modifier l'inventaire par ce biais. »

 Responsable middle office, Orsay Gestion 

 La base de gestion vous est fournie. Les obligations y sont cotées en pourcentage du nominal, au pied de coupon. Les actions sont cotées à l'unité.

 Dossier donnees/

 Ce que le client vous remet

 Arrêté du 25 septembre 2026, dans la forme où le client reçoit ces fichiers : personne ne les a nettoyés pour vous.

 Fichier Contenu 

 positions_internes.csv Extraction de l'inventaire du PMS, par sous-compte et par valeur. C'est la source interne du rapprochement 

 depositaire_A_20260925.xlsx Relevé de positions du conservateur A 

 depositaire_B_20260925.txt Relevé de positions du conservateur B, au format décrit en annexe 

 depositaire_C_20260925.xml Relevé de positions du conservateur C, au format décrit en annexe 

 parametrage.xlsx Tables de transcodification des comptes vers les fonds, et typologie des suspens 

 orsay.db Base de gestion (SQLite) : fonds, référentiel valeurs, cours de clôture, inventaire, opérations de la semaine. Base d'information, à ne pas utiliser comme source du rapprochement 

 Ce que nous regardons

 Votre réponse

 La forme de la solution est libre. Vous choisissez ce que vous construisez, avec quelles technologies, et comment le client s'en sert.

 Les deux besoins ne tiennent pas en une heure. Ce que vous choisissez de traiter, dans quel ordre et à quel niveau de fiabilité fait partie de l'évaluation.

 Ce que vous livrez doit fonctionner sur ce poste, lancé par nous à partir de vos instructions.

 Vous êtes consultant : si le besoin vous paraît ambigu, choisissez une interprétation, écrivez-la et continuez.

 Fournis par Saify

 Vos moyens

 Claude Code est à votre disposition et son usage est attendu. Nous regardons autant votre façon de l'utiliser que le résultat.

 Une clé d'API Anthropic vous est fournie dans le fichier .env du dossier, variable ANTHROPIC_API_KEY . Vous l'utilisez si et comme vous le jugez utile. Elle est plafonnée et révoquée après la session. Ne la recopiez pas dans le code et ne commitez pas .env , déjà exclu par .gitignore .

 Le poste dispose de git, Python 3.12 et Node.js. Vous pouvez installer ce dont vous avez besoin. Internet et la documentation sont autorisés, l'aide d'une autre personne ne l'est pas.

 Pendant et à la fin de l'heure

 Ce que vous nous laissez

 Des commits réguliers , au moins toutes les 15 minutes. Le dépôt git est déjà initialisé.

 Un README.md court : comment lancer votre solution, vos choix, ce qui marche et ce qui manque. Distinguez ce que vous avez vérifié vous-même de ce que l'assistant de code affirme.

 L'historique de votre session Claude Code, exporté avec la commande /export .

 La durée est fixe : à la fin de l'heure, on s'arrête là où on en est.

 La deuxième heure

 La restitution

 15 minutes de démonstration , comme devant le responsable middle office. Nous jouerons aussi les gérants et poserons nos propres questions.

 Revue du code : nous choisissons des passages et vous nous les expliquez, y compris ceux écrits par Claude Code.

 Vos choix : pourquoi cette solution, ces technologies, ces priorités, et ce que vous feriez avec une journée de plus.

 Votre méthode : nous parcourons ensemble l'historique de vos prompts.

 Annexe

 Spécifications transmises par les conservateurs

 Conservateur B : fichier à largeur fixe

 Ligne Positions Contenu 

 En-tête 1 · 2-9 H , puis la date d'arrêté AAAAMMJJ , puis un libellé libre 

 Détail 1 D 

 2-4 Code desk du client 

 5-16 Code ISIN 

 17-31 Quantité sur 15 chiffres, 2 décimales implicites 

 Contrôle 1 · 2-7 T , puis le nombre de lignes de détail sur 6 chiffres 

 H20260925DEPOSITAIRE B RELEVE POSITIONS
DOROFR0000010373000000000500000
…
T000013 

 Conservateur C : fichier XML

 Espace de noms urn:orsay:depositaire-c:positions:2026 . Chaque Item est une suite de Dim identifiées par leur attribut prop .

 Élément Contenu 

 Entete/DateArrete Date d'arrêté, JJMMAAAA 

 Entete/NbItems Nombre total d' Item , annulations comprises 

 ACTION C = position, S = annulation 

 COMPTE Compte-titres du client 

 CODE_ISIN · LIBELLE_TITRE Code ISIN et libellé 

 QUANTITE Quantité, virgule décimale 

 LOT Numéro de lot : une position peut être livrée en plusieurs lots 

 <RelevePositions xmlns="urn:orsay:depositaire-c:positions:2026">
 <Entete><DateArrete>25092026</DateArrete><Emetteur>DEPOSITAIRE C</Emetteur><NbItems>9</NbItems></Entete>
 <Positions>
 <Item><Dim prop="ACTION">C</Dim><Dim prop="COMPTE">ORS-PAT</Dim><Dim prop="CODE_ISIN">FR0000050007</Dim>
 <Dim prop="LIBELLE_TITRE">ESSILORLUXOTTICA</Dim><Dim prop="QUANTITE">50000,00</Dim><Dim prop="LOT">1</Dim></Item>
 … 

 Saify · Cas pratique « Orsay Gestion » · Version 3.0 du 27 septembre 2026. Société, fonds, comptes et données fictifs, créés pour le recrutement.
