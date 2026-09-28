---
name: react-frontend
description: Build/edit React + TypeScript frontend features using Wouter routing, TanStack Query v5 server state, react-hook-form + zod forms, and Tailwind/shadcn UI. Use when adding pages, components, hooks, or forms in client/src/.
---

# React Frontend Conventions

## Routing (Wouter, not React Router)
- Use `<Link href="...">` and `useLocation()` / `useRoute()` from `wouter`.
- Pages live in `client/src/pages/{admin,employee,student}/` by role, or top-level for public pages (`landing-page.tsx`, `login.tsx`).
- Wrap authenticated pages in `components/layout-shell.tsx` (sidebar + top nav). Public pages use `components/landing-navbar.tsx` and skip auth redirect.

## Server state (TanStack Query v5)
- All API-calling hooks live in `client/src/hooks/` (e.g. `use-courses.ts`, `use-lms.ts`, `use-auth.ts`). Don't call `fetch` directly from components.
- Every fetch MUST include `credentials: "include"` (session cookie auth).
- Use `useQuery` for reads, `useMutation` + `queryClient.invalidateQueries` for writes.
- Auth/session state comes from `use-auth.ts`'s context, not ad-hoc `useQuery` calls per component.

## Forms
- react-hook-form + zod via `@hookform/resolvers`. Derive the zod schema from `shared/schema.ts` insert schemas (drizzle-zod) where the form maps to a DB table — don't hand-write a parallel schema.

## Styling
- Tailwind utility classes first. Custom CSS only in `client/src/styles/` (e.g. `repel-glitch.css`, `login.css`). No inline `style={{}}`, no styled-components.
- UI primitives come from shadcn/ui (Radix). Check `client/src/components/ui/` before building a new primitive.
- Animations: Framer Motion.

## Imports
- `@/` → `client/src/`. `@shared/` → `shared/` (for types/schemas shared with server).

## Checklist for a new page/feature
1. Define/extend types in `shared/schema.ts` if it touches the DB; run `npm run db:push`.
2. Add/extend a hook in `client/src/hooks/` for the API call (credentials included).
3. Build the page/component using existing shadcn primitives + Tailwind.
4. Wire route via Wouter, respect role-based page directories.
5. Run `npm run check` (tsc --noEmit) before considering done.
