import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Request, Header, Query
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Database helper
def get_db_connection():
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    except Exception as e:
        print("Database connection error:", e)
        raise HTTPException(status_code=500, detail="Database connection failure")


# ---------- GET /api/issues ----------
@app.get("/api/issues")
async def get_issues(
    user_id: Optional[str] = Query(None, description="Filter by LINE user ID")
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if user_id:
            query = "SELECT * FROM issues WHERE line_user_id = %s ORDER BY created_at DESC"
            cursor.execute(query, (user_id,))
        else:
            query = "SELECT * FROM issues ORDER BY created_at DESC"
            cursor.execute(query)

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert rows to dict list
        issues = []
        for row in rows:
            issues.append({
                "id": row[0],
                "lineUserId": row[1],
                "reporterName": row[2],
                "category": row[3],
                "description": row[4],
                "imageUrl": row[5],
                "latitude": float(row[6]) if row[6] else None,
                "longitude": float(row[7]) if row[7] else None,
                "status": row[8],
                "createdAt": str(row[9]),
                "studentYear": row[10] if len(row) > 10 else None,
                "studentClass": row[11] if len(row) > 11 else None,
                "studentNumber": row[12] if len(row) > 12 else None,
            })
        return {"success": True, "issues": issues}
    except Exception as e:
        print("GET error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST /api/issues (extended for student details) ----------
@app.post("/api/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(
    lineUserId: str = Form(...),
    reporterName: Optional[str] = Form(None),
    category: str = Form(...),
    description: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    studentYear: Optional[str] = Form(None),
    studentClass: Optional[str] = Form(None),
    studentNumber: Optional[str] = Form(None),
):
    image_url = None

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

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO issues 
            (line_user_id, reporter_name, category, description, image_url, 
             latitude, longitude, student_year, student_class, student_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, line_user_id, reporter_name, category, description, 
                      image_url, latitude, longitude, status, created_at,
                      student_year, student_class, student_number;
        """
        values = (
            lineUserId, reporterName, category, description, image_url,
            latitude, longitude, studentYear, studentClass, studentNumber
        )
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
                "createdAt": str(new_row[9]),
                "studentYear": new_row[10],
                "studentClass": new_row[11],
                "studentNumber": new_row[12],
            }
        }
    except Exception as e:
        print("Database error:", e)
        raise HTTPException(status_code=500, detail=f"Database insertion error: {str(e)}")


# ---------- LINE Bot Webhook ----------
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

    elif user_text == "ดูเรื่องแจ้ง":
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(
                    action=URIAction(
                        label="เรื่องแจ้งของฉัน",
                        uri="https://liff.line.me/2010847048-WMKaotVe?mode=view_mine"
                    )
                ),
                QuickReplyButton(
                    action=URIAction(
                        label="เรื่องแจ้งจากผู้อื่น",
                        uri="https://liff.line.me/2010847048-WMKaotVe?mode=view_others"
                    )
                ),
                QuickReplyButton(
                    action=URIAction(
                        label="ยกเลิก กลับไปหน้าหลัก",
                        uri="https://liff.line.me/2010847048-WMKaotVe?mode=home"
                    )
                )
            ]
        )
        msg = TextSendMessage(
            text="คุณต้องการดูเรื่องแจ้งประเภทใดครับ?",
            quick_reply=quick_reply
        )
        line_bot_api.reply_message(event.reply_token, msg)

    elif user_text == "แจ้งเรื่องใหม่":
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(
                    action=URIAction(
                        label="แจ้งปัญหาเพื่อแก้ไขด่วน",
                        uri="https://liff.line.me/2010847048-WMKaotVe?mode=form_urgent"
                    )
                ),
                QuickReplyButton(
                    action=URIAction(
                        label="เสนอแนะเพื่อปรับปรุงรร.",
                        uri="https://liff.line.me/2010847048-WMKaotVe?mode=form_suggestion"
                    )
                ),
                QuickReplyButton(
                    action=URIAction(
                        label="ยกเลิก กลับไปหน้าหลัก",
                        uri="https://liff.line.me/2010847048-WMKaotVe?mode=home"
                    )
                )
            ]
        )
        msg = TextSendMessage(
            text="คุณต้องการแจ้งปัญหาเรื่องอะไรดีครับ?",
            quick_reply=quick_reply
        )
        line_bot_api.reply_message(event.reply_token, msg)