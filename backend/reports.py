"""
Export reports: Excel, CSV, PDF.
"""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from database import get_db, BASE_DIR
from analytics import get_overview_stats, get_question_averages, QUESTION_LABELS

BACKUPS_DIR = BASE_DIR / "backups"
BACKUPS_DIR.mkdir(exist_ok=True)
NAVY = "102B46"
BLUE = "1769AA"

def export_csv() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ["شناسه مشارکت‌کننده", "تاریخ ثبت", "میانگین امتیاز"] + [
        QUESTION_LABELS[i] for i in range(1, 12)
    ] + ["پیشنهاد/انتقاد"]
    writer.writerow(headers)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT participant_id, created_at, average_score,
                   q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11, feedback
            FROM responses WHERE status = 'registered' ORDER BY id"""
        ).fetchall()
        for r in rows:
            writer.writerow([
                r["participant_id"], r["created_at"],
                round(r["average_score"], 2) if r["average_score"] else "",
                r["q1"], r["q2"], r["q3"], r["q4"], r["q5"],
                r["q6"], r["q7"], r["q8"], r["q9"], r["q10"], r["q11"],
                r["feedback"] or "",
            ])
    return ("\ufeff" + output.getvalue()).encode("utf-8")

def export_excel() -> bytes:
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "خلاصه"
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor=NAVY)
    stats = get_overview_stats()
    ws1["A1"] = "گزارش نظرسنجی وعده غذایی ناهار"
    ws1["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws1["A2"] = f"تاریخ تولید: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ws1["A4"] = "شاخص"
    ws1["B4"] = "مقدار"
    ws1["A4"].fill = header_fill
    ws1["B4"].fill = header_fill
    ws1["A4"].font = header_font
    ws1["B4"].font = header_font
    rows_data = [
        ("تعداد کل پاسخ‌ها", stats["total_responses"]),
        ("میانگین رضایت کلی", stats["average_score"]),
        ("درصد رضایت کلی", f"{stats['satisfaction_percent']}%"),
        ("تعداد پیشنهادها و انتقادات", stats["feedback_count"]),
        ("پاسخ‌های امروز", stats["today_count"]),
    ]
    for i, (k, v) in enumerate(rows_data, start=5):
        ws1[f"A{i}"] = k
        ws1[f"B{i}"] = v
    ws2 = wb.create_sheet("میانگین سؤالات")
    ws2["A1"] = "سؤال"
    ws2["B1"] = "میانگین (از ۴)"
    ws2["C1"] = "درصد رضایت"
    for col in ("A", "B", "C"):
        ws2[f"{col}1"].fill = header_fill
        ws2[f"{col}1"].font = header_font
    avgs = get_question_averages()
    for i, q in enumerate(avgs, start=2):
        ws2[f"A{i}"] = q["label"]
        ws2[f"B{i}"] = q["average"]
        ws2[f"C{i}"] = f"{q['satisfaction_percent']}%"
    ws3 = wb.create_sheet("تمام پاسخ‌ها")
    headers = ["شناسه", "تاریخ", "میانگین"] + [f"س{i}" for i in range(1, 12)] + ["بازخورد"]
    for col, h in enumerate(headers, start=1):
        cell = ws3.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
    with get_db() as conn:
        data = conn.execute(
            """SELECT participant_id, created_at, average_score,
                   q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11, feedback
            FROM responses WHERE status = 'registered' ORDER BY id"""
        ).fetchall()
        for row_idx, r in enumerate(data, start=2):
            values = [
                r["participant_id"], r["created_at"],
                round(r["average_score"], 2) if r["average_score"] else "",
                r["q1"], r["q2"], r["q3"], r["q4"], r["q5"],
                r["q6"], r["q7"], r["q8"], r["q9"], r["q10"], r["q11"],
                r["feedback"] or "",
            ]
            for col, v in enumerate(values, start=1):
                ws3.cell(row_idx, col, v)
    for ws in (ws1, ws2, ws3):
        for col in ws.columns:
            max_len = 12
            for cell in col:
                if cell.value:
                    max_len = max(max_len, min(len(str(cell.value)), 40))
            ws.column_dimensions[col[0].column_letter].width = max_len + 2
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def export_pdf() -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleFa", parent=styles["Title"], fontSize=16, alignment=1, spaceAfter=20)
    normal = ParagraphStyle("NormalFa", parent=styles["Normal"], fontSize=11, leading=16, alignment=2)
    story = []
    story.append(Paragraph("گزارش نظرسنجی وعده غذایی ناهار", title_style))
    story.append(Paragraph(f"پالایش گاز بیدبلند خلیج فارس — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", normal))
    story.append(Spacer(1, 20))
    stats = get_overview_stats()
    data = [
        ["شاخص", "مقدار"],
        ["تعداد کل پاسخ‌ها", str(stats["total_responses"])],
        ["میانگین رضایت کلی", str(stats["average_score"])],
        ["درصد رضایت", f"{stats['satisfaction_percent']}%"],
        ["تعداد پیشنهادها", str(stats["feedback_count"])],
        ["پاسخ‌های امروز", str(stats["today_count"])],
    ]
    table = Table(data, colWidths=[250, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102B46")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F3F6FA")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("میانگین سؤالات", title_style))
    avgs = get_question_averages()
    qdata = [["سؤال", "میانگین", "درصد"]]
    for q in avgs:
        qdata.append([q["label"], str(q["average"]), f"{q['satisfaction_percent']}%"])
    qtable = Table(qdata, colWidths=[280, 80, 80])
    qtable.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1769AA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6FA")]),
    ]))
    story.append(qtable)
    doc.build(story)
    return buf.getvalue()

def create_backup() -> dict:
    from database import DB_PATH, log_event
    import shutil
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = BACKUPS_DIR / f"survey_backup_{ts}.db"
    try:
        shutil.copy2(DB_PATH, dest)
        size = dest.stat().st_size
        with get_db() as conn:
            conn.execute(
                "INSERT INTO backups (filename, size_bytes, created_at, status) VALUES (?, ?, ?, ?)",
                (dest.name, size, datetime.now(timezone.utc).isoformat(), "success"),
            )
        log_event("backup_created", dest.name)
        return {"success": True, "filename": dest.name, "size": size}
    except Exception as e:
        log_event("backup_error", str(e))
        return {"success": False, "error": str(e)}
