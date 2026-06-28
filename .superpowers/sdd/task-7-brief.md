# Task 7: Next.js Setup + Auth Pages

## Context
You are implementing Task 7 of a 9-task SaaS MVP — first task of Phase 3 (Next.js Web Dashboard). The FastAPI backend (Tasks 1-4) and desktop app (Tasks 5-6) are complete. Now build the web dashboard.

## Global Constraints
- Next.js 14 App Router, TypeScript, Tailwind CSS
- Dashboard lives at `dashboard/` inside the repo
- `NEXT_PUBLIC_API_URL=http://localhost:8000` (env var)
- Token stored in `localStorage` (`access_token`, `refresh_token`)
- `core/rename_faktur.py` and `ui/app.py` must NOT be modified

## Files to Create
- `dashboard/lib/api.ts`
- `dashboard/lib/auth.tsx`
- `dashboard/app/layout.tsx`
- `dashboard/app/login/page.tsx`
- `dashboard/app/register/page.tsx`
- `dashboard/app/forgot-password/page.tsx`

## IMPORTANT: Scaffold with create-next-app FIRST
Before creating any files, scaffold the project:
```bash
cd dashboard
npx create-next-app@14 . --typescript --tailwind --app --no-src-dir --import-alias "@/*" --yes
```
The `--yes` flag skips all prompts. If the `dashboard/` directory doesn't exist yet, create it first:
```bash
mkdir dashboard
```
If `npx create-next-app` asks for confirmation to install, allow it.

After scaffolding, the following already exist (DO NOT recreate):
- `dashboard/package.json`
- `dashboard/tsconfig.json`
- `dashboard/tailwind.config.ts`
- `dashboard/postcss.config.mjs`
- `dashboard/app/globals.css`
- `dashboard/app/page.tsx` (default — leave it or it will be overwritten by later tasks)

Then create/replace the files specified below.

## Step-by-Step Implementation

### Step 1: Scaffold the project
```bash
mkdir dashboard 2>/dev/null; cd dashboard && npx create-next-app@14 . --typescript --tailwind --app --no-src-dir --import-alias "@/*" --yes
```
Wait for it to complete.

### Step 2: Create `dashboard/lib/api.ts`
```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface QuotaResponse {
  remaining: number | null;
  limit: number | null;
  used: number;
}

export interface MeResponse {
  id: string;
  email: string;
  role: "owner" | "member";
  organization_id: string;
  plan: "free" | "starter" | "pro";
  quota: QuotaResponse;
}

export interface UserOut {
  id: string;
  email: string;
  role: "owner" | "member";
  created_at: string;
}

export const api = {
  register: (email: string, password: string, name?: string, invite?: string) => {
    const url = invite ? `/auth/register?invite=${invite}` : "/auth/register";
    return request<TokenResponse>(url, {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    });
  },
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<MeResponse>("/me"),
  quota: () => request<QuotaResponse>("/usage/quota"),
  listUsers: () => request<UserOut[]>("/admin/users"),
  invite: () => request<{ invite_url: string }>("/admin/users/invite", { method: "POST" }),
  removeUser: (id: string) => request<void>(`/admin/users/${id}`, { method: "DELETE" }),
};
```

### Step 3: Create `dashboard/lib/auth.tsx`
```typescript
"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, MeResponse } from "./api";

interface AuthContextValue {
  user: MeResponse | null;
  loading: boolean;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  logout: () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refresh = async () => {
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    router.push("/login");
  };

  return <AuthContext.Provider value={{ user, loading, logout, refresh }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function saveTokens(access_token: string, refresh_token: string) {
  localStorage.setItem("access_token", access_token);
  localStorage.setItem("refresh_token", refresh_token);
}
```

### Step 4: Create `dashboard/app/layout.tsx`
Replace or create (overwrite the scaffold default):
```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = { title: "Rename Faktur Pajak" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
```

### Step 5: Create `dashboard/app/login/page.tsx`
```typescript
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await api.login(email, password);
      saveTokens(tokens.access_token, tokens.refresh_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">Rename Faktur Pajak</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>
        <div className="mt-4 text-center text-sm space-y-1">
          <a href="/register" className="text-blue-600 hover:underline block">Don't have an account?</a>
          <a href="/forgot-password" className="text-gray-500 hover:underline block">Forgot password?</a>
        </div>
      </div>
    </div>
  );
}
```

### Step 6: Create `dashboard/app/register/page.tsx`
```typescript
"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { api } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

function RegisterForm() {
  const router = useRouter();
  const params = useSearchParams();
  const invite = params.get("invite") ?? undefined;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await api.register(email, password, invite ? undefined : name, invite);
      saveTokens(tokens.access_token, tokens.refresh_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-2 text-center">Create Account</h1>
        {invite && <p className="text-sm text-center text-green-600 mb-4">You've been invited to join a team.</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          {!invite && (
            <div>
              <label className="block text-sm font-medium mb-1">Company / Org Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} required
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm"><a href="/login" className="text-blue-600 hover:underline">Already have an account?</a></p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return <Suspense><RegisterForm /></Suspense>;
}
```

### Step 7: Create `dashboard/app/forgot-password/page.tsx`
```typescript
export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold mb-4">Forgot Password?</h1>
        <p className="text-gray-600 mb-4">
          Automated password reset is not yet available.
        </p>
        <p className="text-gray-600">
          Please contact your administrator to reset your password.
        </p>
        <a href="/login" className="mt-6 inline-block text-blue-600 hover:underline">Back to Login</a>
      </div>
    </div>
  );
}
```

### Step 8: Add `.env.local`
Create `dashboard/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 9: TypeScript build check
```bash
cd dashboard
npx tsc --noEmit
```
If there are TS errors, fix them. Common issues: `err: any` needs `@typescript-eslint/no-explicit-any` suppression, or use `err: unknown` with type guard.

### Step 10: Commit
```bash
git add dashboard/
git commit -m "feat: add Next.js dashboard with auth pages"
```

## Report File
Write your full report to: `.superpowers/sdd/task-7-report.md`

Include:
- What you implemented
- TypeScript build result
- Any deviations from the spec and why
- Any concerns

Then respond with ONLY:
- Status: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
- Commits made (short hashes)
- One-line test summary (tsc result)
- Concerns (if DONE_WITH_CONCERNS)
