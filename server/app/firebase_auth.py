import os
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Header, HTTPException
from fastapi.concurrency import run_in_threadpool

if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred)

async def require_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing admin token")
    token = authorization.split(" ", 1)[1]
    try:
        return await run_in_threadpool(firebase_auth.verify_id_token, token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")