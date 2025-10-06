from datetime import datetime
from pydantic import BaseModel


class TokenBase(BaseModel):
    address: str
    name: str
    label: str | None = None
    description: str | None = None
    image: str | None = None
    ordering: int | None = 0
    tier: int | None = 1
    description_en: str | None = None


class TokenCreate(TokenBase):
    created_by: str | None = None


class TokenUpdate(BaseModel):
    name: str | None = None
    label: str | None = None
    description: str | None = None
    image: str | None = None
    ordering: int | None = None
    tier: int | None = None
    description_en: str | None = None
    archived_at: datetime | None = None


class TokenResponse(TokenBase):
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    archived_at: datetime | None

    class Config:
        from_attributes = True
