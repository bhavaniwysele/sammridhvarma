from sqlalchemy import Column, Integer, String, Date, Text
from app.database import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    mobile_number = Column(String)
    email = Column(String)
    district = Column(String)
    village = Column(String)
    constituency = Column(String)
    preferred_date = Column(Date)
    time_slot = Column(String)
    issue_category = Column(String)
    subject = Column(String)
    description = Column(Text)
    document = Column(String)
    status = Column(String, default="pending")