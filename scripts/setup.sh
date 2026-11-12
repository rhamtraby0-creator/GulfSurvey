#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=============================================="
echo "  راه‌اندازی سامانه نظرسنجی"
echo "  پالایش گاز بیدبلند خلیج فارس"
echo "=============================================="
echo ""
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "▶ بررسی Python..."
if ! command -v python3 &>/dev/null; then
  echo "Python3 یافت نشد. در حال نصب..."
  if command -v pkg &>/dev/null; then
    pkg update -y
    pkg install -y python
  else
    echo "لطفاً Python 3 را نصب کنید."
    exit 1
  fi
fi
echo "▶ ایجاد محیط مجازی..."
python3 -m venv "$ROOT/.venv" 2>/dev/null || true
if [ -f "$ROOT/.venv/bin/activate" ]; then
  source "$ROOT/.venv/bin/activate"
fi
echo "▶ نصب وابستگی‌های Python..."
pip install --upgrade pip -q
pip install -r "$ROOT/backend/requirements.txt" -q
echo "▶ ایجاد پوشه داده..."
mkdir -p "$ROOT/data" "$ROOT/backups"
echo "▶ مقداردهی اولیه پایگاه داده و تولید رمز..."
cd "$ROOT/backend"
python3 -c "
from database import init_db
from auth import setup_initial_admin
init_db()
pwd = setup_initial_admin()
if pwd:
    print('')
    print('=' * 50)
    print('  رمز اولیه پنل مدیریت (فقط یک‌بار نمایش):')
    print('  ' + pwd)
    print('=' * 50)
    print('')
    print('این رمز را در جای امنی یادداشت کنید.')
    print('پس از اولین ورود می‌توانید آن را تغییر دهید.')
else:
    print('پایگاه داده از قبل مقداردهی شده است.')
"
echo ""
echo "✅ راه‌اندازی کامل شد."
echo ""
echo "برای اجرا:"
echo "  bash scripts/start.sh"
echo ""
