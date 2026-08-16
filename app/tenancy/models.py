"""Organization ownership and bounded membership roles."""

import uuid
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.database import Base


class MembershipRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


def new_tenant_id() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=new_tenant_id)
    name = Column(String(160), nullable=False)
    slug = Column(String(80), nullable=False, unique=True)
    ownership_state = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "ownership_state IN ('active', 'legacy_unclaimed')",
            name="ck_organizations_ownership_state",
        ),
    )


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(String(36), primary_key=True, default=new_tenant_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    role = Column(String(16), nullable=False, default=MembershipRole.MEMBER.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'admin', 'member')", name="ck_memberships_role"
        ),
        UniqueConstraint(
            "user_id", "organization_id", name="uq_memberships_user_organization"
        ),
    )
