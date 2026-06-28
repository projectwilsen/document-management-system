import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from backend.models import Plan, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None  # org name; required when no invite token


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class QuotaResponse(BaseModel):
    remaining: int | None  # None = unlimited
    limit: int | None
    used: int


class ReportRequest(BaseModel):
    files_processed: int


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    created_at: datetime
    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    organization_id: uuid.UUID
    plan: Plan
    quota: QuotaResponse


class InviteResponse(BaseModel):
    invite_url: str
