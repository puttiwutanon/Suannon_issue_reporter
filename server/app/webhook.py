from fastapi import APIRouter, Request, HTTPException, Header
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, URIAction
)

from .config import logger
from .line_client import line_bot_api, handler

router = APIRouter(tags=["webhook"])


@router.post("/webhook")
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
