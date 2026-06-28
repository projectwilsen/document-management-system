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
