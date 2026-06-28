# Dark Mode Design — Full Dark Theme

**Date:** 2026-06-28
**Scope:** dashboard/ (Next.js + Tailwind CSS)
**Approach:** Direct Tailwind class replacement — no new abstractions

## Goal

Convert the entire dashboard UI to a permanent dark theme. The current UI has hardcoded light Tailwind classes that make text invisible when the OS is in dark mode (because `globals.css` already sets `--background: #0a0a0a` via media query, but cards and page backgrounds stay `bg-white`/`bg-gray-50`).

## Files to Change (9 total)

| File | Changes |
|------|---------|
| `app/globals.css` | Remove `@media (prefers-color-scheme: dark)` block; set `:root` to dark values permanently |
| `components/NavBar.tsx` | bg, border, text colors |
| `components/UsageBar.tsx` | Progress bar track colors |
| `app/login/page.tsx` | Page bg, card bg, input styles |
| `app/register/page.tsx` | Page bg, card bg, input styles |
| `app/forgot-password/page.tsx` | Page bg, card bg, text |
| `app/dashboard/page.tsx` | Page bg, card bg, text |
| `app/billing/page.tsx` | Page bg, card bg, text, plan list borders |
| `app/settings/users/page.tsx` | Page bg, card bg, invite box, badges |

## Color Mapping

| Old class | New class | Usage |
|-----------|-----------|-------|
| `bg-gray-50` | `bg-gray-950` | Page backgrounds |
| `bg-white` | `bg-gray-900` | Cards, NavBar, invite link input |
| `text-gray-800` | `text-gray-100` | Strong text (NavBar brand) |
| `text-gray-600` | `text-gray-300` | Body/paragraph text |
| `text-gray-500` | `text-gray-400` | Muted/secondary text |
| `text-gray-700` | `text-gray-200` | invite link text |
| `border-gray-200` | `border-gray-700` | Card/row borders |
| `border-b` (NavBar) | `border-b border-gray-700` | NavBar bottom border |
| `bg-blue-50 border-blue-200` | `bg-blue-950 border-blue-800` | Invite link box |
| `text-blue-700` | `text-blue-300` | Text on blue-950 bg |
| `bg-blue-100 text-blue-700` | `bg-blue-900 text-blue-300` | "owner" role badge |
| `bg-gray-100 text-gray-600` | `bg-gray-700 text-gray-300` | Member role badge |
| `bg-gray-200` | `bg-gray-700` | Progress bar track (UsageBar) |
| `bg-green-100` | `bg-green-950` | Unlimited bar track (UsageBar) |
| Input `border` | `border-gray-600 bg-gray-800 text-gray-100` | All form inputs |

## What Does NOT Change

- Blue accent buttons (`bg-blue-600 hover:bg-blue-700`) — visible on dark
- Green/red/yellow status colors (WhatsApp button, error text, usage bar fills)
- `text-blue-600` links — visible on dark
- `text-red-500`/`text-red-600` error states
- `shadow` on cards — kept (subtle on dark)
- All business logic and component structure

## globals.css After Change

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: #0a0a0a;
  --foreground: #ededed;
}

body {
  color: var(--foreground);
  background: var(--background);
  font-family: Arial, Helvetica, sans-serif;
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
}
```

## No New Dependencies

Pure Tailwind class changes. No new packages, no new components, no new state management.
