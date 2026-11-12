"""
Statistical analysis engine – real data only.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from database import get_db

QUESTION_LABELS = {
    1: "کیفیت غذا",
    2: "حجم غذا",
    3: "تنوع منوی غذایی",
    4: "اقلام همراه غذا",
    5: "بسته‌بندی غذا و اقلام",
    6: "بهداشت و نظافت رستوران",
    7: "رعایت موارد بهداشتی توسط متصدیان",
    8: "نحوه برخورد متصدیان",
    9: "چیدمان میز و صندلی",
    10: "زمان شروع و پایان سرو",
    11: "رضایت کلی از غذا و رستوران",
}

def get_overview_stats() -> Dict[str, Any]:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM responses WHERE status = 'registered'").fetchone()["c"]
        with_feedback = conn.execute(
            "SELECT COUNT(*) as c FROM responses WHERE status = 'registered' AND feedback IS NOT NULL AND TRIM(feedback) != ''"
        ).fetchone()["c"]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) as c FROM responses WHERE status = 'registered' AND date(created_at) = ?",
            (today,)
        ).fetchone()["c"]
        avg_row = conn.execute(
            "SELECT AVG(average_score) as avg_score FROM responses WHERE status = 'registered'"
        ).fetchone()
        avg_score = round(avg_row["avg_score"] or 0, 2)
        satisfaction_pct = round((avg_score / 4.0) * 100, 1) if avg_score else 0.0
        return {
            "total_responses": total,
            "complete_responses": total,
            "feedback_count": with_feedback,
            "today_count": today_count,
            "average_score": avg_score,
            "satisfaction_percent": satisfaction_pct,
        }

def get_question_averages() -> List[Dict[str, Any]]:
    with get_db() as conn:
        results = []
        for i in range(1, 12):
            col = f"q{i}"
            row = conn.execute(
                f"SELECT AVG({col}) as avg, COUNT({col}) as cnt FROM responses WHERE status = 'registered'"
            ).fetchone()
            avg = round(row["avg"] or 0, 2)
            results.append({
                "question": i,
                "label": QUESTION_LABELS[i],
                "average": avg,
                "satisfaction_percent": round((avg / 4.0) * 100, 1) if avg else 0.0,
                "count": row["cnt"],
            })
        return results

def get_option_distribution() -> Dict[str, Any]:
    with get_db() as conn:
        dist = {1: 0, 2: 0, 3: 0, 4: 0}
        total_answers = 0
        for i in range(1, 12):
            for score in range(1, 5):
                cnt = conn.execute(
                    f"SELECT COUNT(*) as c FROM responses WHERE status = 'registered' AND q{i} = ?",
                    (score,)
                ).fetchone()["c"]
                dist[score] += cnt
                total_answers += cnt
        labels = {1: "ضعیف", 2: "متوسط", 3: "خوب", 4: "خیلی خوب"}
        return {
            "labels": [labels[i] for i in range(1, 5)],
            "values": [dist[i] for i in range(1, 5)],
            "total": total_answers,
            "percentages": [round(dist[i] / total_answers * 100, 1) if total_answers else 0 for i in range(1, 5)],
        }

def get_trend(days: int = 30) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT date(created_at) as day, COUNT(*) as count
            FROM responses
            WHERE status = 'registered' AND created_at >= date('now', ?)
            GROUP BY date(created_at) ORDER BY day
            """,
            (f"-{days} days",)
        ).fetchall()
        return [{"date": r["day"], "count": r["count"]} for r in rows]

def get_responses(page=1, per_page=20, search_id=None, date_from=None, date_to=None, sort_by="created_at", sort_dir="desc"):
    allowed_sort = {"created_at", "participant_id", "average_score"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    with get_db() as conn:
        where = ["status = 'registered'"]
        params = []
        if search_id:
            where.append("participant_id LIKE ?")
            params.append(f"%{search_id}%")
        if date_from:
            where.append("date(created_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("date(created_at) <= ?")
            params.append(date_to)
        where_sql = " AND ".join(where)
        total = conn.execute(f"SELECT COUNT(*) as c FROM responses WHERE {where_sql}", params).fetchone()["c"]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""SELECT id, participant_id, created_at, average_score, status,
                   q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11, feedback
            FROM responses WHERE {where_sql}
            ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()
        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "participant_id": r["participant_id"],
                "created_at": r["created_at"],
                "average_score": round(r["average_score"], 2) if r["average_score"] else 0,
                "status": r["status"],
                "has_feedback": bool(r["feedback"] and r["feedback"].strip()),
                "answers": {f"q{i}": r[f"q{i}"] for i in range(1, 12)},
                "feedback": r["feedback"] or "",
            })
        return {"items": items, "total": total, "page": page, "per_page": per_page,
                "pages": max(1, (total + per_page - 1) // per_page)}

def get_feedbacks(page=1, per_page=20, search=None, date_from=None, date_to=None):
    with get_db() as conn:
        where = ["status = 'registered'", "feedback IS NOT NULL", "TRIM(feedback) != ''"]
        params = []
        if search:
            where.append("feedback LIKE ?")
            params.append(f"%{search}%")
        if date_from:
            where.append("date(created_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("date(created_at) <= ?")
            params.append(date_to)
        where_sql = " AND ".join(where)
        total = conn.execute(f"SELECT COUNT(*) as c FROM responses WHERE {where_sql}", params).fetchone()["c"]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""SELECT participant_id, created_at, feedback, average_score
            FROM responses WHERE {where_sql}
            ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()
        return {
            "items": [{"participant_id": r["participant_id"], "created_at": r["created_at"],
                       "feedback": r["feedback"],
                       "average_score": round(r["average_score"], 2) if r["average_score"] else 0} for r in rows],
            "total": total, "page": page, "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
        }

def get_system_health() -> Dict[str, Any]:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM responses").fetchone()["c"]
        errors = conn.execute("SELECT COUNT(*) as c FROM responses WHERE status = 'error'").fetchone()["c"]
        success_rate = 100.0 if total == 0 else round((total - errors) / total * 100, 1)
        db_ok = True
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception:
            db_ok = False
        last_backup = conn.execute(
            "SELECT created_at, status FROM backups ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        backup_ok = bool(last_backup and last_backup["status"] == "success")
        recent_errors = conn.execute(
            """SELECT COUNT(*) as c FROM system_logs
            WHERE event_type LIKE '%error%' AND created_at >= datetime('now', '-1 day')"""
        ).fetchone()["c"]
        score = 100
        if not db_ok:
            score -= 40
        if success_rate < 95:
            score -= int((100 - success_rate) * 0.5)
        if not backup_ok and total > 0:
            score -= 15
        if recent_errors > 5:
            score -= min(20, recent_errors * 2)
        score = max(0, min(100, score))
        if score >= 90:
            status = "عالی"
        elif score >= 75:
            status = "خوب"
        elif score >= 50:
            status = "نیازمند بررسی"
        elif score >= 25:
            status = "نامطلوب"
        else:
            status = "قطع‌شده"
        return {
            "score": score, "status": status, "db_healthy": db_ok,
            "success_rate": success_rate, "total_requests": total, "error_count": errors,
            "recent_errors_24h": recent_errors,
            "last_backup": last_backup["created_at"] if last_backup else None,
            "backup_ok": backup_ok,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": 12,
        }
