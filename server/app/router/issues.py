from typing import Optional
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException, status, Query
from linebot.models import TextSendMessage, ImageSendMessage
from ..firebase_auth import require_admin
from ..line_auth import verify_line_id_token
from ..config import logger
from .. import db
from .. import r2_client
from .. import sheets_client
from ..line_client import line_bot_api
from ..config import limiter

router = APIRouter(prefix="/api", tags=["issues"])


def _row_to_issue(row: dict):
    # D1 returns rows as dicts already, so this just renames keys to
    # match the camelCase shape the frontend expects.
    return {
        "id": row["id"],
        "lineUserId": row["line_user_id"],
        "reporterName": row["reporter_name"],
        "category": row["category"],
        "description": row["description"],
        "imageUrl": row["image_url"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "studentYear": row.get("student_year"),
        "studentClass": row.get("student_class"),
        "studentNumber": row.get("student_number"),
        "issueType": row.get("issue_type"),
        "fixImageUrl": row.get("fix_image_url"),
        "resolvedAt": row.get("resolved_at"),
    }


# ---------- GET /api/issues (Admin Only) ----------
@router.get("/issues")
async def get_issues(admin=Depends(require_admin)):
    rows = db.fetch_all("SELECT * FROM issues ORDER BY created_at DESC")
    issues = [_row_to_issue(row) for row in rows]
    return {"success": True, "issues": issues}


# ---------- GET /api/issues/community (LIFF Users) ----------
@router.get("/issues/community")
async def get_community_issues(
    view_mode: str = "mine",
    line_user=Depends(verify_line_id_token)
):
    if view_mode == "mine":
        rows = db.fetch_all(
            "SELECT * FROM issues WHERE line_user_id = ? ORDER BY created_at DESC",
            [line_user["userId"]]
        )
    else:
        rows = db.fetch_all(
            "SELECT * FROM issues WHERE line_user_id != ? ORDER BY created_at DESC",
            [line_user["userId"]]
        )
    issues = [_row_to_issue(row) for row in rows]
    return {"success": True, "issues": issues}


# ---------- POST /api/issues/{issue_id}/resolve ----------
@router.post("/issues/{issue_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_issue(
    issue_id: int,
    fix_image: UploadFile = File(...),
    admin=Depends(require_admin),
):
    logger.info(f"🔧 Resolving issue ID: {issue_id}")

    MAX_IMAGE_BYTES = 8 * 1024 * 1024

    def _validate_image(upload_file):
        if not upload_file.content_type or not upload_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type")
        contents = upload_file.file.read()
        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="Image too large")
        upload_file.file.seek(0)

    try:
        _validate_image(fix_image)
        logger.info(f"📤 Uploading fix image to R2: {fix_image.filename}")
        fix_image_url = r2_client.upload_image(fix_image.file, folder="school_issues/fixed")
        logger.info(f"✅ Fix image uploaded: {fix_image_url}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ R2 error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload fix image")

    try:
        query = """
            UPDATE issues
            SET status = 'resolved',
                fix_image_url = ?,
                resolved_at = datetime('now')
            WHERE id = ?
            RETURNING line_user_id, reporter_name, category, description, resolved_at;
        """
        result = db.execute(query, [fix_image_url, issue_id])
        if not result:
            raise HTTPException(status_code=404, detail="Issue not found")

        line_user_id = result["line_user_id"]
        reporter_name = result["reporter_name"]
        category = result["category"]
        description = result["description"]

        # Best-effort — updates the permanent log so it reflects the
        # outcome, but never blocks the resolve action if Sheets is down.
        sheets_client.mark_issue_resolved(issue_id, result["resolved_at"], fix_image_url)

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resolve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST /api/issues ----------
@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(
    request: Request,
    lineIdToken: str = Form(...),
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
    # Verify LINE token
    line_user = await verify_line_id_token(x_line_id_token=lineIdToken)
    lineUserId = line_user["userId"]
    # Use token display name if reporterName not provided
    if not reporterName:
        reporterName = line_user.get("displayName", "ผู้ใช้ LINE")

    logger.info(f"📝 POST /api/issues - User: {lineUserId}, Type: {issue_type}, Category: {category}")
    logger.info(f"📝 Reporter: {reporterName}, Description length: {len(description) if description else 0}")
    logger.info(f"📝 Student: {studentYear}/{studentClass}/{studentNumber}")

    image_url = None
    MAX_IMAGE_BYTES = 8 * 1024 * 1024

    def _validate_image(upload_file):
        if not upload_file.content_type or not upload_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type")
        contents = upload_file.file.read()
        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="Image too large")
        upload_file.file.seek(0)

    if image:
        _validate_image(image)
        try:
            logger.info(f"📤 Uploading image to R2: {image.filename}")
            image_url = r2_client.upload_image(image.file, folder="school_issues")
            logger.info(f"✅ Image uploaded: {image_url}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ R2 error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to upload image")

    try:
        query = """
            INSERT INTO issues
            (line_user_id, reporter_name, category, description, image_url,
             latitude, longitude, student_year, student_class, student_number, issue_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, line_user_id, reporter_name, category, description,
                      image_url, latitude, longitude, status, created_at,
                      student_year, student_class, student_number, issue_type;
        """
        values = [
            lineUserId, reporterName, category, description, image_url,
            latitude, longitude, studentYear, studentClass, studentNumber,
            issue_type
        ]

        logger.info(f"💾 Inserting issue into database...")
        new_row = db.execute(query, values)
        logger.info(f"✅ Issue inserted with ID: {new_row['id']}")

        # Best-effort permanent log — never blocks the reporter if Sheets is down.
        sheets_client.append_issue_row(new_row)

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
            "issue": _row_to_issue(new_row)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database insertion error: {str(e)}")
