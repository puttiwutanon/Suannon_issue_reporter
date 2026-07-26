import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
import cloudinary.uploader
import psycopg2
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    QuickReply, QuickReplyButton, URIAction
)

load_dotenv()

app = FastAPI(title="School Issue Reporter API")

# Enable CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Database Connection Helper
def get_db_connection():
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    except Exception as e:
        print("Database connection error:", e)
        raise HTTPException(status_code=500, detail="Database connection failure")

@app.post("/api/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(
    lineUserId: str = Form(...),
    reporterName: Optional[str] = Form(None),
    category: str = Form(...),
    description: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    image_url = None

    # 1. Upload file object directly to Cloudinary if an image was attached
    if image:
        try:
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="school_issues"
            )
            image_url = upload_result.get("secure_url")
        except Exception as e:
            print("Cloudinary error:", e)
            raise HTTPException(status_code=500, detail="Failed to upload image")

    # 2. Insert record into PostgreSQL
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO issues (line_user_id, reporter_name, category, description, image_url, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, line_user_id, reporter_name, category, description, image_url, latitude, longitude, status, created_at;
        """
        values = (lineUserId, reporterName, category, description, image_url, latitude, longitude)

        cursor.execute(query, values)
        new_row = cursor.fetchone()
        conn.commit()
        
        cursor.close()
        conn.close()

        return {
            "success": True,
            "issue": {
                "id": new_row[0],
                "lineUserId": new_row[1],
                "reporterName": new_row[2],
                "category": new_row[3],
                "description": new_row[4],
                "imageUrl": new_row[5],
                "latitude": float(new_row[6]) if new_row[6] else None,
                "longitude": float(new_row[7]) if new_row[7] else None,
                "status": new_row[8],
                "createdAt": str(new_row[9])
            }
        }
    except Exception as e:
        print("Database error:", e)
        raise HTTPException(status_code=500, detail=f"Database insertion error: {str(e)}")


line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.post("/webhook")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()

    # 1. New User Tutorial
    if user_text == "ผู้ใช้ใหม่":
        tutorial_text = (
            "📌 **วิธีใช้งานระบบแจ้งปัญหา**\n\n"
            "1. กดปุ่ม 'แจ้งเรื่องใหม่' ที่เมนูด้านล่าง\n"
            "2. กรอกรายละเอียดปัญหาที่คุณพบเจอ\n"
            "3. แนบรูปภาพสถานที่เกิดเหตุ\n"
            "4. กดยืนยัน ข้อมูลจะถูกส่งไปยังสภานักเรียนทันที!\n\n"
            "ขอบคุณที่ช่วยทำให้โรงเรียนของเราดีขึ้นครับ 🏫✨"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=tutorial_text))

    # 2. View Reports (Quick Reply Menu opens LIFF)
    elif user_text == "ดูเรื่องแจ้ง":
        
        # Replace the URLs below with your actual LIFF URL.
        # You can use URL parameters (like ?view=mine) so your React app 
        # knows which data to fetch when the page loads!
        
        quick_reply_menu = QuickReply(
            items=[
                QuickReplyButton(action=URIAction(
                    label="เรื่องแจ้งของฉัน", 
                    uri="https://liff.line.me/2010847048-z4172Q47"
                )),
                QuickReplyButton(action=URIAction(
                    label="เรื่องแจ้งจากผู้อื่น", 
                    uri="https://liff.line.me/2010847048-z4172Q47"
                ))
            ]
        )
        msg = TextSendMessage(
            text="คุณต้องการดูเรื่องแจ้งประเภทใดครับ?",
            quick_reply=quick_reply_menu
        )
        line_bot_api.reply_message(event.reply_token, msg)

    # 3. reports problems (Quick Reply Menu opens LIFF)
    elif user_text == "แจ้งเรื่องใหม่":
        
        # Replace the URLs below with your actual LIFF URL.
        # You can use URL parameters (like ?view=mine) so your React app 
        # knows which data to fetch when the page loads!
        
        quick_reply_menu = QuickReply(
            items=[
                QuickReplyButton(action=URIAction(
                    label="แจ้งปัญหาเพื่อแก้ไขด่วน", 
                    uri="https://liff.line.me/2010847048-WMKaotVe"
                )),
                QuickReplyButton(action=URIAction(
                    label="เสนอแนะเพื่อปรับปรุงรร.", 
                    uri="https://liff.line.me/2010847048-WMKaotVe"
                ))
            ]
        )
        msg = TextSendMessage(
            text="คุณต้องการแจ้งปัญหาเรื่องอะไรดีครับ?",
            quick_reply=quick_reply_menu
        )
        line_bot_api.reply_message(event.reply_token, msg)