"""Auth & onboarding request/response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.tenant import UserRole


class SignupRequest(BaseModel):
    """Create a new agency (tenant) and its owner user in one step."""

    agency_name: str = Field(min_length=2, max_length=120)
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    onboarding_completed: bool
    auto_followup: bool = False
    created_at: datetime


class MeResponse(BaseModel):
    user: UserOut
    tenant: TenantOut


class OnboardingUpdate(BaseModel):
    completed: bool = True
