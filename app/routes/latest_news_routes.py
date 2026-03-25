import os
from datetime import datetime
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from dateutil import parser
from app.database import get_db
from app.models.latest_news import LatestNews

router = APIRouter(prefix="/latest-news", tags=["Latest News"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 📁 Save file
def save_file(file: UploadFile):
    file_name = f"{datetime.now().timestamp()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return file_path


# ✅ CREATE (with images)
@router.post("/")
def create_news(
    date: str = Form(...),
    maintitle: str = Form(...),
    subtitle: str = Form(None),
    description: str = Form(None),

    main_image: UploadFile = File(...),
    additional_images: List[UploadFile] = File([]),

    db: Session = Depends(get_db)
):
    try:
        parsed_date = parser.parse(date).date()
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")

    main_image_path = save_file(main_image)
    additional_paths = [save_file(img) for img in additional_images]

    news = LatestNews(
        date=parsed_date,
        maintitle=maintitle,
        subtitle=subtitle,
        description=description,
        mainimageurl=main_image_path,
        additionalimageurl=additional_paths
    )

    db.add(news)
    db.commit()
    db.refresh(news)

    return news


# ✅ READ ALL (limit 4)
@router.get("/")
def get_latest_news(db: Session = Depends(get_db)):
    return db.query(LatestNews).order_by(LatestNews.id.desc()).limit(4).all()


# ✅ READ ONE
@router.get("/{id}")
def get_news(id: int, db: Session = Depends(get_db)):
    news = db.query(LatestNews).filter(LatestNews.id == id).first()

    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    return news


from typing import Optional, List
from fastapi import UploadFile, File, Form

@router.patch("/{id}")
def update_news(
    id: int,

    date: Optional[str] = Form(None),
    maintitle: Optional[str] = Form(None),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),

    main_image: Optional[UploadFile] = File(None),
    additional_images: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    news = db.query(LatestNews).filter(LatestNews.id == id).first()

    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    # 🔥 TEXT FIELDS
    if date and date.strip() != "" and date != "string":
        try:
            news.date = parser.parse(date).date()
        except:
            raise HTTPException(status_code=400, detail="Invalid date format")

    if maintitle and maintitle.strip() != "" and maintitle != "string":
        news.maintitle = maintitle

    if subtitle and subtitle.strip() != "" and subtitle != "string":
        news.subtitle = subtitle

    if description and description.strip() != "" and description != "string":
        news.description = description

    # 🔥 MAIN IMAGE
    if main_image and hasattr(main_image, "filename") and main_image.filename:
        news.mainimageurl = save_file(main_image)

    # 🔥 ADDITIONAL IMAGES (FIXED PROPERLY)

    # Step 1: CLEAN existing images properly
    existing = []

    if news.additionalimageurl:
        raw = news.additionalimageurl.strip()

        # handle bad old formats
        if raw.startswith("{") or raw.startswith("["):
            try:
                import json
                existing = json.loads(raw.replace("'", '"'))
            except:
                existing = []
        else:
            existing = [img for img in raw.split(",") if img]

    # Step 2: ADD new uploads (not replace)
    new_images = []
    if additional_images:
        new_images = [
            save_file(img)
            for img in additional_images
            if img and hasattr(img, "filename") and img.filename
        ]

    # 🔥 Step 3: MERGE (THIS IS KEY)
    final_images = existing.copy()   # keep old
    final_images.extend(new_images)  # add new

    # Step 4: SAVE BACK
    news.additionalimageurl = ",".join(final_images)
    db.commit()
    db.refresh(news)

    return news


# ✅ DELETE
@router.delete("/{id}")
def delete_news(id: int, db: Session = Depends(get_db)):
    news = db.query(LatestNews).filter(LatestNews.id == id).first()

    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    db.delete(news)
    db.commit()

    return {"message": "Deleted successfully"}