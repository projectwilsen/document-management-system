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
