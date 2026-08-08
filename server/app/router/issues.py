from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Query
import cloudinary.uploader
from linebot.models import TextSendMessage, ImageSendMessage

from ..config import logger
from ..db import get_db_connection
from ..line_client import line_bot_api

router = APIRouter(prefix="/api", tags=["issues"])


# ---------- GET /api/issues ----------
@router.get("/issues")
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
@router.post("/issues/{issue_id}/resolve", status_code=status.HTTP_200_OK)
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
@router.post("/issues", status_code=status.HTTP_201_CREATED)
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
