# Next.js + TanStack React Table + Prisma + PostgreSQL

Production-oriented **admin table example** with URL-driven **server-side** filtering, multi-column sorting, and offset pagination.

## Stack
- Next.js 16 App Router, React 19, TypeScript
- TanStack Table v8 (`manualPagination`, `manualSorting`, `manualFiltering`)
- Prisma ORM 7 + `@prisma/adapter-pg` + PostgreSQL
- No API route, React Query, or client-side bulk fetch.

## Run locally

Prerequisites: Node.js >=20.19, Docker (optional), and PostgreSQL.

```bash
cp .env.example .env
# Optional: local demo PostgreSQL
docker compose up -d
npm install
npm run db:generate
npm run db:migrate -- --name init
npm run db:seed
npm run dev
```

Visit http://localhost:3000.

If you already have a PostgreSQL instance, set `DATABASE_URL` in `.env` and skip Docker.

## Sample URL

`/?page=1&size=20&name=Alex&roles=ADMIN,MANAGER&statuses=ACTIVE,INVITED&from=2025-01-01&to=2025-12-31&sort=role:asc,createdAt:desc`

`page` is **zero-based** (`page=1` = second page). Sort supports up to 3 columns and can be set through **Shift+click** on column headers. Filters combine via **AND across columns** and **OR within each `roles`/`statuses` selection**. Empty status/role selection means no constraint. Dates are UTC, and both endpoints are inclusive.

## Code map

- `prisma/schema.prisma` — model, enums, useful initial indexes
- `prisma/seed.ts` — idempotent demo records
- `prisma.config.ts` — Prisma 7 datasource + seed configuration
- `src/lib/table-query.ts` — shared URL query parser, whitelist, serializer
- `src/lib/users.ts` — Prisma WHERE / ORDER BY / skip / take / count
- `src/app/page.tsx` — server page parses params and queries DB
- `src/components/admin-table.tsx` — table UI and URL navigation

## Engineering notes

1. `where` is identical for `findMany` and `count`. Multiple different keys are ANDed implicitly by Prisma; selected enum values use `in` (OR). Free-text contains uses PostgreSQL case-insensitive matching.
2. All ordering fields and enum values are **allowlisted** in `parseTableQuery`, and `id ASC` is appended for deterministic ordering. Invalid inputs fall back to defaults.
3. Table works only with the current page's rows. No `getSortedRowModel`, `getFilteredRowModel` or `getPaginationRowModel`.
4. Sorting/filtering resets pagination to the first page. Search text is submitted via button/Enter (rather than issuing a query on every keystroke).
5. `count()` adds a DB query; for very large datasets, consider estimated counts or next-page-only pagination. Offset pagination gets slower at deep offsets; consider cursor pagination then.
6. The demo does not include authentication / authorization. **Protect the admin route and all server data access before deployment.**
7. PostgreSQL `contains`/`ILIKE` may require pg_trgm indexes for large datasets; regular btree indexes do not usually speed up `%substring%` matches. Add targeted GIN trigram indexes via SQL migrations when needed.
8. Date bounds are interpreted in **UTC** for consistent server behavior; adapt for your users' timezone where necessary.
9. This example has basic navigation-state loading. Very high-frequency controls can benefit from optimistic local state or a query-state library. Any local unsent text draft can be reset when navigating directly to a different URL.
10. For reproducible team deployment, commit the generated `package-lock.json` after `npm install`, and commit migrations after `npm run db:migrate`.

## Adapt to your project

Copy the Prisma model or map fields to your current model; copy `table-query.ts`, `users.ts`, `admin-table.tsx`, and adapt the route. Generated Prisma client code is intentionally excluded from the zip: regenerate via `npm run db:generate`.
