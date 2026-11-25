import asyncio
from typing import Optional
from fastapi import (
    APIRouter, BackgroundTasks, Depends, Request, UploadFile, File, Form,
    HTTPException, status,
)
from fastapi.responses import StreamingResponse
from fastapi.responses import StreamingResponse
from linebot.models import TextSendMessage, ImageSendMessage
from ..firebase_auth import require_admin, verify_admin_token
from ..line_auth import verify_line_id_token
from ..config import logger, now_th
from .. import db
from .. import r2_client
from .. import sheets_client
from ..line_client import line_bot_api
from ..config import limiter
from ..connection_manager import manager


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
        "userStatus": row.get("user_status"),
        "contactNumber": row.get("contact_number"),
        "issueType": row.get("issue_type"),
        "fixImageUrl": row.get("fix_image_url"),
        "resolvedAt": row.get("resolved_at"),
        "progressImageUrl": row.get("progress_image_url"),
        "acknowledgedAt": row.get("acknowledged_at"),
        "inProgressAt": row.get("in_progress_at"),
        "declinedAt": row.get("declined_at"),
        "topic": row.get("topic"),
        "declineReason": row.get("decline_reason"),
    }


def _validate_image_upload(upload_file, max_bytes: int = 8 * 1024 * 1024):
    if not upload_file.content_type or not upload_file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")
    contents = upload_file.file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail="Image too large")
    upload_file.file.seek(0)


# ---------- Notification helpers (run as background tasks) ----------
# LINE pushes and the Sheets log are both "fire and forget" from the
# caller's point of view — the HTTP response should not wait on either
# of them. Wrapping them as background_tasks.add_task(...) means
# FastAPI runs them (in a worker thread, since they're sync) *after*
# the response has already been sent, instead of blocking the request
# on a LINE API round-trip or a multi-call Sheets update.
def _notify_acknowledged(line_user_id: str, topic: str, category: str, description: str):
    try:
        line_bot_api.push_message(
            to=line_user_id,
            messages=TextSendMessage(
                text=(
                    f"📨 ทีมงานได้รับเรื่องแจ้ง: {topic} ของคุณแล้ว และกำลังดำเนินการอยู่ครับ\n\n"
                    f"📋 ประเภท: {category}\n"
                    f"📝 รายละเอียด: {description}\n\n"
                    f"กรุณารอสักครู่นะครับ 🙏"
                )
            ),
        )
        logger.info(f"✅ 'acknowledged' notification sent to {line_user_id}")
    except Exception as e:
        logger.error(f"❌ LINE push error: {e}", exc_info=True)


def _notify_in_progress(line_user_id: str, topic: str, progress_image_url: str):
    try:
        line_bot_api.push_message(
            to=line_user_id,
            messages=[
                TextSendMessage(text=f"🔧 ทีมงานกำลังดำเนินการซ่อมแซมเรื่อง: {topic}\nที่คุณแจ้งอยู่ครับ"),
                ImageSendMessage(
                    original_content_url=progress_image_url,
                    preview_image_url=progress_image_url,
                ),
            ],
        )
        logger.info(f"✅ 'in_progress' notification sent to {line_user_id}")
    except Exception as e:
        logger.error(f"❌ LINE push error: {e}", exc_info=True)


def _notify_resolved(line_user_id: str, topic: str, category: str, description: str, fix_image_url: Optional[str]):
    try:
        messages = [
            TextSendMessage(
                text=(
                    f"✅ เรื่องแจ้ง: {topic} ได้รับการแก้ไขแล้ว!\n\n"
                    f"📋 ประเภท: {category}\n"
                    f"📝 รายละเอียด: {description}\n\n"
                    f"ขอบคุณที่ช่วยทำให้โรงเรียนของเราดีขึ้นครับ 🙏"
                )
            )
        ]
        if fix_image_url:
            messages.append(
                ImageSendMessage(
                    original_content_url=fix_image_url,
                    preview_image_url=fix_image_url,
                )
            )
        line_bot_api.push_message(to=line_user_id, messages=messages)
        logger.info(f"✅ 'resolved' notification sent to {line_user_id}")
    except Exception as e:
        logger.error(f"❌ LINE push error: {e}", exc_info=True)


