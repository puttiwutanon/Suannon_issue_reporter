import os
import uuid
import boto3
from fastapi import HTTPException
from .config import logger

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        raise HTTPException(
            status_code=500,
            detail="R2 is not configured (missing R2_*/CLOUDFLARE_ACCOUNT_ID env vars)",
        )

    _client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    return _client


def upload_image(file_obj, folder: str = "school_issues") -> str:
    """Uploads a file-like object to R2 and returns its public URL."""
    bucket = os.getenv("R2_BUCKET_NAME")
    public_base = os.getenv("R2_PUBLIC_BASE_URL")  # e.g. https://img.skn.ac.th
    if not bucket or not public_base:
        raise HTTPException(
            status_code=500,
            detail="R2 is not configured (missing R2_BUCKET_NAME/R2_PUBLIC_BASE_URL)",
        )

    key = f"{folder}/{uuid.uuid4().hex}.jpg"
    client = _get_client()

    try:
        file_obj.seek(0)
        client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
    except Exception as e:
        logger.error(f"❌ R2 upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload image")

    return f"{public_base.rstrip('/')}/{key}"