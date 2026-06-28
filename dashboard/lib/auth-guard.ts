import { NextRequest, NextResponse } from "next/server"
import { verifyToken } from "./jwt"

export async function requireAuth(req: NextRequest): Promise<{ userId: string } | NextResponse> {
  const authHeader = req.headers.get("authorization")
  const token = authHeader?.startsWith("Bearer ") ? authHeader.slice(7) : null
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
  }
  try {
    const payload = await verifyToken(token)
    if (payload.type !== "access" || !payload.sub) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
    }
    return { userId: payload.sub as string }
  } catch {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
  }
}
