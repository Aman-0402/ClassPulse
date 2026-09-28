---
name: express-api
description: Add/edit backend API routes, auth checks, and DB access for the Express + Passport + Drizzle ORM backend. Use when working in server/routes.ts, server/storage.ts, server/auth.ts, or shared/schema.ts.
---

# Express + Drizzle Backend Conventions

## Layout
- `server/routes.ts` — all API routes, registered via `registerRoutes(app)`. Add new endpoints here, grouped near related existing ones.
- `server/storage.ts` — DB access layer behind an `IStorage` interface. Routes call storage methods, never `db` directly.
- `server/auth.ts` — Passport local strategy, `hashPassword`/`verifyPassword`.
- `server/db.ts` — Drizzle `db` + pg pool (`DATABASE_URL` required).
- `shared/schema.ts` — Drizzle table defs + Zod insert schemas (drizzle-zod). Single source of truth for DB shape, shared with frontend via `@shared/`.
- `shared/routes.ts` — typed API route definitions (path, method, input, response) — keep in sync when adding/changing an endpoint.

## Auth
- Roles: `admin`, `employee` (trainer), `student`. Check with `req.user?.role` inside the route handler — no separate middleware convention beyond that; be explicit per-route.
- Session cookie auth (express-session + connect-pg-simple). Never invent token-based auth.

## Schema changes
- Edit `shared/schema.ts`, then run `npm run db:push` (drizzle-kit push — syncs schema directly, no generated migration files).
- For additive, safe changes needing raw SQL (e.g. backfills, indexes), add a file to `migrations/` using `IF NOT EXISTS` guards — these run on every startup via `server/migrations.ts`.
- Do NOT hand-write drizzle migration files for ordinary schema changes.

## File uploads
- multer, saved to `./uploads/`, served statically at `/uploads/`. Course images go through `POST /api/upload/course-image` (admin only, 16:9 thumbnail).

## Adding an endpoint checklist
1. Add/extend Drizzle table + zod schema in `shared/schema.ts` if needed → `npm run db:push`.
2. Add a method to the `IStorage` interface + implementation in `server/storage.ts`.
3. Add the route in `server/routes.ts`, with explicit `req.user?.role` auth check.
4. Add/update the typed entry in `shared/routes.ts`.
5. Add a corresponding hook in `client/src/hooks/` for frontend consumption.
6. Run `npm run check`.
