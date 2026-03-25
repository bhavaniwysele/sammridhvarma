from pydantic import BaseModel
from datetime import date
from typing import List

class LatestNewsBase(BaseModel):
    date: date
    maintitle: str
    subtitle: str | None = None
    description: str | None = None


class LatestNewsResponse(LatestNewsBase):
    id: int
    mainimageurl: str | None
    additionalimageurl: List[str] | None

    class Config:
        from_attributes = True