def _notify_declined(line_user_id: str, topic: str, category: str, description: str, decline_reason: Optional[str] = None):
    try:
        reason_line = f"\n📋 เหตุผล: {decline_reason}\n" if decline_reason else "\n"
        line_bot_api.push_message(
            to=line_user_id,
            messages=TextSendMessage(
                text=(
                    f"เรื่องแจ้ง: {topic} ไม่สามารถดำเนินการได้ในขณะนี้ครับ\n\n"
                    f"📋 ประเภท: {category}\n"
                    f"📝 รายละเอียด: {description}\n"
                    f"{reason_line}"
                    f"ขอบคุณที่แจ้งให้ทราบครับ 🙏"
                )
            ),
        )
        logger.info(f"✅ 'declined' notification sent to {line_user_id}")
    except Exception as e:
        logger.error(f"❌ LINE push error: {e}", exc_info=True)


def _log_created_to_sheets(new_row: dict):
    # Best-effort — never blocks the reporter if Sheets is down.
    sheets_client.append_issue_row(new_row)

def _log_status_to_sheets(issue_id: int, new_status: str, **kwargs):
    # Best-effort — never blocks the status-update action if Sheets is down.
    sheets_client.update_issue_status(issue_id, new_status, **kwargs)


# ---------- GET /api/issues (Admin Only) ----------
@router.get("/issues")
async def get_issues(admin=Depends(require_admin)):
    rows = await db.afetch_all("SELECT * FROM issues ORDER BY created_at DESC")
    issues = [_row_to_issue(row) for row in rows]
    return {"success": True, "issues": issues}


# ---------- GET /api/issues/community (LIFF Users) ----------
@router.get("/issues/community")
async def get_community_issues(
    view_mode: str = "mine",
    line_user=Depends(verify_line_id_token)
):
    if view_mode == "mine":
        rows = await db.afetch_all(
            "SELECT * FROM issues WHERE line_user_id = ? ORDER BY created_at DESC",
            [line_user["userId"]]
        )
    else:
        rows = await db.afetch_all(
            "SELECT * FROM issues WHERE line_user_id != ? ORDER BY created_at DESC",
            [line_user["userId"]]
        )
    issues = [_row_to_issue(row) for row in rows]
    return {"success": True, "issues": issues}


# ---------- POST /api/issues/{issue_id}/status ----------
# Drives the 3-step admin flow: pending -> acknowledged -> in_progress -> resolved.
#   pending -> acknowledged   : no image. Just tells the reporter the team has it.
#   acknowledged -> in_progress : requires an image (the "fixing in progress" photo).
#   in_progress -> resolved   : no new image required — falls back to the
#                                progress photo already on file. An admin can
#                                still attach a fresh "after" photo if they want one.
#
# Rejects any transition that doesn't match the issue's current status (e.g.
# calling this with status=resolved on an issue that's still `pending`) so a
# stale dashboard tab or a double-click can't skip a step.
ALLOWED_TRANSITIONS = {
    "pending": "acknowledged",
    "acknowledged": "in_progress",
    "in_progress": "resolved",
}

# Declining bypasses the normal step order — allowed from any
# non-terminal state, not just the "current expected next" one.
DECLINABLE_STATUSES = {"pending", "acknowledged", "in_progress"}

