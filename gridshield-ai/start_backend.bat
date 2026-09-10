@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM GridShield AI – Start Backend  (run from project root)
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0backend"

IF NOT EXIST .env (
    copy .env.example .env
    echo [INFO] Created .env from .env.example - edit it to add IBM_WATSONX_API_KEY
)

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
