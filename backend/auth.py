"""
Authentication and session management for admin panel.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, Request, Response, Depends
from fastapi.security import HTTPBearer

from database import get_db, log_event
from security import hash_password, verify_password, generate_token, generate_strong_password

SESSION_DURATION_HOURS = 8
BASE_LOCK_SECONDS = 5
security_scheme = HTTPBearer(auto_error=False)

def setup_initial_admin() -> Optional[str]:
    with get_db() as conn:
        row = conn.execute("SELECT password_hash FROM admin_settings WHERE id = 1").fetchone()
        if row:
            return None
        plain = generate_strong_password(28)
        hashed = hash_password(plain)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO admin_settings 
               (id, password_hash, created_at, last_password_change, failed_attempts, lock_until)
               VALUES (1, ?, ?, ?, 0, NULL)""",
            (hashed, now, now)
        )
        conn.execute(
            "INSERT INTO system_logs (event_type, message, created_at) VALUES (?, ?, ?)",
            ("admin_init", "Initial admin password generated", now)
        )
        return plain

def get_admin_settings(conn):
    return conn.execute("SELECT * FROM admin_settings WHERE id = 1").fetchone()

def is_locked(settings) -> Tuple[bool, int]:
    if not settings or not settings["lock_until"]:
        return False, 0
    lock_until = datetime.fromisoformat(settings["lock_until"])
    now = datetime.now(timezone.utc)
    if now < lock_until:
        return True, int((lock_until - now).total_seconds())
    return False, 0

def record_failed_login():
    with get_db() as conn:
        settings = get_admin_settings(conn)
        if not settings:
            return
        attempts = (settings["failed_attempts"] or 0) + 1
        lock_until = None
        if attempts >= 1:
            delay = min(BASE_LOCK_SECONDS * (2 ** (attempts - 1)), 900)
            lock_until = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
        conn.execute(
            "UPDATE admin_settings SET failed_attempts = ?, lock_until = ? WHERE id = 1",
            (attempts, lock_until)
        )
        log_event("login_failed", f"Attempt {attempts}")

def reset_failed_attempts():
    with get_db() as conn:
        conn.execute(
            "UPDATE admin_settings SET failed_attempts = 0, lock_until = NULL WHERE id = 1"
        )

def login(password: str) -> Tuple[bool, Optional[str], Optional[str], int]:
    with get_db() as conn:
        settings = get_admin_settings(conn)
        if not settings:
            return False, "سیستم هنوز راه‌اندازی نشده است", None, 0

        locked, wait = is_locked(settings)
        if locked:
            return False, f"به دلیل تلاش‌های ناموفق، لطفاً {wait} ثانیه صبر کنید", None, wait

        if not verify_password(password, settings["password_hash"]):
            attempts = int(settings["failed_attempts"] or 0) + 1
            delay = min(BASE_LOCK_SECONDS * (2 ** (attempts - 1)), 900)
            lock_until = (
                datetime.now(timezone.utc) + timedelta(seconds=delay)
            ).isoformat()

            conn.execute(
                "UPDATE admin_settings SET failed_attempts = ?, lock_until = ? WHERE id = 1",
                (attempts, lock_until)
            )

            conn.execute(
                "INSERT INTO system_logs (event_type, message, created_at) VALUES (?, ?, ?)",
                ("login_failed", f"Attempt {attempts}", datetime.now(timezone.utc).isoformat())
            )

            return False, "رمز عبور نادرست است", None, delay

        token = generate_token(32)
        expires = (
            datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
        ).isoformat()

        conn.execute(
            """UPDATE admin_settings
            SET session_token = ?, session_expires = ?,
                failed_attempts = 0, lock_until = NULL
            WHERE id = 1""",
            (token, expires)
        )

        conn.execute(
            "INSERT INTO system_logs (event_type, message, created_at) VALUES (?, ?, ?)",
            ("login_success", "Admin logged in", datetime.now(timezone.utc).isoformat())
        )

        return True, "ورود موفق", token, 0


def logout(token: str):
    with get_db() as conn:
        settings = get_admin_settings(conn)
        if settings and settings["session_token"] == token:
            conn.execute(
                "UPDATE admin_settings SET session_token = NULL, session_expires = NULL WHERE id = 1"
            )
            conn.execute(
                "INSERT INTO system_logs (event_type, message, created_at) VALUES (?, ?, ?)",
                ("logout", "Admin logged out", datetime.now(timezone.utc).isoformat())
            )


def validate_session(token: Optional[str]) -> bool:
    if not token:
        return False
    with get_db() as conn:
        settings = get_admin_settings(conn)
        if not settings or not settings["session_token"]:
            return False
        if settings["session_token"] != token:
            return False
        if not settings["session_expires"]:
            return False
        expires = datetime.fromisoformat(settings["session_expires"])
        if datetime.now(timezone.utc) > expires:
            conn.execute(
                "UPDATE admin_settings SET session_token = NULL, session_expires = NULL WHERE id = 1"
            )
            return False
        return True

def change_password(old_password: str, new_password: str) -> Tuple[bool, str]:
    if len(new_password) < 12:
        return False, "رمز جدید باید حداقل ۱۲ کاراکتر باشد"
    with get_db() as conn:
        settings = get_admin_settings(conn)
        if not settings:
            return False, "خطا در تنظیمات"
        if not verify_password(old_password, settings["password_hash"]):
            return False, "رمز فعلی نادرست است"
        new_hash = hash_password(new_password)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE admin_settings SET password_hash = ?, last_password_change = ?, session_token = NULL, session_expires = NULL WHERE id = 1",
            (new_hash, now)
        )
        log_event("password_changed", "Admin password updated")
        return True, "رمز عبور با موفقیت تغییر کرد. لطفاً دوباره وارد شوید."

async def require_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
    if not validate_session(token):
        raise HTTPException(status_code=401, detail="نشست نامعتبر یا منقضی شده است")
    return token
