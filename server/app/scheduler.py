from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from .config import logger
from . import db

scheduler = BackgroundScheduler()


# ---------- Auto-delete old resolved issues ----------
def delete_old_resolved_issues():
    """ลบรายการปัญหาที่แก้ไขแล้ว (status='resolved') ที่เก่ากว่า 4 วัน.

    Safe to delete from D1 since every issue is permanently logged to
    Google Sheets (see sheets_client.py) at creation and resolution
    time — this cleanup only trims D1's active working set, it is no
    longer the only copy of the data.
    """
    logger.info("🧹 Running scheduled cleanup: deleting old resolved issues")
    try:
        query = """
            DELETE FROM issues
            WHERE status = 'resolved'
              AND resolved_at < datetime('now', '-4 days')
            RETURNING id;
        """
        deleted = db.fetch_all(query)
        if deleted:
            logger.info(f"🗑️ Deleted {len(deleted)} old resolved issues")
        else:
            logger.info("✅ No old resolved issues to delete")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}", exc_info=True)


def job_listener(event):
    if event.exception:
        logger.error(f"❌ Scheduled job failed: {event.exception}")
    elif event.code == EVENT_JOB_MISSED:
        logger.warning(f"⚠️ Scheduled job missed its run time: {event}")
    else:
        logger.info("✅ Scheduled job executed successfully")


def start_scheduler():
    """Register jobs/listeners and start the scheduler. Call once from main.py startup."""
    scheduler.add_job(
        delete_old_resolved_issues,
        trigger=CronTrigger(hour=3, minute=0, timezone="Asia/Bangkok"),
        id="cleanup_old_resolved_issues",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1hr late
        coalesce=True,
    )
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    scheduler.start()
    logger.info("✅ Scheduler started")
