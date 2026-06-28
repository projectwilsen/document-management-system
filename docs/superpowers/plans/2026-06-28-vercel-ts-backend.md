# TypeScript Backend (Next.js API Routes) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the FastAPI Python backend with Next.js Route Handlers inside `dashboard/` so the entire web stack deploys to Vercel from a single service.

**Architecture:** All backend logic moves into `dashboard/app/` as Next.js Route Handlers co-located with page routes (e.g. `app/auth/login/route.ts` → `/auth/login`). Routes are placed **outside** of `app/api/` so that paths match the Python backend exactly — enabling the desktop app's `core/api_client.py` to work against the Vercel URL without code changes. Drizzle ORM talks to the existing Neon PostgreSQL database via `@neondatabase/serverless`. JWT auth is reimplemented with `jose` and `bcryptjs`.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Drizzle ORM, `@neondatabase/serverless`, `jose`, `bcryptjs`, Neon PostgreSQL, Vercel

## Global Constraints

- Branch: `feat/saas-mvp-be-ts` — never commit to `feat/saas-mvp`
- All work happens inside `dashboard/` after cleanup in Task 1
- API paths must match the Python backend exactly — no `/api/` prefix
  - `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
  - `GET /me`
  - `GET /usage/quota`, `POST /usage/report`
  - `GET /admin/users`, `POST /admin/users/invite`, `DELETE /admin/users/[id]`
- Response JSON keys must be snake_case where `lib/api.ts` expects them (`organization_id`, `created_at`)
- No new features beyond what exists in `feat/saas-mvp`
- `drizzle-kit push` (not migrate) — schema already exists in Neon from Alembic
- Local env file: `dashboard/.env.local`
- `ui/` and `core/` are not touched

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `dashboard/lib/db/schema.ts` | Create | Drizzle table definitions matching existing Neon schema |
| `dashboard/lib/db/client.ts` | Create | Neon + Drizzle client singleton |
| `dashboard/drizzle.config.ts` | Create | drizzle-kit config |
| `dashboard/lib/jwt.ts` | Create | hashPassword, verifyPassword, sign/verify tokens |
| `dashboard/lib/auth-guard.ts` | Create | requireAuth helper used by all protected routes |
| `dashboard/lib/api.ts` | Modify | Change BASE default from `"http://localhost:8000"` to `""` |
| `dashboard/app/auth/register/route.ts` | Create | POST /auth/register |
| `dashboard/app/auth/login/route.ts` | Create | POST /auth/login |
| `dashboard/app/auth/refresh/route.ts` | Create | POST /auth/refresh |
| `dashboard/app/me/route.ts` | Create | GET /me |
| `dashboard/app/usage/quota/route.ts` | Create | GET /usage/quota |
| `dashboard/app/usage/report/route.ts` | Create | POST /usage/report |
| `dashboard/app/admin/users/route.ts` | Create | GET /admin/users |
| `dashboard/app/admin/users/invite/route.ts` | Create | POST /admin/users/invite |
| `dashboard/app/admin/users/[id]/route.ts` | Create | DELETE /admin/users/[id] |

> **Why routes are NOT in `app/api/`:** Next.js 14 App Router allows `route.ts` files anywhere in `app/`. Placing them at `app/auth/login/route.ts` exposes the endpoint at `/auth/login`, matching the Python FastAPI paths exactly. The existing page routes (`app/login/page.tsx`, `app/register/page.tsx`, etc.) do not conflict because they use different path segments.

---

## Task 1: Create Branch & Cleanup

**Files:**
- Delete: `backend/`
- Delete: `processed/`

- [ ] **Step 1: Create new branch from feat/saas-mvp**

```bash
git checkout feat/saas-mvp
git checkout -b feat/saas-mvp-be-ts
```

- [ ] **Step 2: Verify you are on the correct branch**

```bash
git branch
```
Expected: `* feat/saas-mvp-be-ts`

- [ ] **Step 3: Delete the Python backend**

```bash
git rm -r backend/
```

- [ ] **Step 4: Delete the processed PDF folder**

`processed/` is untracked, delete it manually:
```bash
rm -rf processed/
```

- [ ] **Step 5: Verify remaining structure**

```bash
ls
```
Expected: `core/  dashboard/  docs/  ui/  uv.lock` (plus any root dotfiles)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove Python backend and processed folder for TS rewrite"
```

