import os
import httpx
from fastapi import Header, HTTPException

async def verify_line_id_token(x_line_id_token: str = Header(None)) -> dict:
    if not x_line_id_token:
        raise HTTPException(status_code=401, detail="Missing LINE ID token")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.line.me/oauth2/v2.1/verify",
            data={"id_token": x_line_id_token, "client_id": os.getenv("LINE_LOGIN_CHANNEL_ID")}
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid LINE ID token")
    payload = resp.json()
    return {"userId": payload["sub"], "displayName": payload.get("name", "")}