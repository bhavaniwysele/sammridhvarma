from pydantic import BaseModel

class IssueCreate(BaseModel):
    full_name: str
    mobile_number: str
    email: str
    location: str
    category: str
    description: str