# Design: SaaS MVP — Rename Faktur Pajak Coretax

**Date:** 2026-06-28
**Status:** Approved

## Overview

Transform the existing desktop app into a SaaS product using a **Desktop-first Hybrid** approach: the desktop app remains the primary product (local file processing, no uploads), while a FastAPI backend handles auth, subscription management, and usage quota enforcement. A minimal Next.js web dashboard serves as the account control panel.

## Goals

- Users must log in before the desktop app runs
- Subscription plans limit how many documents can be processed per billing period
- Quota is enforced server-side (backend is the source of truth)
- PDF files never leave the user's machine
- Web dashboard for account management, plan info, and org user management
- Data model supports multi-tenant upgrade (goal C) without a schema migration

## Non-Goals (MVP)

- Payment gateway integration — no Stripe, Xendit, Midtrans, or any automated billing
- Email verification flow
- Password reset via email (users are directed to contact admin)
- Web-based PDF processing / upload
- Multiple organizations per user
- Webhook integrations
- Analytics beyond usage count

**Billing in MVP is manual:** user contacts owner via WA/email → owner updates plan directly in the database. Payment gateway is a post-MVP concern once there are paying customers to justify the integration.

## Architecture

```
┌──────────────────────────┐         ┌─────────────────────────────────┐
│   Desktop App            │  HTTPS  │   FastAPI Backend               │
│   (CustomTkinter)        │◄───────►│                                 │
│                          │         │   /auth  — login, register,     │
│   • Login screen (new)   │         │            refresh token        │
│   • Main UI (unchanged)  │         │   /usage — report + check quota │
│   • Stores JWT locally   │         │   /me    — profile, plan info   │
│   • Reports usage        │         │   /admin — org user management  │
│     after each Sync      │         │                                 │
└──────────────────────────┘         └──────────────┬──────────────────┘
                                                     │
┌──────────────────────────┐         ┌──────────────▼──────────────────┐
│   Next.js Dashboard      │  HTTPS  │   Neon (serverless Postgres)    │
│                          │◄───────►│                                 │
│   • Login / register     │         │   organizations                 │
│   • Account & plan info  │         │   users                         │
│   • Usage stats          │         │   subscriptions                 │
│   • Upgrade contact info │         │   usage_logs                    │
│   • Org user management  │         │                                 │
└──────────────────────────┘         └─────────────────────────────────┘
```

## Data Model

```sql
organizations
  id              uuid        PK
  name            text
  created_at      timestamp

users
  id              uuid        PK
  organization_id uuid        FK → organizations.id
  email           text        UNIQUE
  password_hash   text
  role            enum        (owner, member)
  created_at      timestamp

subscriptions
  id              uuid        PK
  organization_id uuid        FK → organizations.id
  plan            enum        (free, starter, pro)
  doc_limit       int         -- NULL = unlimited (pro)
  period_start    date
  period_end      date
  -- payment_ref  text        -- reserved for post-MVP payment gateway reference

usage_logs
  id              uuid        PK
  organization_id uuid        FK → organizations.id
  user_id         uuid        FK → users.id
  files_processed int
  synced_at       timestamp
```

**Quota calculation:** `SELECT SUM(files_processed) FROM usage_logs WHERE organization_id = ? AND synced_at BETWEEN period_start AND period_end`

**Plan tiers (example — final pricing TBD by client feedback):**

| Plan    | Doc limit / month | How activated                        |
|---------|-------------------|--------------------------------------|
| Free    | 50                | Auto on register                     |
| Starter | 500               | Owner manually updates DB after payment |
| Pro     | Unlimited         | Owner manually updates DB after payment |

**How manual plan upgrade works:**
```sql
-- Owner runs this after receiving payment (WA/transfer):
UPDATE subscriptions
SET plan = 'starter', doc_limit = 500,
    period_start = '2026-07-01', period_end = '2026-07-31'
WHERE organization_id = '<org_id>';
```

**Multi-tenancy note:** On signup, the backend silently auto-creates an `organization` and links the new user as `owner`. The user never sees the word "organization" in the MVP UI. When multi-user is added later, the schema requires no changes — only org management UI is new.

## Backend API (FastAPI)

### File structure

```
backend/
├── main.py
├── database.py          ← Neon connection via SQLAlchemy async
├── models.py            ← ORM models
├── schemas.py           ← Pydantic schemas
├── auth/
│   ├── router.py        ← /auth/register, /auth/login, /auth/refresh
│   └── utils.py         ← JWT helpers, bcrypt password hashing
├── usage/
│   └── router.py        ← /usage/quota, /usage/report
├── admin/
│   └── router.py        ← /admin/users (owner only)
└── me/
    └── router.py        ← /me
```

### Endpoints used by the desktop app

| Method | Endpoint        | Purpose                                          |
|--------|-----------------|--------------------------------------------------|
| POST   | /auth/login     | Email + password → JWT access token              |
| GET    | /me             | User info + current plan + quota remaining       |
| GET    | /usage/quota    | `{ remaining: 88, limit: 500 }`                  |
| POST   | /usage/report   | `{ files_processed: 12 }` → decrements quota     |

### Endpoints used by the web dashboard

