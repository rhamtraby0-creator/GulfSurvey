import json
import re
import sqlite3
"""
پالایش گاز بیدبلند خلیج فارس – سامانه نظرسنجی وعده غذایی ناهار
Main FastAPI application.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from database import init_db, get_db, get_next_participant_id, log_event, BASE_DIR
from auth import (
    setup_initial_admin, login, logout, validate_session, require_admin, change_password
)
from analytics import (
    get_overview_stats, get_question_averages, get_option_distribution,
    get_trend, get_responses, get_feedbacks, get_system_health
)
from reports import export_csv, export_excel, export_pdf, create_backup

app = FastAPI(
    title="سامانه نظرسنجی پالایش گاز بیدبلند خلیج فارس",
    docs_url=None,
    redoc_url=None,
)

FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        return response

app.add_middleware(TimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

class SurveySubmit(BaseModel):
    q1: int = Field(..., ge=1, le=4)
    q2: int = Field(..., ge=1, le=4)
    q3: int = Field(..., ge=1, le=4)
    q4: int = Field(..., ge=1, le=4)
    q5: int = Field(..., ge=1, le=4)
    q6: int = Field(..., ge=1, le=4)
    q7: int = Field(..., ge=1, le=4)
    q8: int = Field(..., ge=1, le=4)
    q9: int = Field(..., ge=1, le=4)
    q10: int = Field(..., ge=1, le=4)
    q11: int = Field(..., ge=1, le=4)
    feedback: Optional[str] = Field(None, max_length=2000)

class LoginRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@app.on_event("startup")
def on_startup():
    init_db()
    with get_db() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(responses)")
        }
        if "client_token" not in columns:
            conn.execute(
                "ALTER TABLE responses ADD COLUMN client_token TEXT"
            )
        if "answers" not in columns:
            conn.execute("ALTER TABLE responses ADD COLUMN answers TEXT")
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_responses_client_token
            ON responses(client_token)
        """)
    plain = setup_initial_admin()
    if plain:
        secret_file = DATA_DIR / ".initial_password"
        secret_file.write_text(plain, encoding="utf-8")
        os.chmod(secret_file, 0o600)
        print("\n" + "=" * 60)
        print("  رمز اولیه پنل مدیریت (فقط یک‌بار نمایش داده می‌شود):")
        print(f"  {plain}")
        print("=" * 60 + "\n")

@app.get("/", response_class=HTMLResponse)
async def index_page():
    index_path = FRONTEND_DIR / "Index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Index.html not found</h1>", status_code=404)

@app.get("/admin", response_class=HTMLResponse)
@app.get("/Admin.html", response_class=HTMLResponse)
async def admin_page():
    admin_path = FRONTEND_DIR / "Admin.html"
    if admin_path.exists():
        return HTMLResponse(admin_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Admin.html not found</h1>", status_code=404)




@app.post("/api/survey/submit")
async def submit_survey(data: SurveySubmit, request: Request):
    token = request.headers.get("X-Client-Token", "").strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", token):
        raise HTTPException(status_code=400, detail="شناسه مرورگر معتبر نیست.")

    answers = [getattr(data, f"q{i}") for i in range(1, 12)]

    try:
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")

            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(responses)")
            }
            required = {
                "participant_id", "client_token",
                "q1", "q2", "q3", "q4", "q5", "q6",
                "q7", "q8", "q9", "q10", "q11",
                "feedback", "created_at", "status"
            }
            missing = required - columns
            if missing:
                raise RuntimeError(
                    "Database schema missing: " + ", ".join(sorted(missing))
                )

            previous = conn.execute(
                "SELECT participant_id FROM responses WHERE client_token = ?",
                (token,)
            ).fetchone()

            if previous:
                raise HTTPException(
                    status_code=409,
                    detail="با تشکر، شما قبلاً رأی داده‌اید."
                )

            participant_id = get_next_participant_id(conn)
            now = datetime.now(timezone.utc).isoformat()
            feedback = (data.feedback or "").strip() or None

            conn.execute("""
                INSERT INTO responses (
                    participant_id, client_token,
                    q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                    feedback, created_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registered')
            """, (
                participant_id, token, *answers, feedback, now
            ))

            try:
                conn.execute("""
                    INSERT INTO system_logs
                    (event_type, message, created_at)
                    VALUES (?, ?, ?)
                """, ("survey_submitted", f"participant={participant_id}", now))
            except sqlite3.Error as log_error:
                print("SURVEY_LOG_ERROR:", repr(log_error))

        return {
            "success": True,
            "participant_id": participant_id,
            "message": "نظرسنجی با موفقیت ثبت شد"
        }

    except HTTPException:
        raise
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="این نظرسنجی قبلاً ثبت شده است."
        )
    except Exception as e:
        import traceback
        print("SURVEY_V2_ERROR:", repr(e))
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="خطا در ثبت نظرسنجی. لطفاً دوباره تلاش کنید."
        )

