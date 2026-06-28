import { NextRequest, NextResponse } from "next/server"
import { and, eq } from "drizzle-orm"
import { db } from "@/lib/db/client"
import { users } from "@/lib/db/schema"
import { requireAuth } from "@/lib/auth-guard"

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const auth = await requireAuth(req)
  if (auth instanceof NextResponse) return auth

  const [currentUser] = await db.select().from(users)
    .where(eq(users.id, auth.userId)).limit(1)
  if (!currentUser) return NextResponse.json({ detail: "Not found" }, { status: 404 })
  if (currentUser.role !== "owner") {
    return NextResponse.json({ detail: "Owner role required" }, { status: 403 })
  }

  if (params.id === auth.userId) {
    return NextResponse.json({ detail: "Cannot remove yourself" }, { status: 400 })
  }

  const [target] = await db.select().from(users).where(
    and(
      eq(users.id, params.id),
      eq(users.organizationId, currentUser.organizationId)
    )
  ).limit(1)

  if (!target) {
    return NextResponse.json({ detail: "User not found in your org" }, { status: 404 })
  }

  await db.delete(users).where(eq(users.id, params.id))
  return new NextResponse(null, { status: 204 })
}