| Method | Endpoint              | Purpose                                                         |
|--------|-----------------------|-----------------------------------------------------------------|
| POST   | /auth/register        | Create user + auto-create org                                   |
| POST   | /auth/refresh         | Rotate access token                                             |
| GET    | /me                   | Profile + plan info                                             |
| GET    | /admin/users          | List org members (owner only)                                   |
| POST   | /admin/users/invite   | Create pending user + return invite link (no email needed)      |
| DELETE | /admin/users/{id}     | Remove member (owner only)                                      |

### Auth

- JWT access token: 15-minute expiry
- Refresh token: 30-day expiry, stored in httpOnly cookie (web) or `~/.faktur/token.json` (desktop)
- Passwords hashed with bcrypt

## Desktop App Changes

The existing main UI is **unchanged**. Two additions only:

### Login screen (`ui/login.py`)

Shown on startup if no valid token is found locally. Email + password form. Register and password reset open the web dashboard in the browser.

```
┌──────────────────────────────────────┐
│         Rename Faktur Pajak          │
├──────────────────────────────────────┤
│                                      │
│   Email    [_________________________]│
│   Password [_________________________]│
│                                      │
│              [  Login  ]             │
│                                      │
│   Don't have an account? → browser   │
│   Forgot password? → browser         │
│                                      │
└──────────────────────────────────────┘
```

### Status bar (`ui/status_bar.py`)

Added at the bottom of the existing main window:

```
┌──────────────────────────────────────────────────────┐
│  ...existing UI unchanged...                         │
├──────────────────────────────────────────────────────┤
│  📦 Starter Plan  •  312 / 500 docs used  [Upgrade →]│
└──────────────────────────────────────────────────────┘
```

"Upgrade →" opens the `/billing` page in the browser, which shows contact info for upgrading (WA link / email). No payment gateway.

### Modified Sync flow

```
User clicks Sync
      │
      ▼
GET /usage/quota
      │
      ├── remaining = 0 → show "Plan limit reached. Contact us to upgrade." → stop
      │
      └── remaining > 0 → run rename_faktur() as before
                │
                ▼
          POST /usage/report { files_processed: N }
                │
                ▼
          Refresh status bar with new remaining count
```

### New files

```
core/
  api_client.py    ← thin requests wrapper: login(), get_quota(), report_usage()
ui/
  login.py         ← CTkToplevel login window
  status_bar.py    ← plan + usage display strip
```

Token stored at `~/.faktur/token.json`: `{ access_token, refresh_token, expires_at }`.

## Web Dashboard (Next.js)

6 pages. No file processing, no payment gateway — control panel only.

### Pages

```
/login              ← email + password
/register           ← name, email, password
/forgot-password    ← shows "contact your admin" message (email reset is post-MVP)
/dashboard          ← usage bar + recent activity log
/billing            ← current plan info + WhatsApp/email contact to upgrade (NO payment gateway)
/settings/users     ← list members, invite link, remove (owner only)
```

### Dashboard page

```
┌─────────────────────────────────────────────────────┐
│  Rename Faktur Pajak          [Settings] [Logout]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Starter Plan                   [Upgrade Plan →]    │
│                                                     │
│  Documents this period                              │
│  ████████████░░░░░░░░  312 / 500                   │
│                                                     │
│  Recent activity                                    │
│  ┌─────────────────────────────────────────────┐   │
│  │ 28 Jun  •  gerald@email.com  •  12 files    │   │
│  │ 27 Jun  •  gerald@email.com  •  34 files    │   │
│  │ 26 Jun  •  staff@email.com   •   8 files    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Billing page (no payment gateway)

```
┌─────────────────────────────────────────────────────┐
│  Current Plan: Starter  •  500 docs/month           │
│  Period: 1 Jul – 31 Jul 2026                        │
│                                                     │
│  Want to upgrade?                                   │
│  Contact us to activate your new plan:              │
│                                                     │
│  [💬 WhatsApp]   [📧 Email]                         │
│                                                     │
│  Available plans:                                   │
│  Free      50 docs/month    Rp 0                    │
│  Starter  500 docs/month    Rp X                    │
│  Pro      Unlimited         Rp Y                    │
└─────────────────────────────────────────────────────┘
```

### Tech choices

- Next.js 14 App Router
- Tailwind CSS
- JWT in `Authorization` header (simpler for MVP)
- No payment gateway library

### File structure

```
dashboard/
├── app/
│   ├── login/page.tsx
│   ├── register/page.tsx
│   ├── forgot-password/page.tsx
│   ├── dashboard/page.tsx
│   ├── billing/page.tsx
│   └── settings/users/page.tsx
├── lib/
│   └── api.ts          ← typed fetch wrapper for FastAPI
└── components/
    └── UsageBar.tsx
```

## Deployment

| Service    | Platform           | Cost      |
|------------|--------------------|-----------|
| FastAPI    | Render (free tier) | Rp 0      |
| Next.js    | Vercel (free tier) | Rp 0      |
| Database   | Neon (free tier)   | Rp 0      |

No payment gateway account needed for MVP. Total infrastructure cost: Rp 0.

## Repo Structure

```
document-management-system/     ← existing repo
├── main.py                     ← existing, unchanged
├── core/
│   ├── rename_faktur.py        ← existing, unchanged
│   └── api_client.py           ← NEW
├── ui/
│   ├── app.py                  ← modified (add status bar + quota check)
│   ├── login.py                ← NEW
│   └── status_bar.py           ← NEW
├── rename_faktur.py            ← existing CLI, unchanged
├── backend/                    ← NEW FastAPI project
└── dashboard/                  ← NEW Next.js project
```
