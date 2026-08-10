import os
import logging
import cloudinary
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()
ENV = os.getenv("ENVIRONMENT", "development")
limiter = Limiter(key_func=get_remote_address)

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---------- Cloudinary ----------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# ---------- CORS ----------
if ENV == "production":
    CORS_ORIGINS = [
        "https://your-admin-dashboard-domain.com",
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