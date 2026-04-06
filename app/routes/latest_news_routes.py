import os, json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from dateutil import parser
from app.database import get_db
from app.models.latest_news import LatestNews
from app.s3 import upload_to_s3, delete_from_s3, generate_presigned_url

router = APIRouter(prefix="/latest-news", tags=["Latest News"])


def parse_images(raw: str) -> List[str]:
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("{") or raw.startswith("["):
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return []
    return [img for img in raw.split(",") if img]


def news_with_urls(news):
    return {
        "id": news.id,
        "date": news.date,
        "maintitle": news.maintitle,
        "subtitle": news.subtitle,
        "description": news.description,
        "mainimageurl": generate_presigned_url(news.mainimageurl),
        "additionalimageurl": [generate_presigned_url(k) for k in parse_images(news.additionalimageurl)]
    }


# CREATE
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
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format")

    main_image_url = upload_to_s3(main_image)
    additional_urls = [upload_to_s3(img) for img in additional_images if img.filename]

    news = LatestNews(
        date=parsed_date,
        maintitle=maintitle,
        subtitle=subtitle,
        description=description,
        mainimageurl=main_image_url,
        additionalimageurl=",".join(additional_urls)
    )

    db.add(news)
    db.commit()
    db.refresh(news)
    return news


# READ ALL
@router.get("/")
def get_latest_news(db: Session = Depends(get_db)):
    news_list = db.query(LatestNews).order_by(LatestNews.id.desc()).limit(4).all()
    return [news_with_urls(n) for n in news_list]


# READ ONE
@router.get("/{id}")
def get_news(id: int, db: Session = Depends(get_db)):
    news = db.query(LatestNews).filter(LatestNews.id == id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news_with_urls(news)


# UPDATE
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

    def is_valid(v):
        return v and v.strip() != "" and v != "string"

    if is_valid(date):
        try:
            news.date = parser.parse(date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format")

    if is_valid(maintitle):
        news.maintitle = maintitle
    if is_valid(subtitle):
        news.subtitle = subtitle
    if is_valid(description):
        news.description = description

    if main_image and main_image.filename:
        news.mainimageurl = upload_to_s3(main_image)

    existing = parse_images(news.additionalimageurl)
    new_urls = [
        upload_to_s3(img)
        for img in (additional_images or [])
        if img and img.filename
    ]
    news.additionalimageurl = ",".join(existing + new_urls)

    db.commit()
    db.refresh(news)
    return news


# DELETE SINGLE ADDITIONAL IMAGE
@router.delete("/{id}/image")
def delete_single_image(id: int, image_url: str, db: Session = Depends(get_db)):
    news = db.query(LatestNews).filter(LatestNews.id == id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    images = parse_images(news.additionalimageurl)
    if image_url not in images:
        raise HTTPException(status_code=404, detail="Image not found")

    images.remove(image_url)
    news.additionalimageurl = ",".join(images)
    delete_from_s3(image_url)

    db.commit()
    return {"message": "Image deleted successfully"}


# DELETE
@router.delete("/{id}")
def delete_news(id: int, db: Session = Depends(get_db)):
    news = db.query(LatestNews).filter(LatestNews.id == id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    for img in parse_images(news.additionalimageurl):
        delete_from_s3(img)
    delete_from_s3(news.mainimageurl)

    db.delete(news)
    db.commit()
    return {"message": "Deleted successfully"}
