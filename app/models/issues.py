from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from app.database import Base
from datetime import datetime

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    mobile_number = Column(String)
    email = Column(String)
    location = Column(String)
    category = Column(String)
    description = Column(Text)
    image_url = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)