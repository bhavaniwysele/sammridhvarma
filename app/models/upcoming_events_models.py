from sqlalchemy import Column, Integer, String, Date, Time, Text,ForeignKey
from app.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    event_date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    location = Column(String)
    image_url = Column(Text)

class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    full_name = Column(String)
    phone = Column(String)
    email = Column(String)
    city = Column(String)
    source = Column(String)
    other_source = Column(Text)