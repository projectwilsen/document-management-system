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
