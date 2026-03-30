from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.database import Base

class PressRelease(Base):
    __tablename__ = "press_releases"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    date = Column(String, nullable=False)

    file_urls = Column(Text)   # comma separated
    file_sizes = Column(Text)  # comma separated

    created_at = Column(DateTime, default=datetime.utcnow)