---

## Task 2: Install Dependencies

**Files:**
- Modify: `dashboard/package.json`

All steps in this task run from the `dashboard/` directory.

- [ ] **Step 1: Install runtime dependencies**

```bash
cd dashboard
npm install drizzle-orm @neondatabase/serverless jose bcryptjs
```

- [ ] **Step 2: Install dev dependencies**

```bash
npm install -D drizzle-kit @types/bcryptjs
```

- [ ] **Step 3: Verify package.json**

Confirm these appear in `dashboard/package.json`:
```json
"dependencies": {
  "drizzle-orm": "...",
  "@neondatabase/serverless": "...",
  "jose": "...",
  "bcryptjs": "..."
},
"devDependencies": {
  "drizzle-kit": "...",
  "@types/bcryptjs": "..."
}
```

- [ ] **Step 4: Create `dashboard/.env.local`**

```
DATABASE_URL=postgresql://neondb_owner:<password>@ep-polished-river-ah2abbvz-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
JWT_SECRET=<your-jwt-secret>
NEXT_PUBLIC_URL=http://localhost:3000
```

> Use the Neon connection string from your Neon dashboard. The `@neondatabase/serverless` package uses the standard `sslmode=require` format (not `ssl=require` as asyncpg used).

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add drizzle, neon serverless, jose, bcryptjs dependencies"
```

---

## Task 3: Database Schema & Client

**Files:**
- Create: `dashboard/lib/db/schema.ts`
- Create: `dashboard/lib/db/client.ts`
- Create: `dashboard/drizzle.config.ts`

**Produces:**
- `db` — imported as `import { db } from "@/lib/db/client"`
- `organizations`, `users`, `subscriptions`, `usageLogs` — imported as `import { organizations, users, subscriptions, usageLogs } from "@/lib/db/schema"`

- [ ] **Step 1: Create `dashboard/lib/db/schema.ts`**

> The `plan` and `role` columns use `varchar` (not `pgEnum`) because the Alembic migration created them as `VARCHAR` with CHECK constraints (`native_enum=False`), not as PostgreSQL ENUM types.

```ts
import { pgTable, uuid, varchar, timestamp, integer, date } from "drizzle-orm/pg-core"

export const organizations = pgTable("organizations", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: varchar("name", { length: 255 }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
})

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  organizationId: uuid("organization_id").notNull().references(() => organizations.id),
  email: varchar("email", { length: 255 }).notNull().unique(),
  passwordHash: varchar("password_hash", { length: 255 }).notNull(),
  role: varchar("role", { length: 50 }).notNull().default("owner")
    .$type<"owner" | "member">(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
})

export const subscriptions = pgTable("subscriptions", {
  id: uuid("id").primaryKey().defaultRandom(),
  organizationId: uuid("organization_id").notNull().references(() => organizations.id),
  plan: varchar("plan", { length: 50 }).notNull().default("free")
    .$type<"free" | "starter" | "pro">(),
  docLimit: integer("doc_limit"),
  periodStart: date("period_start").notNull(),
  periodEnd: date("period_end").notNull(),
})

export const usageLogs = pgTable("usage_logs", {
  id: uuid("id").primaryKey().defaultRandom(),
  organizationId: uuid("organization_id").notNull().references(() => organizations.id),
  userId: uuid("user_id").notNull().references(() => users.id),
  filesProcessed: integer("files_processed").notNull(),
  syncedAt: timestamp("synced_at", { withTimezone: true }).defaultNow().notNull(),
})
```

- [ ] **Step 2: Create `dashboard/lib/db/client.ts`**

```ts
import { neon } from "@neondatabase/serverless"
import { drizzle } from "drizzle-orm/neon-http"
import * as schema from "./schema"

