from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class LeadCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    notes_public: Optional[str] = Field(None, max_length=1000)
    referral_code: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    status: str
    created_at: datetime
    referrer_name: Optional[str] = None
    advisor_name: Optional[str] = None

    model_config = {"from_attributes": True}


class LeadStatusUpdate(BaseModel):
    status: str


class LeadNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)