@router.get("/issues/stream")
async def stream_issues(token: str):
    # EventSource can't send custom headers, so the token comes in as a
    # query param here instead of the Authorization header your other
    # admin routes use.
    await verify_admin_token(token)

    queue = await manager.connect()

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # keeps the connection alive through proxies that kill idle sockets
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            manager.disconnect(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/issues/{issue_id}/status", status_code=status.HTTP_200_OK)
async def update_issue_status(
    issue_id: int,
    background_tasks: BackgroundTasks,
    status_value: str = Form(..., alias="status"),
    image: Optional[UploadFile] = File(None),
    declineReason: Optional[str] = Form(None),   # ← new
    admin=Depends(require_admin),
):
    logger.info(f"🔄 Updating issue {issue_id} status -> {status_value}")

    row = await db.afetch_one("SELECT * FROM issues WHERE id = ?", [issue_id])
    if not row:
        raise HTTPException(status_code=404, detail="Issue not found")

    current_status = row["status"]
    line_user_id = row["line_user_id"]
    topic = row["topic"]
    category = row["category"]
    description = row["description"]

    if status_value == "declined":
        if current_status not in DECLINABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot decline an issue that is already '{current_status}'",
            )
        await db.aexecute(
            "UPDATE issues SET status = 'declined', declined_at = ?, decline_reason = ? WHERE id = ?",
            [now_th(), declineReason, issue_id],
        )
        background_tasks.add_task(_log_status_to_sheets, issue_id, "declined", decline_reason=declineReason)
        background_tasks.add_task(manager.broadcast, {"type": "issue_updated", "issueId": issue_id})
        background_tasks.add_task(_notify_declined, line_user_id, topic, category, description, declineReason)
        return {"success": True, "message": "Issue declined", "status": "declined"}

    expected_next = ALLOWED_TRANSITIONS.get(current_status)
    if status_value != expected_next:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move from '{current_status}' to '{status_value}' "
                   f"(expected next status: '{expected_next}')",
        )

    if status_value == "acknowledged":
        await db.aexecute(
            "UPDATE issues SET status = 'acknowledged', acknowledged_at = ? WHERE id = ?",
            [now_th(), issue_id],
        )
        background_tasks.add_task(_log_status_to_sheets, issue_id, "acknowledged")
        background_tasks.add_task(_notify_acknowledged, line_user_id, topic, category, description)
        background_tasks.add_task(manager.broadcast, {"type": "issue_updated", "issueId": issue_id})

        return {
            "success": True,
            "message": "Issue acknowledged",
            "status": "acknowledged",
        }

    if status_value == "in_progress":
        progress_image_url = None
        if image:
            try:
                _validate_image_upload(image)
                logger.info(f"📤 Uploading progress image to R2: {image.filename}")
                progress_image_url = await r2_client.aupload_image(image.file, folder="school_issues/progress")
                logger.info(f"✅ Progress image uploaded: {progress_image_url}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ R2 error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to upload progress image")

        await db.aexecute(
            "UPDATE issues SET status = 'in_progress', progress_image_url = ?, "
            "in_progress_at = ? WHERE id = ?",
            [progress_image_url, now_th(), issue_id],
        )

        background_tasks.add_task(_log_status_to_sheets, issue_id, "in_progress")
        if progress_image_url:
            background_tasks.add_task(_notify_in_progress, line_user_id, topic, progress_image_url)
        else:
            background_tasks.add_task(_notify_acknowledged, line_user_id, topic, category, description)
        background_tasks.add_task(manager.broadcast, {"type": "issue_updated", "issueId": issue_id})
        return {
            "success": True,
            "message": "Issue marked in progress",
            "status": "in_progress",
            "progressImageUrl": progress_image_url,
        }

    if status_value == "resolved":
        fix_image_url = row.get("progress_image_url")
        if image:
            try:
                _validate_image_upload(image)
                logger.info(f"📤 Uploading final fix image to R2: {image.filename}")
                fix_image_url = await r2_client.aupload_image(image.file, folder="school_issues/fixed")
                logger.info(f"✅ Final fix image uploaded: {fix_image_url}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ R2 error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to upload final fix image")

        result = await db.aexecute(
            "UPDATE issues SET status = 'resolved', fix_image_url = ?, resolved_at = ? "
            "WHERE id = ? RETURNING resolved_at",
            [fix_image_url, now_th(), issue_id],
        )

        background_tasks.add_task(_log_status_to_sheets, issue_id, "resolved", resolved_at=result["resolved_at"], fix_image_url=fix_image_url)
        background_tasks.add_task(_notify_resolved, line_user_id, topic, category, description, fix_image_url)
        background_tasks.add_task(manager.broadcast, {"type": "issue_updated", "issueId": issue_id})
        return {
            "success": True,
            "message": "Issue resolved and notification sent",
            "status": "resolved",
            "fixImageUrl": fix_image_url,
        }

    # Unreachable given ALLOWED_TRANSITIONS, but keep an explicit guard
    # rather than silently doing nothing if a new status value shows up.
    raise HTTPException(status_code=400, detail=f"Unknown status: {status_value}")


