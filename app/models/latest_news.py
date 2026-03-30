from sqlalchemy import Column, Integer, String, Date, Text
from app.database import Base

class LatestNews(Base):
    __tablename__ = "latestnews"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    maintitle = Column(String(255), nullable=False)
    subtitle = Column(String(255))
    description = Column(Text)
    mainimageurl = Column(Text)
    additionalimageurl = Column(Text)
    deleted_images = Column(Text, default="")