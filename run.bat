@echo off
echo ==========================================
echo SignAI - Initialization Script
echo ==========================================

echo [1/3] Checking dependencies...
pip install -r requirements.txt

echo [2/3] Checking Database...
if not exist signai.db (
    echo Initializing database...
    python database.py
)

echo [3/3] Starting SignAI Application Server...
start http://127.0.0.1:5500
python app.py

pause
