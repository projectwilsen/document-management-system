# Task 7 Report: Next.js Setup + Auth Pages

## What Was Implemented

### Scaffold
- Created `dashboard/` and ran `npx create-next-app@14.2.35` with TypeScript, Tailwind CSS, App Router, no src-dir, `@/*` import alias, and ESLint enabled.
- Note: `--yes` flag alone did not suppress the ESLint interactive prompt in this version of create-next-app; had to pipe `echo "y"` and add `--eslint` flag explicitly to complete non-interactively.

### Files Created / Overwritten
| File | Action |
|------|--------|
| `dashboard/lib/api.ts` | Created — base API client with typed interfaces |
| `dashboard/lib/auth.tsx` | Created — AuthProvider context, useAuth hook, saveTokens |
| `dashboard/app/layout.tsx` | Overwritten — wraps app in AuthProvider, uses Inter font |
| `dashboard/app/login/page.tsx` | Created — login form, redirects to /dashboard on success |
| `dashboard/app/register/page.tsx` | Created — register form with Suspense wrapper for useSearchParams |
| `dashboard/app/forgot-password/page.tsx` | Created — static placeholder page |
| `dashboard/.env.local` | Created — sets NEXT_PUBLIC_API_URL=http://localhost:8000 |

## TypeScript Build Result
`npx tsc --noEmit` — **PASSED, 0 errors, 0 warnings**

## Deviations from Spec

1. **`err: any` replaced with `err: unknown` + type guard** — The spec noted `err: any` might cause TS strict errors. Used `catch (err: unknown)` with `err instanceof Error ? err.message : "..."` fallback in login and register pages to be clean without needing eslint-disable comments.

2. **HTML entity escaping** — Replaced `'` and `'` literal apostrophes in JSX strings with `&apos;` to satisfy Next.js JSX linting rules (affects "Don't have an account?" and "You've been invited" strings).

3. **`eslint-disable-next-line react-hooks/exhaustive-deps`** added above the `useEffect` in `auth.tsx` as instructed in the brief, since `refresh` is stable but not declared in the dependency array.

## Concerns
None. TypeScript is clean, all spec files are in place, and the scaffold is complete.