# ---------- POST /api/issues ----------
@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(
    request: Request,
    background_tasks: BackgroundTasks,
    lineIdToken: str = Form(...),
    reporterName: str = Form(None),
    topic: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    user_status: str = Form(None),
    contactNumber: str = Form(None),
    issue_type: Optional[str] = Form('urgent'),
):
    # Verify LINE token
    line_user = await verify_line_id_token(x_line_id_token=lineIdToken)
    lineUserId = line_user["userId"]
    # Use token display name if reporterName not provided
    if not reporterName:
        reporterName = line_user.get("displayName", "ผู้ใช้ LINE")

    logger.info(f"📝 POST /api/issues - User: {lineUserId}, Type: {issue_type}, Topic: {topic}, Category: {category}")
    logger.info(f"📝 Reporter: {reporterName}, Description length: {len(description) if description else 0}")
    logger.info(f"📝 User Status: {user_status}, Contact: {contactNumber}, Location: ({latitude}, {longitude})")

    if issue_type == 'urgent':
        missing = [
            name for name, val in [
                ("reporterName", reporterName),
                ("topic", topic),
                ("category", category),
                ("description", description),
                ("user_status", user_status),
                ("contactNumber", contactNumber),
            ] if not val or not val.strip()
        ]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field(s) for urgent report: {', '.join(missing)}",
            )

    image_url = None
    if image:
        _validate_image_upload(image)
        try:
            logger.info(f"📤 Uploading image to R2: {image.filename}")
            image_url = await r2_client.aupload_image(image.file, folder="school_issues")
            logger.info(f"✅ Image uploaded: {image_url}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ R2 error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to upload image")

    try:
        query = """
            INSERT INTO issues
            (line_user_id, reporter_name, topic, category, description, image_url,
             latitude, longitude, user_status, contact_number, issue_type,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, line_user_id, reporter_name, topic, category, description,
                      image_url, latitude, longitude, status, created_at,
                      user_status, contact_number, issue_type;
        """
        values = [
            lineUserId, reporterName, topic, category, description, image_url,
            latitude, longitude, user_status, contactNumber,
            issue_type, now_th()
        ]

        logger.info("💾 Inserting issue into database...")
        new_row = await db.aexecute(query, values)
        logger.info(f"✅ Issue inserted with ID: {new_row['id']}")

        background_tasks.add_task(_log_created_to_sheets, new_row)
        background_tasks.add_task(manager.broadcast, {"type": "issue_created", "issueId": new_row["id"]})

        if issue_type == 'suggestion':
            msg_text = "✅ ส่งข้อเสนอแนะสำเร็จแล้ว!\nขอบคุณที่ช่วยพัฒนาโรงเรียนของเรา 🙏"
        else:
            msg_text = "✅ แจ้งปัญหาสำเร็จแล้ว!\nทีมงานจะแจ้งให้ทราบอีกครั้งเมื่อเรื่องที่แจ้งถึงมือช่าง 🛠️"

        def _send_created_confirmation():
            try:
                logger.info(f"📤 Sending LINE confirmation to: {lineUserId}")
                line_bot_api.push_message(to=lineUserId, messages=TextSendMessage(text=msg_text))
                logger.info("✅ LINE confirmation sent")
            except Exception as e:
                logger.error(f"❌ LINE push error: {e}", exc_info=True)

        background_tasks.add_task(_send_created_confirmation)

        return {
            "success": True,
            "issue": _row_to_issue(new_row)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database insertion error: {str(e)}")

    
# ---------- POST /api/issues/{issue_id}/inform ----------
@router.post("/issues/{issue_id}/inform", status_code=status.HTTP_200_OK)
async def inform_reporter(
    issue_id: int,
    background_tasks: BackgroundTasks,
    informMessage: str = Form(...),
    admin=Depends(require_admin),
):
    """Send a custom inform message to the reporter (no status change)."""
    logger.info(f"📤 Admin inform on issue {issue_id}")

    row = await db.afetch_one("SELECT * FROM issues WHERE id = ?", [issue_id])
    if not row:
        raise HTTPException(status_code=404, detail="Issue not found")

    line_user_id = row["line_user_id"]
    topic = row["topic"]
    category = row["category"]
    description = row["description"]

    # Send the inform message
    def _send_inform():
        try:
            line_bot_api.push_message(
                to=line_user_id,
                messages=TextSendMessage(
                    text=(
                        f"📢 แจ้งข้อมูลจากทีมงาน\n\n"
                        f"เรื่อง: {topic}\n"
                        f"หมวดหมู่: {category}\n"
                        f"รายละเอียด: {description}\n\n"
                        f"📝 {informMessage}\n\n"
                        f"ขอบคุณครับ 🙏"
                    )
                ),
            )
            logger.info(f"✅ Inform message sent to {line_user_id}")
        except Exception as e:
            logger.error(f"❌ LINE push error: {e}", exc_info=True)

    background_tasks.add_task(_send_inform)
    # Optionally broadcast a real‑time event to refresh dashboard (if SSE is used)
    background_tasks.add_task(manager.broadcast, {"type": "inform_sent", "issueId": issue_id})

    return {"success": True, "message": "Inform message sent"}