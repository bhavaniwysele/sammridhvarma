from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.issues import Issue
import shutil, os, re

router = APIRouter(prefix="/issues", tags=["issues"])

UPLOAD_FOLDER = os.environ.get("UPLOAD_DIR", "/tmp/uploads")

@router.post("/submit-issue")
def submit_issue(
    full_name: str = Form(...),
    mobile_number: str = Form(...),
    email: str = Form(...),
    location: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not mobile_number.isdigit() or len(mobile_number) != 10:
        raise HTTPException(status_code=422, detail="Phone number must be exactly 10 digits")

    if email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email):
        raise HTTPException(status_code=422, detail="Invalid email address")

    image_url = None

    # 📸 Save Image
    if image:
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        file_path = os.path.join(UPLOAD_FOLDER, image.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        image_url = file_path

    # 💾 Save to DB
    new_issue = Issue(
        full_name=full_name,
        mobile_number=mobile_number,
        email=email,
        location=location,
        category=category,
        description=description,
        image_url=image_url
    )

    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)

    return {
        "message": "Issue submitted successfully",
        "id": new_issue.id
    }