from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.press_release import PressRelease
from typing import Optional, List
import uuid
from datetime import datetime
try:
    from app.s3 import upload_to_s3, delete_from_s3
except Exception as e:
    print("S3 IMPORT ERROR:", e)

    def upload_to_s3(file):
        return "dummy-url"

    def delete_from_s3(url):
        return True

router = APIRouter(prefix="/press-release", tags=["Press Release"])


def generate_code(db: Session):
    year = datetime.now().year
    last = db.query(PressRelease).order_by(PressRelease.id.desc()).first()
    if not last:
        return f"PR-{year}-001"
    last_num = int(last.code.split("-")[-1])
    return f"PR-{year}-{str(last_num + 1).zfill(3)}"


def clean_value(value):
    return None if value in [None, "", "string"] else value


# CREATE
@router.post("/")
async def create_press_release(
    title: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    code = generate_code(db)
    file_urls = []
    file_sizes = []

    for file in files:
        if not file.filename:
            continue
        url = upload_to_s3(file)
        file_urls.append(url)
        file.file.seek(0, 2)
        size_bytes = file.file.tell() / 1024
        size = f"{size_bytes/1024:.1f} MB" if size_bytes > 1024 else f"{size_bytes:.1f} KB"
        file_sizes.append(size)

    new_item = PressRelease(
        code=code,
        title=title,
        description=description,
        date=date,
        file_urls=",".join(file_urls),
        file_sizes=",".join(file_sizes)
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Created successfully", "data": new_item}


# GET WITH PAGINATION
@router.get("/")
def get_press_releases(page: int = 1, limit: int = 3, db: Session = Depends(get_db)):
    skip = (page - 1) * limit
    query = db.query(PressRelease)
    total = query.count()
    data = query.order_by(PressRelease.id.desc()).offset(skip).limit(limit).all()
    total_pages = (total + limit - 1) // limit

    return {
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# UPDATE
@router.put("/{id}")
async def update_press_release(
    id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    item = db.query(PressRelease).filter(PressRelease.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    title = clean_value(title)
    description = clean_value(description)
    date = clean_value(date)

    if title is not None:
        item.title = title
    if description is not None:
        item.description = description
    if date is not None:
        item.date = date

    existing_urls = item.file_urls.split(",") if item.file_urls else []
    existing_sizes = item.file_sizes.split(",") if item.file_sizes else []

    real_files = [f for f in (files or []) if f and f.filename and f.filename.strip() != ""]
    for file in real_files:
        url = upload_to_s3(file)
        existing_urls.append(url)
        file.file.seek(0, 2)
        size_kb = file.file.tell() / 1024
        size = f"{size_kb/1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"
        existing_sizes.append(size)

    item.file_urls = ",".join(existing_urls)
    item.file_sizes = ",".join(existing_sizes)

    db.commit()
    db.refresh(item)
    return {"message": "Updated successfully", "data": item}


# DELETE FULL
@router.delete("/{id}")
def delete_press_release(id: int, db: Session = Depends(get_db)):
    item = db.query(PressRelease).filter(PressRelease.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    for url in (item.file_urls or "").split(","):
        delete_from_s3(url)

    db.delete(item)
    db.commit()
    return {"message": "Deleted successfully"}


# DELETE SINGLE FILE
@router.delete("/file")
def delete_single_file(id: int, filename: str, db: Session = Depends(get_db)):
    item = db.query(PressRelease).filter(PressRelease.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    urls = item.file_urls.split(",") if item.file_urls else []
    sizes = item.file_sizes.split(",") if item.file_sizes else []

    if filename not in urls:
        raise HTTPException(status_code=404, detail="File not linked")

    index = urls.index(filename)
    urls.pop(index)
    sizes.pop(index)

    delete_from_s3(filename)

    item.file_urls = ",".join(urls)
    item.file_sizes = ",".join(sizes)
    db.commit()
    return {"message": "File deleted successfully"}