const sql = neon(process.env.DATABASE_URL!)
export const db = drizzle(sql, { schema })
```

- [ ] **Step 3: Create `dashboard/drizzle.config.ts`**

```ts
import { defineConfig } from "drizzle-kit"

export default defineConfig({
  schema: "./lib/db/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
})
```

- [ ] **Step 4: Run drizzle-kit push to verify schema matches Neon**

```bash
npx drizzle-kit push
```

Expected: drizzle-kit connects to Neon and reports the schema is already in sync. If it prompts to create tables, answer `No` and check that column names and types in `schema.ts` match exactly.

- [ ] **Step 5: Commit**

```bash
git add lib/db/ drizzle.config.ts
git commit -m "feat: add drizzle schema and neon client"
```

---

## Task 4: JWT Utilities & Auth Guard

**Files:**
- Create: `dashboard/lib/jwt.ts`
- Create: `dashboard/lib/auth-guard.ts`
- Modify: `dashboard/lib/api.ts`

**Produces:**
- `hashPassword(password: string): Promise<string>`
- `verifyPassword(plain: string, hash: string): Promise<boolean>`
- `signAccessToken(userId: string): Promise<string>` — exp 15m, `{ sub, type: "access" }`
- `signRefreshToken(userId: string): Promise<string>` — exp 30d, `{ sub, type: "refresh" }`
- `signInviteToken(orgId: string): Promise<string>` — exp 7d, `{ org_id, type: "invite" }`
- `verifyToken(token: string): Promise<JWTPayload>` — throws on invalid/expired
- `requireAuth(req: NextRequest): Promise<{ userId: string } | NextResponse>` — 401 if missing/invalid

- [ ] **Step 1: Create `dashboard/lib/jwt.ts`**

```ts
import { SignJWT, jwtVerify, type JWTPayload } from "jose"
import bcrypt from "bcryptjs"

const secret = new TextEncoder().encode(process.env.JWT_SECRET!)

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10)
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash)
}

export async function signAccessToken(userId: string): Promise<string> {
  return new SignJWT({ sub: userId, type: "access" })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("15m")
    .sign(secret)
}

export async function signRefreshToken(userId: string): Promise<string> {
  return new SignJWT({ sub: userId, type: "refresh" })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("30d")
    .sign(secret)
}

export async function signInviteToken(orgId: string): Promise<string> {
  return new SignJWT({ org_id: orgId, type: "invite" })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("7d")
    .sign(secret)
}

export async function verifyToken(token: string): Promise<JWTPayload> {
  const { payload } = await jwtVerify(token, secret)
  return payload
}
```

- [ ] **Step 2: Create `dashboard/lib/auth-guard.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { verifyToken } from "./jwt"

export async function requireAuth(req: NextRequest): Promise<{ userId: string } | NextResponse> {
  const authHeader = req.headers.get("authorization")
  const token = authHeader?.startsWith("Bearer ") ? authHeader.slice(7) : null
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
  }
  try {
    const payload = await verifyToken(token)
    if (payload.type !== "access" || !payload.sub) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
    }
    return { userId: payload.sub as string }
  } catch {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
  }
}
```

- [ ] **Step 3: Update `dashboard/lib/api.ts` — change BASE default**

Find line 1:
```ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
```

Replace with:
```ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? ""
```

This makes the web app call same-origin routes like `/auth/login`, `/me`, etc.

- [ ] **Step 4: Commit**

```bash
git add lib/jwt.ts lib/auth-guard.ts lib/api.ts
git commit -m "feat: add JWT utilities, auth guard; update api base URL to same-origin"
```

---

## Task 5: Auth Routes

**Files:**
- Create: `dashboard/app/auth/register/route.ts`
- Create: `dashboard/app/auth/login/route.ts`
- Create: `dashboard/app/auth/refresh/route.ts`

**Consumes:**
- `db`, `organizations`, `users`, `subscriptions` from Task 3
- `hashPassword`, `signAccessToken`, `signRefreshToken`, `verifyToken` from Task 4

- [ ] **Step 1: Create `dashboard/app/auth/register/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { organizations, users, subscriptions } from "@/lib/db/schema"
import { hashPassword, signAccessToken, signRefreshToken, verifyToken } from "@/lib/jwt"

