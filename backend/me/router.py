from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import User, Subscription, UsageLog
from backend.schemas import MeResponse, QuotaResponse
from backend.deps import get_current_user

router = APIRouter(prefix="/me", tags=["me"])


async def _quota(db: AsyncSession, user: User) -> tuple:
    sub = (await db.execute(select(Subscription).where(Subscription.organization_id == user.organization_id))).scalar_one()
    used = (await db.execute(
        select(func.coalesce(func.sum(UsageLog.files_processed), 0))
        .where(UsageLog.organization_id == user.organization_id,
               func.date(UsageLog.synced_at) >= sub.period_start,
               func.date(UsageLog.synced_at) <= sub.period_end)
    )).scalar()
    remaining = None if sub.doc_limit is None else max(0, sub.doc_limit - used)
    return QuotaResponse(remaining=remaining, limit=sub.doc_limit, used=used), sub


@router.get("", response_model=MeResponse)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    quota, sub = await _quota(db, user)
    return MeResponse(id=user.id, email=user.email, role=user.role,
                      organization_id=user.organization_id, plan=sub.plan, quota=quota)
