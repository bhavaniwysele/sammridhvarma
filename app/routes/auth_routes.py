import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.admin import Admin
from app.security import create_jwt, verify_jwt

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")


class GoogleTokenRequest(BaseModel):
    token: str


def verify_google_token(token: str) -> dict:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    try:
        return id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired Google token")


# POST /auth/google — verify Google ID token, return JWT + user details
@router.post("/google")
def google_auth(body: GoogleTokenRequest, db: Session = Depends(get_db)):
    idinfo = verify_google_token(body.token)

    email = idinfo.get("email")
    name = idinfo.get("name", "")
    google_id = idinfo.get("sub")

    if not email:
        raise HTTPException(status_code=400, detail="Email not found in token")

    # get or create user
    user = db.query(Admin).filter(Admin.email == email).first()
    if not user:
        user = Admin(email=email, name=name, google_id=google_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_jwt({"id": user.id, "email": user.email, "name": user.name})

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }


# GET /auth/me — get current user from JWT
@router.get("/me")
def get_me(token: str, db: Session = Depends(get_db)):
    payload = verify_jwt(token)
    user = db.query(Admin).filter(Admin.email == payload["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name
    }
