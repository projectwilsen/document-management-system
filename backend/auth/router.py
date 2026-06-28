from calendar import monthrange
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
from backend.database import get_db
from backend.models import Organization, User, Subscription, Plan, Role
from backend.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from backend.auth.utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, create_invite_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _current_month_range() -> tuple[date, date]:
    today = date.today()
    _, last_day = monthrange(today.year, today.month)
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, invite: str | None = None, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if invite:
        try:
            payload = decode_token(invite)
            if payload.get("type") != "invite":
                raise ValueError
            org_id = payload["org_id"]
        except (JWTError, ValueError, KeyError):
            raise HTTPException(status_code=400, detail="Invalid or expired invite link")

        user = User(organization_id=org_id, email=body.email, password_hash=hash_password(body.password), role=Role.member)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not body.name:
            raise HTTPException(status_code=422, detail="name is required when registering without invite")

        org = Organization(name=body.name)
        db.add(org)
        await db.flush()

        user = User(organization_id=org.id, email=body.email, password_hash=hash_password(body.password), role=Role.owner)
        db.add(user)
        await db.flush()

        period_start, period_end = _current_month_range()
        db.add(Subscription(organization_id=org.id, plan=Plan.free, doc_limit=50, period_start=period_start, period_end=period_end))
        await db.commit()
        await db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    import uuid
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
        user_id = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    try:
        user = await db.get(User, uuid.UUID(user_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))
