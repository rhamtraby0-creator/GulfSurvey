import subprocess
import sys
import urllib.request
import urllib.error
import json
import re
import time
from pathlib import Path

ROOT = Path(".")
APP = ROOT / "backend/app.py"
DB = ROOT / "backend/database.py"
URL = "https://gulfsurvey-1.onrender.com"

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def stop(msg):
    print("\n❌", msg)
    sys.exit(1)

print("\n===== GULFSURVEY AUTO REPAIR =====")

# 1. Check files
for p in [APP, DB, ROOT / "backend/requirements.txt",
          ROOT / "frontend/js/survey.js"]:
    if not p.exists():
        stop(f"Missing file: {p}")
    print("OK:", p)

# 2. Python syntax
r = run([sys.executable, "-m", "py_compile",
         str(APP), str(DB)])
if r.returncode:
    stop("Python syntax error:\n" + r.stderr)
print("OK: Python syntax")

# 3. Inspect endpoint and schema
app = APP.read_text()
db = DB.read_text()

if '@app.post("/api/survey/submit")' not in app:
    stop("Survey endpoint not found")

if "CREATE TABLE IF NOT EXISTS responses" not in db:
    stop("Responses table definition not found")

if "def get_db" not in db:
    stop("Database connection function not found")

print("OK: Endpoint and database definitions found")

# 4. Check Git state
r = run(["git", "status", "--porcelain"])
if r.stdout.strip():
    stop("Uncommitted changes exist. No files were overwritten.")

# 5. Check diagnostic version
if "خطای داخلی ثبت:" not in app:
    stop("Diagnostic code is missing locally.")

print("OK: Diagnostic version exists locally")

# 6. Check server health
print("\nChecking server...")
try:
    req = urllib.request.Request(URL + "/api/health")
    with urllib.request.urlopen(req, timeout=60) as res:
        print("Health:", res.status, res.read().decode())
except Exception as e:
    stop("Server health failed: " + str(e))

# 7. Test endpoint with a unique token
payload = {
    f"q{i}": 4 for i in range(1, 12)
}
payload["feedback"] = "AUTOMATED DIAGNOSTIC TEST"

token = "AUTO-REPAIR-" + str(int(time.time()))

req = urllib.request.Request(
    URL + "/api/survey/submit",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "X-Client-Token": token
    },
    method="POST"
)

print("\nTesting real submission...")
try:
    with urllib.request.urlopen(req, timeout=90) as res:
        body = res.read().decode()
        print("HTTP:", res.status)
        print(body)
        if res.status == 200:
            print("\nSUCCESS: Survey submission works.")
            sys.exit(0)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print("HTTP:", e.code)
    print("Server response:", body)

    try:
        detail = json.loads(body).get("detail", "")
    except Exception:
        detail = body

    if "خطای داخلی ثبت:" in detail:
        print("\nACTUAL DATABASE ERROR:")
        print(detail)
        print("\nAutomatic safe repair is not possible without identifying this exact error.")
    else:
        print("\nThe deployed server is not returning the diagnostic version.")
        print("No database changes were made.")
except Exception as e:
    print("Request failed:", repr(e))

print("\n===== DIAGNOSIS FINISHED =====")
