"""
Security utilities: password hashing, rate limiting, etc.
"""

import secrets
import hmac
from datetime import datetime, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def generate_strong_password(length: int = 28) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def generate_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)

def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())

_rate_store = {}

def check_rate_limit(key: str, max_attempts: int = 5, window_seconds: int = 300) -> tuple:
    now = datetime.now(timezone.utc)
    if key not in _rate_store:
        _rate_store[key] = []
    _rate_store[key] = [t for t in _rate_store[key] if (now - t).total_seconds() < window_seconds]
    if len(_rate_store[key]) >= max_attempts:
        oldest = _rate_store[key][0]
        wait = int(window_seconds - (now - oldest).total_seconds())
        return False, max(wait, 1)
    return True, 0

def record_attempt(key: str):
    now = datetime.now(timezone.utc)
    if key not in _rate_store:
        _rate_store[key] = []
    _rate_store[key].append(now)

def clear_attempts(key: str):
    _rate_store.pop(key, None)
