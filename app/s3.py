import os
import uuid
from fastapi import HTTPException


def get_s3_client():
    import boto3
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "ap-south-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )


def upload_to_s3(file, filename: str = None) -> str:
    bucket = os.environ.get("AWS_S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "ap-south-1")
    folder = os.environ.get("AWS_FOLDER_NAME", "mla")

    if not bucket:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")

    try:
        s3 = get_s3_client()
        ext = os.path.splitext(file.filename)[-1]
        unique_name = filename or f"{uuid.uuid4()}{ext}"
        key = f"{folder}/{unique_name}"

        s3.upload_fileobj(
            file.file,
            bucket,
            key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")


def delete_from_s3(url: str):
    bucket = os.environ.get("AWS_S3_BUCKET_NAME")
    if not bucket or not url:
        return
    try:
        s3 = get_s3_client()
        key = url.split(".amazonaws.com/")[-1]
        s3.delete_object(Bucket=bucket, Key=key)
    except Exception:
        pass
