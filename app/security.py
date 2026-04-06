import os
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException

JWT_SECRET = os.environ.get("JWT_SECRET", "changeme-use-strong-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def create_jwt(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
