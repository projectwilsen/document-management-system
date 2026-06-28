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