@app.get("/api/health")
async def public_health():
    return {"status": "ok", "service": "survey"}


@app.get("/api/version")
async def release_version():
    return {
        "release": "GULFSURVEY-SUBMIT-V2-20261113",
        "submit": "v2"
    }

@app.post("/api/admin/login")
async def admin_login(body: LoginRequest, response: Response):
    success, msg, token, wait = login(body.password)
    if not success:
        return JSONResponse(
            status_code=401 if wait == 0 else 429,
            content={"success": False, "message": msg, "wait_seconds": wait},
        )
    response.set_cookie(
        key="admin_session", value=token, httponly=True,
        samesite="lax", max_age=8 * 3600, path="/",
    )
    return {"success": True, "message": msg, "token": token}

@app.post("/api/admin/logout")
async def admin_logout(request: Request, response: Response, token: str = Depends(require_admin)):
    logout(token)
    response.delete_cookie("admin_session", path="/")
    return {"success": True, "message": "خروج موفق"}

@app.get("/api/admin/check")
async def admin_check(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
    return {"authenticated": validate_session(token)}

@app.post("/api/admin/change-password")
async def admin_change_password(body: ChangePasswordRequest, token: str = Depends(require_admin)):
    ok, msg = change_password(body.old_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.get("/api/admin/stats")
async def admin_stats(_: str = Depends(require_admin)):
    return get_overview_stats()

@app.get("/api/admin/question-averages")
async def admin_question_averages(_: str = Depends(require_admin)):
    return get_question_averages()

@app.get("/api/admin/distribution")
async def admin_distribution(_: str = Depends(require_admin)):
    return get_option_distribution()

@app.get("/api/admin/trend")
async def admin_trend(days: int = Query(30, ge=7, le=90), _: str = Depends(require_admin)):
    return get_trend(days)

@app.get("/api/admin/responses")
async def admin_responses(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=5, le=100),
    search_id: Optional[str] = None, date_from: Optional[str] = None,
    date_to: Optional[str] = None, sort_by: str = "created_at", sort_dir: str = "desc",
    _: str = Depends(require_admin),
):
    return get_responses(page, per_page, search_id, date_from, date_to, sort_by, sort_dir)

@app.get("/api/admin/feedbacks")
async def admin_feedbacks(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=5, le=100),
    search: Optional[str] = None, date_from: Optional[str] = None,
    date_to: Optional[str] = None, _: str = Depends(require_admin),
):
    return get_feedbacks(page, per_page, search, date_from, date_to)

@app.get("/api/admin/health")
async def admin_health(_: str = Depends(require_admin)):
    return get_system_health()

@app.get("/api/admin/export/csv")
async def admin_export_csv(_: str = Depends(require_admin)):
    data = export_csv()
    return Response(
        content=data, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=survey_export.csv"},
    )

@app.get("/api/admin/export/excel")
async def admin_export_excel(_: str = Depends(require_admin)):
    data = export_excel()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=survey_report.xlsx"},
    )

@app.get("/api/admin/export/pdf")
async def admin_export_pdf(_: str = Depends(require_admin)):
    data = export_pdf()
    return Response(
        content=data, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=survey_report.pdf"},
    )

@app.post("/api/admin/backup")
async def admin_backup(_: str = Depends(require_admin)):
    result = create_backup()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "خطا در پشتیبان‌گیری"))
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
