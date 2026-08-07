import os
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Request, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import locale

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
    allow_origins=[
        "https://*.trycloudflare.com",     # cloudflared frontend
        "https://*.ngrok-free.dev",        # ngrok backend (for API calls)
        "https://liff.line.me",            # LINE LIFF
        "http://localhost:5173",           # local dev
        "http://localhost:8000",           # local dev
        "*"                                # fallback (remove in production)
    ],
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

        try:
            line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
            
            text_msg = TextSendMessage(
                text=(
                    f"✅ เรื่องแจ้งของคุณได้รับการแก้ไขแล้ว!\n\n"
                    f"📋 ประเภท: {category}\n"
                    f"📝 รายละเอียด: {description}\n\n"
                    f"ขอบคุณที่ช่วยทำให้โรงเรียนของเราดีขึ้นครับ 🙏"
                )
            )
            
            image_msg = ImageSendMessage(
                original_content_url=fix_image_url,
                preview_image_url=fix_image_url
            )
            
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
        help_text = "พิมพ์ 'ผู้ใช้ใหม่' เพื่อดูวิธีการใช้งาน\nพิมพ์ 'แจ้งเรื่องใหม่' เพื่อแจ้งปัญหา\nพิมพ์ 'ดูเรื่องแจ้ง' เพื่อดูรายการที่แจ้ง"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))


# ---------- Auto-delete old resolved issues ----------
def delete_old_resolved_issues():
    """ลบรายการปัญหาที่แก้ไขแล้ว (status='resolved') ที่เก่ากว่า 4 วัน"""
    logger.info("🧹 Running scheduled cleanup: deleting old resolved issues")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
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


