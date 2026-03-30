import os
import uuid
from fastapi import HTTPException

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")
AWS_FOLDER_NAME = os.environ.get("AWS_FOLDER_NAME", "mla")


def get_s3_client():
    import boto3
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def upload_to_s3(file, filename: str = None) -> str:
    if not AWS_S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")
    try:
        from botocore.exceptions import BotoCoreError, ClientError
        s3 = get_s3_client()
        ext = os.path.splitext(file.filename)[-1]
        unique_name = filename or f"{uuid.uuid4()}{ext}"
        key = f"{AWS_FOLDER_NAME}/{unique_name}"
        s3.upload_fileobj(
            file.file,
            AWS_S3_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
        return f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")


def delete_from_s3(url: str):
    if not AWS_S3_BUCKET_NAME or not url:
        return
    try:
        s3 = get_s3_client()
        key = url.split(".amazonaws.com/")[-1]
        s3.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=key)
    except Exception:
        pass
