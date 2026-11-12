#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
if [ -f "$ROOT/.venv/bin/activate" ]; then
  source "$ROOT/.venv/bin/activate"
fi
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '$ROOT/backend')
from database import init_db, DB_PATH
init_db()
print('DB ready at', DB_PATH)
" 2>/dev/null || true
echo "▶ راه‌اندازی سرور روی پورت 8000..."
echo "  آدرس نظرسنجی:  http://127.0.0.1:8000/"
echo "  آدرس پنل مدیریت: http://127.0.0.1:8000/admin"
echo ""
echo "برای توقف: Ctrl+C یا bash scripts/stop.sh"
echo ""
cd "$ROOT/backend"
exec python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info
