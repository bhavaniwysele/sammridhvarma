from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.press_release import PressRelease
from fastapi.responses import FileResponse
from typing import Optional, Union,List, Any
import os
import shutil
import uuid
from datetime import datetime
import zipfile

router = APIRouter(prefix="/press-release", tags=["Press Release"])

UPLOAD_DIR = "uploads/press_release"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 🔥 AUTO CODE GENERATION
def generate_code(db: Session):
    year = datetime.now().year
    last = db.query(PressRelease).order_by(PressRelease.id.desc()).first()

    if not last:
        return f"PR-{year}-001"

    last_num = int(last.code.split("-")[-1])
    return f"PR-{year}-{str(last_num + 1).zfill(3)}"


# 🚀 CREATE (UPLOAD)
@router.post("/")
async def create_press_release(
    title: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    try:
        code = generate_code(db)

        file_urls = []
        file_sizes = []

        for file in files:
            # ✅ UNIQUE FILE NAME
            unique_name = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_urls.append(unique_name)  # store only filename

            # ✅ FILE SIZE
            size = os.path.getsize(file_path) / 1024
            if size > 1024:
                size = f"{round(size/1024, 1)} MB"
            else:
                size = f"{round(size, 1)} KB"

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 🚀 GET WITH PAGINATION
@router.get("/")
def get_press_releases(
    page: int = 1,
    limit: int = 3,
    db: Session = Depends(get_db)
):
    skip = (page - 1) * limit

    query = db.query(PressRelease)
    total = query.count()

    data = (
        query.order_by(PressRelease.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

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


# 🚀 DOWNLOAD (SECURE)

@router.get("/download-all/{id}")
def download_all_files(id: int, db: Session = Depends(get_db)):
    item = db.query(PressRelease).filter(PressRelease.id == id).first()

    if not item or not item.file_urls:
        raise HTTPException(status_code=404, detail="No files found")

    files = item.file_urls.split(",")

    # 🔥 zip file name
    zip_filename = f"press_release_{id}.zip"
    zip_path = os.path.join(UPLOAD_DIR, zip_filename)

    # 🔥 create zip
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file)

            if os.path.exists(file_path):
                zipf.write(file_path, arcname=file)

    return FileResponse(zip_path, filename=zip_filename)


# UPDATE
def clean_value(value):
    return None if value in [None, "", "string"] else value


@router.put("/{id}")
async def update_press_release(
    id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(default=None),  # ✅ optional clean
    db: Session = Depends(get_db)
):
    item = db.query(PressRelease).filter(PressRelease.id == id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    # 🔥 Clean values
    title = clean_value(title)
    description = clean_value(description)
    date = clean_value(date)

    if title is not None:
        item.title = title

    if description is not None:
        item.description = description

    if date is not None:
        item.date = date

    # Existing files
    existing_urls = item.file_urls.split(",") if item.file_urls else []
    existing_sizes = item.file_sizes.split(",") if item.file_sizes else []

    # 🔥 HANDLE FILES ONLY IF PROVIDED
    if files:
        for file in files:
            if not file or not file.filename:
                continue

            unique_name = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            existing_urls.append(unique_name)

            size_kb = os.path.getsize(file_path) / 1024
            size = f"{size_kb/1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"

            existing_sizes.append(size)

    # ✅ KEEP OLD FILES IF NO NEW FILES
    item.file_urls = ",".join(existing_urls)
    item.file_sizes = ",".join(existing_sizes)

    db.commit()
    db.refresh(item)

    return {
        "message": "Updated successfully",
        "data": item
    }
# ❌ DELETE FULL
@router.delete("/{id}")
def delete_press_release(id: int, db: Session = Depends(get_db)):
    item = db.query(PressRelease).filter(PressRelease.id == id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    if item.file_urls:
        for filename in item.file_urls.split(","):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(file_path):
                os.remove(file_path)

    db.delete(item)
    db.commit()

    return {"message": "Deleted successfully"}


# 🧹 DELETE SINGLE FILE
@router.delete("/file")
def delete_single_file(
    id: int,
    filename: str,
    db: Session = Depends(get_db)
):
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

    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    item.file_urls = ",".join(urls)
    item.file_sizes = ",".join(sizes)

    db.commit()

    return {"message": "File deleted successfully"}