from pydantic import BaseModel
from datetime import date, time


class RegistrationCreate(BaseModel):
    event_id: int
    full_name: str
    phone: str
    email: str
    city: str
    source: str
    other_source: str | None = None

class EventCreate(BaseModel):
    title: str
    description: str
    event_date: date
    start_time: time
    end_time: time
    location: str
    image_url: str