function currentMonthRange(): { periodStart: string; periodEnd: string } {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const lastDay = new Date(year, month + 1, 0).getDate()
  const pad = (n: number) => String(n).padStart(2, "0")
  return {
    periodStart: `${year}-${pad(month + 1)}-01`,
    periodEnd: `${year}-${pad(month + 1)}-${pad(lastDay)}`,
  }
}

export async function POST(req: NextRequest) {
  const { email, password, name } = await req.json()
  const invite = req.nextUrl.searchParams.get("invite")

  const existing = await db.select({ id: users.id }).from(users)
    .where(eq(users.email, email)).limit(1)
  if (existing.length > 0) {
    return NextResponse.json({ detail: "Email already registered" }, { status: 400 })
  }

  const passwordHash = await hashPassword(password)

  if (invite) {
    let orgId: string
    try {
      const payload = await verifyToken(invite)
      if (payload.type !== "invite" || !payload.org_id) throw new Error()
      orgId = payload.org_id as string
    } catch {
      return NextResponse.json({ detail: "Invalid or expired invite link" }, { status: 400 })
    }

    const [user] = await db.insert(users).values({
      organizationId: orgId,
      email,
      passwordHash,
      role: "member",
    }).returning()

    return NextResponse.json({
      access_token: await signAccessToken(user.id),
      refresh_token: await signRefreshToken(user.id),
      token_type: "bearer",
    }, { status: 201 })
  }

  if (!name) {
    return NextResponse.json(
      { detail: "name is required when registering without invite" },
      { status: 422 }
    )
  }

  const [org] = await db.insert(organizations).values({ name }).returning()

  const [user] = await db.insert(users).values({
    organizationId: org.id,
    email,
    passwordHash,
    role: "owner",
  }).returning()

  const { periodStart, periodEnd } = currentMonthRange()
  await db.insert(subscriptions).values({
    organizationId: org.id,
    plan: "free",
    docLimit: 50,
    periodStart,
    periodEnd,
  })

  return NextResponse.json({
    access_token: await signAccessToken(user.id),
    refresh_token: await signRefreshToken(user.id),
    token_type: "bearer",
  }, { status: 201 })
}
```

- [ ] **Step 2: Create `dashboard/app/auth/login/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users } from "@/lib/db/schema"
import { verifyPassword, signAccessToken, signRefreshToken } from "@/lib/jwt"

export async function POST(req: NextRequest) {
  const { email, password } = await req.json()

  const [user] = await db.select().from(users).where(eq(users.email, email)).limit(1)
  if (!user || !(await verifyPassword(password, user.passwordHash))) {
    return NextResponse.json({ detail: "Invalid credentials" }, { status: 401 })
  }

  return NextResponse.json({
    access_token: await signAccessToken(user.id),
    refresh_token: await signRefreshToken(user.id),
    token_type: "bearer",
  })
}
```

- [ ] **Step 3: Create `dashboard/app/auth/refresh/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users } from "@/lib/db/schema"
import { verifyToken, signAccessToken, signRefreshToken } from "@/lib/jwt"

