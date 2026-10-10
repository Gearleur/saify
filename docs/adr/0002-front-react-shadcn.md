# ADR 0002 : front en React + shadcn/ui (Vite, TypeScript), build servi par FastAPI

- Statut : accepté (remplace la partie « front HTML natif » de l'ADR 0001)
- Date : 2026-10-10

## Contexte
Le back est découpé en couches et testé (176 tests). Le front natif est un `app.js` de 1 700 lignes sans composants, et l'utilisateur le juge trop loin du niveau visé (Attio, dashboard Supabase) en finition comme en fluidité. Le besoin 2 ajoute une interface de questions en flux (SSE). Les contraintes restent : une seule commande pour la démo, une CSP stricte, et aucune donnée inventée côté front.

## Décision
Front en **Vite + React + TypeScript + Tailwind + shadcn/ui** (Radix), sources dans `front/`. Le build (`npm run build`) est écrit dans `middle_office/web/` et servi par FastAPI (`/` et `/static/…`). Il est **commité**, pour que la démo ne demande que `uv run uvicorn middle_office.api:app`. En développement, `npm run dev` lance Vite avec un proxy `/api` vers FastAPI. Le contrat reste `docs/API.md`.

## Alternatives écartées
- Garder le HTML natif : pas de composants, finition et fluidité plafonnées, maintenance difficile.
- Next.js : un serveur Node en plus de FastAPI, donc deux process en démo, pour un rendu serveur sans utilité ici.
- Streamlit : rapide à écrire, mais loin d'un outil métier soigné, et sans contrôle du design.

## Conséquences
- Dépendances npm (Vite, React, Tailwind, Radix/shadcn) : `front/node_modules` est hors git, le build est dans git (à rebâtir après toute modification du front).
- CSP : certains composants Radix injectent des balises `<style>`. Si `style-src 'unsafe-inline'` devient nécessaire, ce relâchement est documenté et limité aux styles (`script-src 'self'` reste strict).
- En production : build en CI plutôt que build commité, et tests de composants (non faits ici).
