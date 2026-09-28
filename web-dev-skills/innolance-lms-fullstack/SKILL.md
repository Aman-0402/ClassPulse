---
name: innolance-lms-fullstack
description: End-to-end workflow for adding a full-stack feature (DB → API → frontend) in the Innolance LMS repo (Node 22 ESM, React+TS/Vite/Wouter, Express/Passport, Drizzle/Postgres). Use when a task spans schema, routes, and UI together, not just one layer.
---

# Innolance LMS — Full-Stack Feature Workflow

Companion to [[react-frontend]] (client layer) and [[express-api]] (server layer) — use this one when a feature touches all three layers: DB schema, API route, and UI.

## Order of operations
1. **Schema** — edit `shared/schema.ts` (Drizzle table + drizzle-zod insert schema). Run `npm run db:push` to sync Postgres (no migration files for schema changes).
2. **Storage** — add method(s) to `IStorage` in `server/storage.ts`.
3. **Route** — add endpoint in `server/routes.ts`, explicit `req.user?.role` check (`admin` / `employee` / `student`).
4. **Typed contract** — update `shared/routes.ts` so path/method/input/response stay in sync.
5. **Frontend hook** — add/extend a hook in `client/src/hooks/` (TanStack Query v5, `credentials: "include"` on every fetch).
6. **UI** — build page/component under the right role directory in `client/src/pages/`, using shadcn/ui + Tailwind, react-hook-form + zod for forms, Wouter for routing.
7. **Verify** — `npm run check` (tsc --noEmit); if UI-facing, start `npm run dev` and click through the golden path in a browser before calling it done.

## Environment
- `DATABASE_URL` in `.env` is required for the server to start.
- `tsx watch server/index.ts` auto-restarts on server file changes; Vite runs as Express middleware on the same port (5000) — one dev server for both.
- Uploads: multer → `./uploads/`, served at `/uploads/<filename>`.

## Don't
- Don't add React Router, styled-components, or hand-rolled token auth — this repo uses Wouter, Tailwind/shadcn, and session-cookie auth exclusively.
- Don't generate drizzle-kit migration files for ordinary schema edits — `db:push` handles it; raw SQL in `migrations/` is only for additive, `IF NOT EXISTS`-safe changes.