export async function POST(req: NextRequest) {
  const { refresh_token } = await req.json()

  let userId: string
  try {
    const payload = await verifyToken(refresh_token)
    if (payload.type !== "refresh" || !payload.sub) throw new Error()
    userId = payload.sub as string
  } catch {
    return NextResponse.json({ detail: "Invalid refresh token" }, { status: 401 })
  }

  const [user] = await db.select({ id: users.id }).from(users)
    .where(eq(users.id, userId)).limit(1)
  if (!user) {
    return NextResponse.json({ detail: "User not found" }, { status: 401 })
  }

  return NextResponse.json({
    access_token: await signAccessToken(user.id),
    refresh_token: await signRefreshToken(user.id),
    token_type: "bearer",
  })
}
```

- [ ] **Step 4: Smoke test auth routes**

Start the dev server: `npm run dev`

Test register (run from `dashboard/`):
```bash
curl -s -X POST http://localhost:3000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secret123","name":"Test Org"}' | jq .
```
Expected: `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }`

Test login:
```bash
curl -s -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secret123"}' | jq .
```
Expected: same token shape

Test wrong password:
```bash
curl -s -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrong"}' | jq .
```
Expected: `{ "detail": "Invalid credentials" }` with HTTP 401

- [ ] **Step 5: Commit**

```bash
git add app/auth/
git commit -m "feat: add auth routes (register, login, refresh)"
```

---

## Task 6: Me & Usage Routes

**Files:**
- Create: `dashboard/app/me/route.ts`
- Create: `dashboard/app/usage/quota/route.ts`
- Create: `dashboard/app/usage/report/route.ts`

**Consumes:**
- `db`, `users`, `subscriptions`, `usageLogs` from Task 3
- `requireAuth` from Task 4

- [ ] **Step 1: Create `dashboard/app/me/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { and, desc, eq, sql } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users, subscriptions, usageLogs } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"

export async function GET(req: NextRequest) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const [user] = await db.select().from(users).where(eq(users.id, auth.userId)).limit(1)
  if (!user) return NextResponse.json({ detail: "Not found" }, { status: 404 })

  const [sub] = await db.select().from(subscriptions)
    .where(eq(subscriptions.organizationId, user.organizationId))
    .orderBy(desc(subscriptions.periodEnd))
    .limit(1)

  const [row] = await db.select({
    total: sql<number>`coalesce(sum(${usageLogs.filesProcessed}), 0)`,
  }).from(usageLogs).where(and(
    eq(usageLogs.organizationId, user.organizationId),
    sql`${usageLogs.syncedAt}::date >= ${sub.periodStart}::date`,
    sql`${usageLogs.syncedAt}::date <= ${sub.periodEnd}::date`,
  ))

  const used = Number(row.total)
  const remaining = sub.docLimit === null ? null : Math.max(0, sub.docLimit - used)

  return NextResponse.json({
    id: user.id,
    email: user.email,
    role: user.role,
    organization_id: user.organizationId,
    plan: sub.plan,
    quota: { used, limit: sub.docLimit, remaining },
  })
}
```

- [ ] **Step 2: Create `dashboard/app/usage/quota/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { and, desc, eq, sql } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users, subscriptions, usageLogs } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"

export async function GET(req: NextRequest) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const [user] = await db.select({ organizationId: users.organizationId })
    .from(users).where(eq(users.id, auth.userId)).limit(1)
  if (!user) return NextResponse.json({ detail: "Not found" }, { status: 404 })

  const [sub] = await db.select().from(subscriptions)
    .where(eq(subscriptions.organizationId, user.organizationId))
    .orderBy(desc(subscriptions.periodEnd))
    .limit(1)

  const [row] = await db.select({
    total: sql<number>`coalesce(sum(${usageLogs.filesProcessed}), 0)`,
  }).from(usageLogs).where(and(
    eq(usageLogs.organizationId, user.organizationId),
    sql`${usageLogs.syncedAt}::date >= ${sub.periodStart}::date`,
    sql`${usageLogs.syncedAt}::date <= ${sub.periodEnd}::date`,
  ))

  const used = Number(row.total)
  const remaining = sub.docLimit === null ? null : Math.max(0, sub.docLimit - used)

  return NextResponse.json({ used, limit: sub.docLimit, remaining })
}
```

- [ ] **Step 3: Create `dashboard/app/usage/report/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { and, desc, eq, sql } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users, subscriptions, usageLogs } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"

