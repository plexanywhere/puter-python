@echo off
chcp 936 >nul 2>&1 || chcp 65001 >nul 2>&1 || echo.

echo ========================================
echo   Puter Python Manager Setup Script
echo ========================================
echo.

REM Check Python installation
echo [Step 1] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8 or later.
    echo [Download] https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>nul') do set PYTHON_VERSION=%%i
echo [OK] Python version: %PYTHON_VERSION%
echo.

REM Check virtual environment
echo [Step 2] Checking virtual environment...
if exist "venv\Scripts\python.exe" (
    echo [OK] Virtual environment exists.
    set VENV_EXISTS=1
) else (
    echo [INFO] Virtual environment not found, creating...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo Possible reasons:
        echo   1. Python installation incomplete
        echo   2. Insufficient permissions
        echo   3. Missing venv module
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
    set VENV_EXISTS=1
)

REM Use virtual environment Python and pip
set VENV_PYTHON=venv\Scripts\python.exe
set VENV_PIP=venv\Scripts\pip.exe

REM Upgrade pip
echo [Step 3] Upgrading pip...
%VENV_PYTHON% -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo [WARN] Pip upgrade failed, continuing...
)

REM Install dependencies
echo [Step 4] Installing dependencies...
if exist "requirements.txt" (
    echo [INFO] Installing from requirements.txt...
    %VENV_PIP% install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Some dependencies may have failed to install.
    )
) else (
    echo [ERROR] requirements.txt not found.
    pause
    exit /b 1
)

REM Verify critical dependencies
echo [Step 5] Verifying critical dependencies...
%VENV_PYTHON% -c "import fastapi, sqlalchemy, playwright" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Critical dependencies missing.
    echo Attempting to install missing packages...
    %VENV_PIP% install fastapi sqlalchemy playwright
)

REM Install Playwright browser
echo [Step 6] Installing Playwright browser...
%VENV_PYTHON% -m playwright install chromium >nul 2>&1
if errorlevel 1 (
    echo [WARN] Playwright browser installation failed.
    echo Will try to use system browser.
)

REM Create data directories
echo [Step 7] Creating data directories...
if not exist "data" mkdir data
if not exist "data\accounts" mkdir data\accounts
if not exist "data\logs" mkdir data\logs
if not exist "data\cache" mkdir data\cache
if not exist "static" mkdir static

REM Check essential files
echo [Step 8] Checking essential files...
set MISSING=0
if not exist "app.py" (
    echo [ERROR] app.py not found - main application file.
    set MISSING=1
)
if not exist "config.py" (
    echo [ERROR] config.py not found - configuration file.
    set MISSING=1
)
if %MISSING% EQU 1 (
    echo [ERROR] Missing essential files, cannot proceed.
    pause
    exit /b 1
)

REM Initialize database
echo [Step 9] Initializing database...
%VENV_PYTHON% -c "from database import create_tables; create_tables()" >nul 2>&1 && echo [OK] Database initialized successfully. || echo [ERROR] Database initialization failed.

echo.
echo ========================================
echo [SUCCESS] Setup completed!
echo.
echo [INFO] To start the service:
echo   1. Run run.bat
echo   2. Visit http://127.0.0.1:8000
echo   3. Press Ctrl+C to stop
echo.
echo [COMMANDS]
echo   - run.bat      Start service
echo   - setup.bat    Reconfigure environment
echo   - cleanup.bat  Clean temporary files
echo ========================================
echo.

set /p START_NOW="Start service now? (y/n): "
if /i "%START_NOW%"=="y" (
    echo [INFO] Starting service...
    call run.bat
) else (
    echo [INFO] You can start the service anytime by running run.bat
    pause
)

exit /b 0