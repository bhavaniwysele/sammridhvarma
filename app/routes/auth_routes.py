import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
JWT_SECRET = os.environ.get("JWT_SECRET", "changeme-use-strong-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def create_jwt(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# STEP 1: Redirect user to Google login
@router.get("/login")
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    params = (
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&access_type=offline"
    )
    return RedirectResponse(url=GOOGLE_AUTH_URL + params)


# STEP 2: Google redirects back with code
@router.get("/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    import httpx
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_response = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get token from Google")

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        userinfo = userinfo_response.json()

    email = userinfo.get("email")
    name = userinfo.get("name")
    google_id = userinfo.get("sub")

    # Save or update admin in DB
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin:
        admin = Admin(email=email, name=name, google_id=google_id)
        db.add(admin)
        db.commit()
        db.refresh(admin)
    else:
        admin.name = name
        admin.picture = picture
        db.commit()

    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Generate JWT
    token = create_jwt({"email": email, "name": name, "id": admin.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": admin.id,
            "email": email,
            "name": name
        }
    }


# GET current logged in user
@router.get("/me")
def get_me(token: str, db: Session = Depends(get_db)):
    payload = verify_jwt(token)
    admin = db.query(Admin).filter(Admin.email == payload["email"]).first()
    if not admin:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": admin.id,
        "email": admin.email,
        "name": admin.name
    }
