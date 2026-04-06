import os
from fastapi import Header, HTTPException

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
VALID_AUDIENCES = [
    GOOGLE_CLIENT_ID,
    "407408718192.apps.googleusercontent.com",  # OAuth Playground for testing
    "339540911772-g0eifsil85vncrh3rruv6ahurau32nmh.apps.googleusercontent.com"  # frontend client ID
]


def verify_google_header(x_google_token: str = Header(..., description="Google ID token")):
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    for audience in VALID_AUDIENCES:
        try:
            idinfo = id_token.verify_oauth2_token(
                x_google_token,
                google_requests.Request(),
                audience
            )
            return {
                "email": idinfo["email"],
                "name": idinfo.get("name", ""),
                "google_id": idinfo["sub"]
            }
        except Exception:
            continue

    raise HTTPException(status_code=401, detail="Invalid or expired Google token")
