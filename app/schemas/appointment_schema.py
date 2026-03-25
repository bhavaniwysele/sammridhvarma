from pydantic import BaseModel, field_validator
from datetime import date

class AppointmentCreate(BaseModel):
    full_name: str
    mobile_number: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v
    email: str | None = None
    district: str
    village: str

    constituency: str
    preferred_date: date
    time_slot: str
    issue_category: str

    subject: str
    description: str

class AppointmentResponse(BaseModel):
    id: int
    full_name: str
    mobile_number: str
    status: str

    class Config:
        orm_mode = True