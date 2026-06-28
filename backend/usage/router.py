from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import User, Subscription, UsageLog
from backend.schemas import QuotaResponse, ReportRequest
from backend.deps import get_current_user

router = APIRouter(prefix="/usage", tags=["usage"])


async def _get_sub_and_used(db: AsyncSession, org_id) -> tuple:
    sub = (await db.execute(select(Subscription).where(Subscription.organization_id == org_id))).scalar_one()
    used = (await db.execute(
        select(func.coalesce(func.sum(UsageLog.files_processed), 0))
        .where(UsageLog.organization_id == org_id,
               func.date(UsageLog.synced_at) >= sub.period_start,
               func.date(UsageLog.synced_at) <= sub.period_end)
    )).scalar()
    return sub, used


def _to_quota(sub, used: int) -> QuotaResponse:
    remaining = None if sub.doc_limit is None else max(0, sub.doc_limit - used)
    return QuotaResponse(remaining=remaining, limit=sub.doc_limit, used=used)


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub, used = await _get_sub_and_used(db, user.organization_id)
    return _to_quota(sub, used)


@router.post("/report", response_model=QuotaResponse)
async def report_usage(body: ReportRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub, used = await _get_sub_and_used(db, user.organization_id)
    if sub.doc_limit is not None and used >= sub.doc_limit:
        raise HTTPException(status_code=402, detail="Quota exceeded")
    db.add(UsageLog(organization_id=user.organization_id, user_id=user.id, files_processed=body.files_processed))
    await db.commit()
    return _to_quota(sub, used + body.files_processed)