export async function POST(req: NextRequest) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const { files_processed } = await req.json()

  const [user] = await db.select().from(users).where(eq(users.id, auth.userId)).limit(1)
  if (!user) return NextResponse.json({ detail: "Not found" }, { status: 404 })

  const [sub] = await db.select().from(subscriptions)
    .where(eq(subscriptions.organizationId, user.organizationId))
    .orderBy(desc(subscriptions.periodEnd))
    .limit(1)

  const [row] = await db.select({
    total: sql<number>`coalesce(sum(${usageLogs.filesProcessed}), 0)`,
  }).from(usageLogs).where(and(
    eq(usageLogs.organizationId, user.organizationId),
    sql`${usageLogs.syncedAt}::date >= ${sub.periodStart}::date`,
    sql`${usageLogs.syncedAt}::date <= ${sub.periodEnd}::date`,
  ))

  const used = Number(row.total)

  if (sub.docLimit !== null && used >= sub.docLimit) {
    return NextResponse.json({ detail: "Quota exceeded" }, { status: 402 })
  }

  await db.insert(usageLogs).values({
    organizationId: user.organizationId,
    userId: user.id,
    filesProcessed: files_processed,
  })

  const remaining = sub.docLimit === null
    ? null
    : Math.max(0, sub.docLimit - used - files_processed)

  return NextResponse.json({ used: used + files_processed, limit: sub.docLimit, remaining })
}
```

- [ ] **Step 4: Smoke test me and usage routes**

```bash
TOKEN=$(curl -s -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secret123"}' | jq -r .access_token)

curl -s http://localhost:3000/me \
  -H "Authorization: Bearer $TOKEN" | jq .
```
Expected: `{ "id": "...", "email": "test@example.com", "role": "owner", "organization_id": "...", "plan": "free", "quota": { "used": 0, "limit": 50, "remaining": 50 } }`

```bash
curl -s http://localhost:3000/usage/quota \
  -H "Authorization: Bearer $TOKEN" | jq .
```
Expected: `{ "used": 0, "limit": 50, "remaining": 50 }`

```bash
curl -s -X POST http://localhost:3000/usage/report \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"files_processed": 5}' | jq .
```
Expected: `{ "used": 5, "limit": 50, "remaining": 45 }`

- [ ] **Step 5: Commit**

```bash
git add app/me/ app/usage/
git commit -m "feat: add me and usage routes"
```

---

## Task 7: Admin Routes

**Files:**
- Create: `dashboard/app/admin/users/route.ts`
- Create: `dashboard/app/admin/users/invite/route.ts`
- Create: `dashboard/app/admin/users/[id]/route.ts`

**Consumes:**
- `db`, `users` from Task 3
- `requireAuth` from Task 4
- `signInviteToken` from Task 4

- [ ] **Step 1: Create `dashboard/app/admin/users/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"

export async function GET(req: NextRequest) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const [currentUser] = await db.select().from(users)
    .where(eq(users.id, auth.userId)).limit(1)
  if (!currentUser) return NextResponse.json({ detail: "Not found" }, { status: 404 })
  if (currentUser.role !== "owner") {
    return NextResponse.json({ detail: "Owner role required" }, { status: 403 })
  }

  const orgUsers = await db.select().from(users)
    .where(eq(users.organizationId, currentUser.organizationId))

  return NextResponse.json(orgUsers.map(u => ({
    id: u.id,
    email: u.email,
    role: u.role,
    created_at: u.createdAt,
  })))
}
```

- [ ] **Step 2: Create `dashboard/app/admin/users/invite/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"
import { signInviteToken } from "@/lib/jwt"

