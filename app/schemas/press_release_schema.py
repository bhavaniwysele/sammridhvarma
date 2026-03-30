from pydantic import BaseModel

class PressReleaseOut(BaseModel):
    id: int
    code: str
    title: str
    description: str
    date: str
    file_urls: str
    file_sizes: str

    class Config:
        orm_mode = True