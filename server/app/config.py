import os
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()
ENV = os.getenv("ENVIRONMENT", "development")
limiter = Limiter(key_func=get_remote_address)

TH_TZ = timezone(timedelta(hours=7))

def now_th() -> str:
    """Current time in Thailand (UTC+7), formatted to match the
    'YYYY-MM-DD HH:MM:SS' shape SQLite's own datetime('now') produces,
    so old and new rows sort and compare the same way."""
    return datetime.now(TH_TZ).strftime("%Y-%m-%d %H:%M:%S")

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---------- CORS ----------
if ENV == "production":
    CORS_ORIGINS = [
        "https://skn-issue-reporter-client-692173962169.asia-southeast1.run.app",
        "https://liff.line.me",
    ]
else:
    CORS_ORIGINS = [
        "https://*.trycloudflare.com",
        "https://*.ngrok-free.dev",
        "https://liff.line.me",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

# ✅ Also allow regex for wildcard matching
if ENV == "production":
    CORS_ORIGIN_REGEX = None
else:
    CORS_ORIGIN_REGEX = r"https://.*\.(trycloudflare\.com|ngrok-free\.dev)"