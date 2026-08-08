import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import logger
from ..reports_pdf import generate_urgent_report_pdf

router = APIRouter(prefix="/api", tags=["reports"])


# ---------- Generate report on demand ----------
@router.get("/generate-report")
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


# ---------- Get list of all reports ----------
@router.get("/reports-list")
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
            except Exception:
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


# ---------- Download a specific report ----------
@router.get("/download-report/{filename}")
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
@router.get("/download-report")
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
