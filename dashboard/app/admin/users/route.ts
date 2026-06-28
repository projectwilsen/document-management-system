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
