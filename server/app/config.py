import os
import logging
import cloudinary
from dotenv import load_dotenv

load_dotenv()

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
CORS_ORIGINS = [
    "https://*.trycloudflare.com",     # cloudflared frontend
    "https://*.ngrok-free.dev",        # ngrok backend (for API calls)
    "https://liff.line.me",            # LINE LIFF
    "http://localhost:5173",           # local dev
    "http://localhost:8000",           # local dev
    "*"                                # fallback (remove in production)
]
