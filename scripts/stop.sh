#!/data/data/com.termux/files/usr/bin/bash
echo "▶ توقف سرویس..."
pkill -f "uvicorn app:app" 2>/dev/null || true
pkill -f "python3 -m uvicorn" 2>/dev/null || true
sleep 1
if pgrep -f "uvicorn app:app" >/dev/null; then
  echo "در حال اجبار به توقف..."
  pkill -9 -f "uvicorn app:app" 2>/dev/null || true
fi
echo "✅ سرویس متوقف شد."
