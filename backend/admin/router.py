import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import User, Role
from backend.schemas import UserOut, InviteResponse
from backend.deps import get_current_user
from backend.auth.utils import create_invite_token
from backend.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_owner(user: User):
    if user.role != Role.owner:
        raise HTTPException(status_code=403, detail="Owner role required")


@router.get("/users", response_model=list[UserOut])
async def list_users(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _require_owner(user)
    result = await db.execute(select(User).where(User.organization_id == user.organization_id))
    return result.scalars().all()


@router.post("/users/invite", response_model=InviteResponse)
async def invite_user(user: User = Depends(get_current_user)):
    _require_owner(user)
    token = create_invite_token(str(user.organization_id))
    return InviteResponse(invite_url=f"{settings.dashboard_url}/register?invite={token}")


@router.delete("/users/{user_id}", status_code=204)
async def remove_user(user_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _require_owner(user)
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found in your org")
    target = await db.get(User, uid)
    if not target or str(target.organization_id) != str(user.organization_id):
        raise HTTPException(status_code=404, detail="User not found in your org")
    if str(target.id) == str(user.id):
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    await db.delete(target)
    await db.commit()
