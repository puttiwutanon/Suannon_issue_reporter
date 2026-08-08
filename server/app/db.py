import os
import psycopg2
from fastapi import HTTPException
from .config import logger


def get_db_connection():
    try:
        logger.info("🔄 Connecting to database...")
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        logger.info("✅ Database connected successfully")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failure")