export async function POST(req: NextRequest) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const [currentUser] = await db.select().from(users)
    .where(eq(users.id, auth.userId)).limit(1)
  if (!currentUser) return NextResponse.json({ detail: "Not found" }, { status: 404 })
  if (currentUser.role !== "owner") {
    return NextResponse.json({ detail: "Owner role required" }, { status: 403 })
  }

  const token = await signInviteToken(currentUser.organizationId)
  const baseUrl = process.env.NEXT_PUBLIC_URL ?? "http://localhost:3000"

  return NextResponse.json({ invite_url: `${baseUrl}/register?invite=${token}` })
}
```

- [ ] **Step 3: Create `dashboard/app/admin/users/[id]/route.ts`**

```ts
import { NextRequest, NextResponse } from "next/server"
import { and, eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const [currentUser] = await db.select().from(users)
    .where(eq(users.id, auth.userId)).limit(1)
  if (!currentUser) return NextResponse.json({ detail: "Not found" }, { status: 404 })
  if (currentUser.role !== "owner") {
    return NextResponse.json({ detail: "Owner role required" }, { status: 403 })
  }

  if (params.id === auth.userId) {
    return NextResponse.json({ detail: "Cannot remove yourself" }, { status: 400 })
  }

  const [target] = await db.select().from(users).where(
    and(
      eq(users.id, params.id),
      eq(users.organizationId, currentUser.organizationId)
    )
  ).limit(1)

  if (!target) {
    return NextResponse.json({ detail: "User not found in your org" }, { status: 404 })
  }

  await db.delete(users).where(eq(users.id, params.id))
  return new NextResponse(null, { status: 204 })
}
```

- [ ] **Step 4: Smoke test admin routes**

```bash
TOKEN=$(curl -s -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secret123"}' | jq -r .access_token)

curl -s http://localhost:3000/admin/users \
  -H "Authorization: Bearer $TOKEN" | jq .
```
Expected: `[{ "id": "...", "email": "test@example.com", "role": "owner", "created_at": "..." }]`

```bash
curl -s -X POST http://localhost:3000/admin/users/invite \
  -H "Authorization: Bearer $TOKEN" | jq .
```
Expected: `{ "invite_url": "http://localhost:3000/register?invite=<jwt>" }`

- [ ] **Step 5: Commit**

```bash
git add app/admin/
git commit -m "feat: add admin routes (list users, invite, remove)"
```

---

## Task 8: Browser Test & Push to GitHub

- [ ] **Step 1: Run the dev server**

```bash
npm run dev
```

- [ ] **Step 2: Full browser flow test**

1. Open `http://localhost:3000`
2. Register a new account → should redirect to `/dashboard`
3. Dashboard should show plan "free", quota 0/50
4. Navigate to Settings → Users → should list the owner
5. Click "Generate Invite" → should produce a link
6. Open the invite link in a private window → register a member account
7. Back in the owner window, Users should now show 2 users
8. Delete the member → they disappear from the list

- [ ] **Step 3: Fix any issues found in browser testing before continuing**

- [ ] **Step 4: Push branch to GitHub**

```bash
git push -u origin feat/saas-mvp-be-ts
```

- [ ] **Step 5: Confirm both branches exist on GitHub**

Open `https://github.com/projectwilsen/document-management-system/branches` and verify:
- `feat/saas-mvp` — Python backend (untouched)
- `feat/saas-mvp-be-ts` — TypeScript backend (new)

---

## Vercel Deploy (after Task 8 passes)

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import `projectwilsen/document-management-system`
3. Select branch: `feat/saas-mvp-be-ts`
4. Set **Root Directory**: `dashboard`
5. Framework: Next.js (auto-detected)
6. Environment variables:
   ```
   DATABASE_URL=<neon connection string with sslmode=require>
   JWT_SECRET=<generate with: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))">
   NEXT_PUBLIC_URL=https://<your-project>.vercel.app
   ```
7. Deploy — one service, no separate backend needed
