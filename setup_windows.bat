@echo off
setlocal
cd /d %~dp0

echo [1/4] Checking Python...
py -3 --version >nul 2>&1 || (echo Python 3 is required. Install it from python.org and enable Add Python to PATH.& pause & exit /b 1)

echo [2/4] Creating virtual environment...
if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [4/4] Creating local config/workspace...
if not exist .env copy /Y .env.example .env >nul
if not exist workspace mkdir workspace

echo.
echo Setup complete.
echo Edit .env and add DISCORD_TOKEN and OPENAI_API_KEY.
echo Then run start_agent.bat and start_worker.bat in two terminals.
pause