def generate_urgent_report_pdf():
    """Generate PDF report of all pending urgent issues and save to reports/ folder."""
    logger.info("📄 Generating urgent issues report...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch pending urgent issues for TODAY ONLY
        query = """
            SELECT reporter_name, description, created_at 
            FROM issues 
            WHERE issue_type = 'urgent' 
              AND status = 'pending'
              AND DATE(created_at) = CURRENT_DATE
            ORDER BY created_at ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            logger.info("ℹ️ No urgent pending issues to report for today.")
            return None

        # Create reports directory if not exists
        os.makedirs("reports", exist_ok=True)

        # File name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"reports/urgent_report_{timestamp}.pdf"
        
        # ---------- Font Loading ----------
        font_name = 'Helvetica'  # fallback
        font_registered = False
        
        # Priority 1: fonts folder (your custom font)
        font_paths = [
            "fonts/THSarabunNew.ttf",
            "fonts/THSarabun.ttf",
            "C:/Windows/Fonts/THSarabunNew.ttf",
            "C:/Windows/Fonts/THSarabun.ttf",
            "C:/Windows/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/thai/THSarabunNew.ttf",
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont('ThaiFont', path))
                    font_name = 'ThaiFont'
                    font_registered = True
                    logger.info(f"✅ Thai font loaded: {path}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Could not load font from {path}: {e}")
                    continue
        
        if not font_registered:
            try:
                from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                font_name = 'STSong-Light'
                font_registered = True
                logger.info("✅ Using UnicodeCIDFont (STSong-Light) as fallback")
            except:
                logger.warning("⚠️ No Thai font found. Using Helvetica.")
                font_name = 'Helvetica'

        # ---------- PDF Setup ----------
        # A4 Landscape with generous margins
        doc = SimpleDocTemplate(
            filename, 
            pagesize=A4,
            rightMargin=30, 
            leftMargin=30,
            topMargin=30, 
            bottomMargin=30
        )

        AVAILABLE_WIDTH = 595 - 60  # 535 points
        TABLE_WIDTH = int(AVAILABLE_WIDTH * 0.95)

        col1 = int(TABLE_WIDTH * 0.20)   
        col2 = int(TABLE_WIDTH * 0.60)   
        col3 = int(TABLE_WIDTH * 0.20)

        styles = getSampleStyleSheet()
        
        # Title style - Font size 20 for visibility
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontName=font_name,
            fontSize=20,  # Increased for better visibility
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        # Header style - Font size 16
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=16,
            alignment=TA_CENTER,
            textColor=colors.white,
            backColor=colors.HexColor('#0d6efd'),
            leading=20  # Line height for headers
        )
        
        # Cell style - Font size 16
        cell_style = ParagraphStyle(
            'Cell',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=16,
            alignment=TA_LEFT,
            leading=22  # Line height for cell content (readable with Thai text)
        )

        # ---------- Build Table Data ----------
        data = []
        # Header row
        data.append([
            Paragraph("ชื่อผู้แจ้ง", header_style),
            Paragraph("สถานที่ / รายละเอียด", header_style),
            Paragraph("วันที่แจ้ง", header_style)
        ])

        for row in rows:
            reporter = row[0] or "ไม่ระบุ"
            description = row[1] or ""
            # Try to split location and detail
            full_text = description
            if "สถานที่:" in description and "\n" in description:
                parts = description.split("\n", 1)
                location_text = parts[0].replace("สถานที่:", "").strip()
                detail_text = parts[1].replace("รายละเอียด:", "").strip() if len(parts) > 1 else ""
                full_text = f"สถานที่: {location_text}\nรายละเอียด: {detail_text}"

            created_at = row[2].strftime("%d/%m/%Y %H:%M") if row[2] else ""

            data.append([
                Paragraph(reporter, cell_style),
                Paragraph(full_text, cell_style),
                Paragraph(created_at, cell_style)
            ])

        # ---------- Create Table ----------
        table = Table(data, colWidths=[col1, col2, col3])
        table.setStyle(TableStyle([
            # Header background
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            # ---------- FIX: Set font size for ALL cells ----------
            ('FONTSIZE', (0, 0), (-1, -1), 16),  # <-- NOW applied to all cells
            # Header specific
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),
            # Cell padding (margins inside cells)
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            # Background for data rows (alternating)
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            # Grid lines
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            # Row height (allows content to fit)
            ('MINIMUMHEIGHT', (0, 1), (-1, -1), 30),
        ]))

        # ---------- Build Document ----------
        elements = []
        today_str = datetime.now().strftime("%d/%m/%Y")
        elements.append(Paragraph(f"รายงานปัญหาเร่งด่วนประจำวันที่ {today_str}", title_style))
        elements.append(Spacer(1, 16))  # Space between title and table
        elements.append(table)

        doc.build(elements)
        logger.info(f"✅ Report saved: {filename}")
        return filename

    except Exception as e:
        logger.error(f"❌ Report generation error: {e}", exc_info=True)
        return None

# Schedule daily at 18:00
def scheduled_report():
    generate_urgent_report_pdf()

scheduler = BackgroundScheduler()
scheduler.add_job(
    scheduled_report,
    trigger=CronTrigger(hour=18, minute=0, timezone="Asia/Bangkok"),
    id="daily_urgent_report",
    replace_existing=True,
    misfire_grace_time=3600,  # allow up to 1hr late
    coalesce=True,
)

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

def job_listener(event):
    if event.exception:
        logger.error(f"❌ Scheduled job failed: {event.exception}")
    elif event.code == EVENT_JOB_MISSED:
        logger.warning(f"⚠️ Scheduled job missed its run time: {event}")
    else:
        logger.info("✅ Scheduled job executed successfully")

scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

scheduler.start()




# ---------- NEW: API to generate report on demand ----------
@app.get("/api/generate-report")
async def generate_report_on_demand():
    """Generate report immediately (for testing)"""
    try:
        filename = generate_urgent_report_pdf()
        if filename:
            return {
                "success": True,
                "message": "Report generated successfully",
                "file": filename
            }
        else:
            return {
                "success": False,
                "message": "No pending urgent issues found for today"
            }
    except Exception as e:
        logger.error(f"❌ Generate report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- NEW: Get list of all reports ----------
@app.get("/api/reports-list")
async def get_reports_list():
    """Get list of all available report PDFs"""
    try:
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            return {"success": True, "reports": []}
        
        files = [f for f in os.listdir(reports_dir) if f.startswith("urgent_report_") and f.endswith(".pdf")]
        reports = []
        for f in sorted(files, reverse=True):
            # Extract date from filename
            # Format: urgent_report_20250101_1800.pdf
            parts = f.replace("urgent_report_", "").replace(".pdf", "").split("_")
            date_str = parts[0] if len(parts) > 0 else ""
            time_str = parts[1] if len(parts) > 1 else ""
            try:
                report_date = datetime.strptime(date_str, "%Y%m%d").strftime("%d/%m/%Y")
            except:
                report_date = date_str
            
            reports.append({
                "filename": f,
                "date": report_date,
                "time": time_str,
                "fullDate": f"{report_date} {time_str[:2]}:{time_str[2:]}",
                "filepath": f"/api/download-report/{f}"
            })
        
        return {"success": True, "reports": reports}
    except Exception as e:
        logger.error(f"❌ Reports list error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Updated download endpoint ----------
@app.get("/api/download-report/{filename}")
async def download_specific_report(filename: str):
    """Download a specific report by filename"""
    try:
        # Security: prevent path traversal
        if ".." in filename or not filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = os.path.join("reports", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Report not found")
        
        return FileResponse(
            file_path,
            media_type='application/pdf',
            filename=filename
        )
    except Exception as e:
        logger.error(f"❌ Download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving report")


# ---------- Keep old endpoint for backward compatibility ----------
@app.get("/api/download-report")
async def download_latest_report():
    """Download the most recent urgent report PDF."""
    try:
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            raise HTTPException(status_code=404, detail="No reports found")
        
        files = [f for f in os.listdir(reports_dir) if f.startswith("urgent_report_") and f.endswith(".pdf")]
        if not files:
            raise HTTPException(status_code=404, detail="No reports available")
        
        files.sort(reverse=True)
        latest = files[0]
        file_path = os.path.join(reports_dir, latest)
        return FileResponse(
            file_path,
            media_type='application/pdf',
            filename=f"urgent_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    except Exception as e:
        logger.error(f"❌ Download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving report")


# Shutdown scheduler on app exit
@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()