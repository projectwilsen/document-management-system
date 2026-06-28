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
