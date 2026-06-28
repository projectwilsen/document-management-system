import uuid
import enum
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Enum as SAEnum, ForeignKey, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Plan(str, enum.Enum):
    free = "free"
    starter = "starter"
    pro = "pro"


class Role(str, enum.Enum):
    owner = "owner"
    member = "member"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="organization")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False), default=Role.owner)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="users")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    plan: Mapped[Plan] = mapped_column(SAEnum(Plan, native_enum=False), default=Plan.free)
    doc_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)

    organization: Mapped["Organization"] = relationship(back_populates="subscriptions")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    files_processed: Mapped[int] = mapped_column(Integer)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="usage_logs")
    user: Mapped["User"] = relationship(back_populates="usage_logs")
