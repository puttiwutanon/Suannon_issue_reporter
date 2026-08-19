"""
Google Sheets logging — a permanent, free archive of every issue ever
reported, so nothing is lost when D1 deletes resolved issues after
4 days. D1 stays the source of truth for the active workflow (admin
dashboard, LINE notifications); Sheets is a best-effort side log that
should never block or fail the user-facing request.

Setup (one-time, see step-by-step notes given alongside this file):
  1. Create/reuse a Google Cloud project, enable the Google Sheets API.
  2. Create a service account, download its JSON key.
  3. Share your target Google Sheet with the service account's
     client_email as Editor.
  4. Put the JSON key contents in GOOGLE_SERVICE_ACCOUNT_JSON and the
     sheet's ID (from its URL) in GOOGLE_SHEETS_ID.

Column order (row 1 should have these as headers):
  ID | LINE User ID | Reporter Name | Category | Description |
  Image URL | Latitude | Longitude | Status | Created At |
  Student Year | Student Class | Student Number | Issue Type |
  Fix Image URL | Resolved At
"""
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from .config import logger

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column positions (1-indexed, matching the header row above)
COL_ID = 1
COL_STATUS = 9
COL_FIX_IMAGE_URL = 15
COL_RESOLVED_AT = 16

_worksheet = None


def _get_worksheet():
    global _worksheet
    if _worksheet is not None:
        return _worksheet

    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not creds_json or not sheet_id:
        logger.warning("⚠️ Google Sheets not configured — skipping sheet logging")
        return None

    try:
        creds_info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        _worksheet = client.open_by_key(sheet_id).sheet1
        return _worksheet
    except Exception as e:
        logger.error(f"❌ Failed to connect to Google Sheets: {e}", exc_info=True)
        return None


def append_issue_row(issue: dict):
    """Best-effort: log a newly created issue. Never raises — a
    Sheets outage should not block someone from filing a report."""
    ws = _get_worksheet()
    if ws is None:
        return
    try:
        ws.append_row(
            [
                issue.get("id"),
                issue.get("line_user_id"),
                issue.get("reporter_name"),
                issue.get("category"),
                issue.get("description"),
                issue.get("image_url"),
                issue.get("latitude"),
                issue.get("longitude"),
                issue.get("status"),
                issue.get("created_at"),
                issue.get("student_year"),
                issue.get("student_class"),
                issue.get("student_number"),
                issue.get("issue_type"),
                issue.get("fix_image_url"),
                issue.get("resolved_at"),
            ],
            value_input_option="USER_ENTERED",
        )
        logger.info(f"📊 Logged issue {issue.get('id')} to Google Sheets")
    except Exception as e:
        logger.error(f"❌ Failed to append issue to Google Sheets: {e}", exc_info=True)


def mark_issue_resolved(issue_id: int, resolved_at: str, fix_image_url: str):
    """Best-effort: update an existing row's status once resolved,
    so the permanent log reflects the outcome, not just the report."""
    ws = _get_worksheet()
    if ws is None:
        return
    try:
        cell = ws.find(str(issue_id), in_column=COL_ID)
        if cell is None:
            logger.warning(f"⚠️ Issue {issue_id} not found in Sheets log — skipping update")
            return
        ws.update_cell(cell.row, COL_STATUS, "resolved")
        ws.update_cell(cell.row, COL_FIX_IMAGE_URL, fix_image_url)
        ws.update_cell(cell.row, COL_RESOLVED_AT, resolved_at)
        logger.info(f"📊 Updated issue {issue_id} in Google Sheets as resolved")
    except Exception as e:
        logger.error(f"❌ Failed to update issue in Google Sheets: {e}", exc_info=True)
