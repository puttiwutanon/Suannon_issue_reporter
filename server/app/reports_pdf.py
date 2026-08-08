import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .config import logger
from .db import get_db_connection


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
            except Exception:
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
