import os
import uuid
import boto3
from fastapi import HTTPException, UploadFile
from urllib.parse import urlparse, unquote

# ==============================
# CONFIG
# ==============================
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")
AWS_FOLDER_NAME = os.environ.get("AWS_FOLDER_NAME", "mla")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# ==============================
# S3 CLIENT
# ==============================
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


# ==============================
# VALIDATION
# ==============================
def validate_file(file: UploadFile):
    if "." not in file.filename:
        raise HTTPException(status_code=400, detail="Invalid file name")

    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid MIME type")

    # file size check
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")


# ==============================
# UPLOAD FILE → RETURNS KEY
# ==============================
def upload_to_s3(file: UploadFile) -> str:
    if not AWS_S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="Bucket not configured")

    validate_file(file)

    try:
        s3 = get_s3_client()

        ext = file.filename.rsplit(".", 1)[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{ext}"

        key = f"{AWS_FOLDER_NAME}/{unique_filename}"

        s3.upload_fileobj(
            file.file,
            AWS_S3_BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": file.content_type
            }
        )

        return key  # ✅ store this in DB

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ==============================
# GENERATE PRE-SIGNED URL
# ==============================
def generate_presigned_url(file_key: str, expires: int = 3600) -> str:
    if not file_key:
        return None

    try:
        s3 = get_s3_client()

        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": AWS_S3_BUCKET_NAME,
                "Key": file_key
            },
            ExpiresIn=expires
        )

        return url

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL generation failed: {str(e)}")


# ==============================
# DELETE FILE
# ==============================
def delete_from_s3(file_key: str):
    if not file_key:
        return

    try:
        s3 = get_s3_client()

        s3.delete_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=file_key
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ==============================
# EXTRACT KEY FROM URL (OPTIONAL)
# ==============================
def extract_s3_key(file_ref: str):
    if not file_ref:
        return None

    if not file_ref.startswith(("http://", "https://")):
        return file_ref

    parsed = urlparse(file_ref)
    path_key = unquote(parsed.path.lstrip("/"))

    if not path_key:
        return None

    if path_key.startswith(f"{AWS_S3_BUCKET_NAME}/"):
        return path_key[len(AWS_S3_BUCKET_NAME) + 1:]

    return path_key