import os
import logging
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
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage,  
    QuickReply, QuickReplyButton, URIAction
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

# ---------- Setup Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
        logger.info("🔄 Connecting to database...")
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        logger.info("✅ Database connected successfully")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failure")


# ---------- GET /api/issues ----------
@app.get("/api/issues")
async def get_issues(
    user_id: Optional[str] = Query(None, description="Filter by LINE user ID")
):
    logger.info(f"📥 GET /api/issues - user_id: {user_id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if user_id:
            logger.info(f"🔍 Fetching issues for user: {user_id}")
            query = "SELECT * FROM issues WHERE line_user_id = %s ORDER BY created_at DESC"
            cursor.execute(query, (user_id,))
        else:
            logger.info("📋 Fetching all issues")
            query = "SELECT * FROM issues ORDER BY created_at DESC"
            cursor.execute(query)

        rows = cursor.fetchall()
        logger.info(f"✅ Found {len(rows)} issues")
        cursor.close()
        conn.close()

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
                "issueType": row[13] if len(row) > 13 else None,
                "fixImageUrl": row[14] if len(row) > 14 else None,
                "resolvedAt": str(row[15]) if len(row) > 15 and row[15] else None,
            })
        
        logger.info(f"📤 Returning {len(issues)} issues")
        return {"success": True, "issues": issues}
    except Exception as e:
        logger.error(f"❌ GET error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST /api/issues/{issue_id}/resolve ----------
@app.post("/api/issues/{issue_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_issue(
    issue_id: int,
    fix_image: UploadFile = File(...),
):
    logger.info(f"🔧 Resolving issue ID: {issue_id}")
    
    # Upload fix image to Cloudinary
    try:
        logger.info(f"📤 Uploading fix image to Cloudinary: {fix_image.filename}")
        upload_result = cloudinary.uploader.upload(
            fix_image.file,
            folder="school_issues/fixed"
        )
        fix_image_url = upload_result.get("secure_url")
        logger.info(f"✅ Fix image uploaded: {fix_image_url}")
    except Exception as e:
        logger.error(f"❌ Cloudinary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload fix image")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update issue: set status = 'resolved', fix_image_url, resolved_at
        query = """
            UPDATE issues 
            SET status = 'resolved', 
                fix_image_url = %s, 
                resolved_at = NOW()
            WHERE id = %s
            RETURNING line_user_id, reporter_name, category, description;
        """
        cursor.execute(query, (fix_image_url, issue_id))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        line_user_id, reporter_name, category, description = result
        conn.commit()
        cursor.close()
        conn.close()

        # -------- Send LINE notification with image --------
        try:
            line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
            
            # Text message
            text_msg = TextSendMessage(
                text=(
                    f"✅ เรื่องแจ้งของคุณได้รับการแก้ไขแล้ว!\n\n"
                    f"📋 ประเภท: {category}\n"
                    f"📝 รายละเอียด: {description}\n\n"
                    f"ขอบคุณที่ช่วยทำให้โรงเรียนของเราดีขึ้นครับ 🙏"
                )
            )
            
            # Image message – send the fix photo directly
            image_msg = ImageSendMessage(
                original_content_url=fix_image_url,
                preview_image_url=fix_image_url
            )
            
            # Send both as a multi-message (text + image)
            line_bot_api.push_message(
                to=line_user_id,
                messages=[text_msg, image_msg]
            )
            logger.info(f"✅ LINE notification with image sent to {line_user_id}")
        except Exception as e:
            logger.error(f"❌ LINE push error: {e}", exc_info=True)

        return {
            "success": True,
            "message": "Issue resolved and notification sent",
            "fixImageUrl": fix_image_url
        }
    except Exception as e:
        logger.error(f"❌ Resolve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST /api/issues ----------
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

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
    issue_type: Optional[str] = Form('urgent'),
):
    logger.info(f"📝 POST /api/issues - User: {lineUserId}, Type: {issue_type}, Category: {category}")
    logger.info(f"📝 Reporter: {reporterName}, Description length: {len(description) if description else 0}")
    logger.info(f"📝 Student: {studentYear}/{studentClass}/{studentNumber}")
    
    image_url = None

    if image:
        try:
            logger.info(f"📤 Uploading image to Cloudinary: {image.filename}")
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="school_issues"
            )
            image_url = upload_result.get("secure_url")
            logger.info(f"✅ Image uploaded: {image_url}")
        except Exception as e:
            logger.error(f"❌ Cloudinary error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to upload image")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO issues 
            (line_user_id, reporter_name, category, description, image_url, 
             latitude, longitude, student_year, student_class, student_number, issue_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, line_user_id, reporter_name, category, description, 
                      image_url, latitude, longitude, status, created_at,
                      student_year, student_class, student_number, issue_type;
        """
        values = (
            lineUserId, reporterName, category, description, image_url,
            latitude, longitude, studentYear, studentClass, studentNumber,
            issue_type
        )
        
        logger.info(f"💾 Inserting issue into database...")
        cursor.execute(query, values)
        new_row = cursor.fetchone()
        conn.commit()
        logger.info(f"✅ Issue inserted with ID: {new_row[0]}")
        cursor.close()
        conn.close()

        # -------- Send LINE confirmation message --------
        try:
            if issue_type == 'suggestion':
                msg_text = "✅ ส่งข้อเสนอแนะสำเร็จแล้ว!\nขอบคุณที่ช่วยพัฒนาโรงเรียนของเรา 🙏"
            else:
                msg_text = "✅ แจ้งปัญหาสำเร็จแล้ว!\nทีมงานจะรีบดำเนินการต่อไป 🛠️"
            
            logger.info(f"📤 Sending LINE confirmation to: {lineUserId}")
            line_bot_api.push_message(
                to=lineUserId,
                messages=TextSendMessage(text=msg_text)
            )
            logger.info("✅ LINE confirmation sent")
        except Exception as e:
            logger.error(f"❌ LINE push error: {e}", exc_info=True)
            # Don't fail the request if push fails

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
                "issueType": new_row[13],
            }
        }
    except Exception as e:
        logger.error(f"❌ Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database insertion error: {str(e)}")


# ---------- LINE Bot Webhook ----------
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.post("/webhook")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    logger.info("📨 Webhook received")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
        logger.info("✅ Webhook handled successfully")
    except InvalidSignatureError:
        logger.error("❌ Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()
    user_id = event.source.user_id
    logger.info(f"💬 Message from {user_id}: {user_text}")

    if user_text == "ผู้ใช้ใหม่":
        logger.info(f"📖 Tutorial requested by {user_id}")
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
        logger.info(f"👀 View reports requested by {user_id}")
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
        logger.info(f"📝 New report requested by {user_id}")
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
    
    else:
        logger.info(f"❓ Unknown command: {user_text} from {user_id}")
        # Optional: reply with help message
        help_text = "พิมพ์ 'ผู้ใช้ใหม่' เพื่อดูวิธีการใช้งาน\nพิมพ์ 'แจ้งเรื่องใหม่' เพื่อแจ้งปัญหา\nพิมพ์ 'ดูเรื่องแจ้ง' เพื่อดูรายการที่แจ้ง"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))


def delete_old_resolved_issues():
    """ลบรายการปัญหาที่แก้ไขแล้ว (status='resolved') ที่เก่ากว่า 4 วัน"""
    logger.info("🧹 Running scheduled cleanup: deleting old resolved issues")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Delete issues where status='resolved' and resolved_at < now - 4 days
        query = """
            DELETE FROM issues 
            WHERE status = 'resolved' 
              AND resolved_at < NOW() - INTERVAL '4 days'
            RETURNING id;
        """
        cursor.execute(query)
        deleted = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
        if deleted:
            logger.info(f"🗑️ Deleted {len(deleted)} old resolved issues")
        else:
            logger.info("✅ No old resolved issues to delete")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}", exc_info=True)

# Schedule the job to run daily at 3:00 AM
scheduler = BackgroundScheduler()
scheduler.add_job(
    delete_old_resolved_issues,
    trigger=CronTrigger(hour=3, minute=0),
    id="cleanup_resolved_issues",
    replace_existing=True
)
scheduler.start()

# Shutdown scheduler on app exit
@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()