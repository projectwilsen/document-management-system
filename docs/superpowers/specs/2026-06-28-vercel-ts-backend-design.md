# Design: TypeScript Backend via Next.js API Routes (feat/saas-mvp-be-ts)

**Date:** 2026-06-28
**Branch:** `feat/saas-mvp-be-ts` (from `feat/saas-mvp`)
**Goal:** Replace FastAPI Python backend with Next.js API Routes so the entire web stack deploys to Vercel with no credit card required.

---

## Context

The current `feat/saas-mvp` branch has:
- FastAPI Python backend (`backend/`)
- Next.js 14 frontend (`dashboard/`)
- Python desktop app + CLI client (`ui/`, `core/`)
- PostgreSQL on Neon

Render's free tier requires a credit card, ruling it out for the backend. Vercel (no card) is perfect for Next.js but awkward for Python. Solution: move the backend logic into Next.js API Routes so everything deploys to Vercel as a single service.

The desktop app (`ui/`, `core/`) is kept — it calls the same API endpoints and only needs its `base_url` updated to the Vercel URL in production.

---

## Branch Strategy

| Branch | Backend | Frontend | Deploy target |
|--------|---------|----------|---------------|
| `feat/saas-mvp` | FastAPI (Python) | Next.js | Render + Vercel |
| `feat/saas-mvp-be-ts` | Next.js API Routes (TS) | Next.js | Vercel only |

**Neither branch is deleted.** `feat/saas-mvp` stays as the Python reference.

---

## Cleanup in New Branch

**Removed:**
- `backend/` — entire FastAPI project
- `processed/` — PDF files, not for version control

**Kept:**
- `dashboard/` — Next.js project (gains API routes)
- `core/` — Python CLI client (used by desktop app)
- `ui/` — Python desktop app
- `uv.lock` — still needed for desktop app deps
- `docs/`

---

## Architecture

Everything lives in `dashboard/`. Next.js serves both the frontend pages and the backend API routes from a single Vercel deployment.

```
dashboard/
├── app/
│   ├── api/                          ← backend (NEW)
│   │   ├── auth/
│   │   │   ├── register/route.ts
│   │   │   ├── login/route.ts
│   │   │   └── refresh/route.ts
│   │   ├── me/route.ts
│   │   ├── usage/
│   │   │   ├── quota/route.ts
│   │   │   └── report/route.ts
│   │   └── admin/users/
│   │       ├── route.ts              (GET list + POST invite)
│   │       └── [id]/route.ts         (DELETE)
│   └── ... (existing pages, unchanged)
├── lib/
│   ├── db/
│   │   ├── schema.ts                 ← Drizzle schema (NEW)
│   │   └── client.ts                 ← Neon + Drizzle client (NEW)
│   ├── jwt.ts                        ← JWT + password utils (NEW)
│   ├── auth-guard.ts                 ← requireAuth helper (NEW)
│   ├── auth.tsx                      ← unchanged
│   └── api.ts                        ← 1 line change: BASE = ""
├── drizzle.config.ts                 ← drizzle-kit config (NEW)
└── drizzle/migrations/               ← auto-generated
```

---

## Database Schema (Drizzle)

Schema mirrors the existing Alembic tables in Neon exactly — no migration needed, `drizzle-kit push` verifies on first run.

**4 tables:**

```ts
// organizations
id: uuid (PK), name: varchar(255), created_at: timestamp

// users
id: uuid (PK), organization_id: uuid (FK), email: varchar(255) unique,
password_hash: varchar(255), role: enum(owner|member), created_at: timestamp

// subscriptions
id: uuid (PK), organization_id: uuid (FK), plan: enum(free|starter|pro),
doc_limit: integer nullable, period_start: date, period_end: date

// usage_logs
id: uuid (PK), organization_id: uuid (FK), user_id: uuid (FK),
files_processed: integer, synced_at: timestamp
```

**Stack:** `drizzle-orm` + `@neondatabase/serverless`

---

## Auth Design

**`lib/jwt.ts`** — all JWT and password utilities:

| Function | Details |
|----------|---------|
| `hashPassword(password)` | bcryptjs, rounds=10 |
| `verifyPassword(plain, hash)` | bcryptjs.compare |
| `signAccessToken(userId)` | jose, exp 15m, type: "access" |
| `signRefreshToken(userId)` | jose, exp 7d, type: "refresh" |
| `signInviteToken(orgId)` | jose, exp 24h, type: "invite" |
| `verifyToken(token)` | jose jwtVerify, throws on invalid |

**`lib/auth-guard.ts`** — extracts and verifies JWT per route:
```ts
export async function requireAuth(req: NextRequest): Promise<{ userId: string }>
// throws NextResponse with 401 if missing or invalid token
```

Each protected route calls `requireAuth(req)` at the top. No Next.js middleware — keeps auth logic explicit and colocated with each route.

---

## API Routes

All paths match the existing FastAPI routes exactly (desktop app compatibility).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | — | Register (new org or invite join) |
| POST | `/api/auth/login` | — | Login, return tokens |
| POST | `/api/auth/refresh` | — | Refresh access token |
| GET | `/api/me` | ✓ | Current user + quota |
| GET | `/api/usage/quota` | ✓ | Current period quota |
| POST | `/api/usage/report` | ✓ | Report files processed |
| GET | `/api/admin/users` | ✓ owner | List org users |
| POST | `/api/admin/users/invite` | ✓ owner | Generate invite link |
| DELETE | `/api/admin/users/[id]` | ✓ owner | Remove user from org |

**Register logic (no invite):** create org → create user (owner) → create subscription (free, limit 50, current month period)

**Register logic (with invite):** decode invite token → join existing org as member

---

## Frontend Changes

**`lib/api.ts`** — one line change:
```ts
// before
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
// after
const BASE = process.env.NEXT_PUBLIC_API_URL ?? ""
```

Same-origin requests to `/api/*` — no CORS needed, no external URL. All existing page components and the `api` object are unchanged.

---

## Environment Variables

| Variable | Used by | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `lib/db/client.ts` | Neon connection string (same as current) |
| `JWT_SECRET` | `lib/jwt.ts` | Can reuse existing secret |
| `NEXT_PUBLIC_URL` | invite link generation | Replaces `DASHBOARD_URL` from Python config |

---

## New Dependencies

Added to `dashboard/package.json`:

```json
"dependencies": {
  "drizzle-orm": "^0.43",
  "@neondatabase/serverless": "^0.10",
  "jose": "^5.0",
  "bcryptjs": "^2.4"
},
"devDependencies": {
  "drizzle-kit": "^0.31",
  "@types/bcryptjs": "^2.4"
}
```

---

## Desktop App Compatibility

`core/api_client.py` is unchanged. It uses `base_url` parameter — in production, pass the Vercel URL:

```python
client = ApiClient(base_url="https://<project>.vercel.app")
```

All API paths are identical, so the desktop app works against the TypeScript backend with zero code changes.

---

## Out of Scope

- No changes to `ui/` or `core/`
- No new features beyond what exists in `feat/saas-mvp`
- No tests (matching current state of the project)
