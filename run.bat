@echo off
chcp 936 >nul 2>&1 || chcp 65001 >nul 2>&1 || echo.

echo ========================================
echo   Puter Python Manager Startup Script
echo ========================================
echo.

REM Set variables
set SCRIPT_NAME=%~n0
set ARG1=%~1

REM Show help
if "%ARG1%"=="help" (
    echo Usage:
    echo   %SCRIPT_NAME%          Start service
    echo   %SCRIPT_NAME% setup    Configure environment
    echo   %SCRIPT_NAME% clean    Clean files
    echo   %SCRIPT_NAME% update   Update dependencies
    echo   %SCRIPT_NAME% help     Show this help
    echo.
    echo Quick start:
    echo   1. First run: %SCRIPT_NAME% setup
    echo   2. Start service: %SCRIPT_NAME%
    echo   3. Visit http://127.0.0.1:8000
    exit /b 0
)

REM Handle arguments
if "%ARG1%"=="setup" (
    echo Running environment configuration...
    call setup.bat
    exit /b 0
)

if "%ARG1%"=="clean" (
    echo Running cleanup script...
    call cleanup.bat
    exit /b 0
)

if "%ARG1%"=="update" (
    echo Updating dependencies...
    call :UPDATE_DEPS
    exit /b 0
)

if not "%ARG1%"=="" (
    echo Unknown parameter: %ARG1%
    echo Use %SCRIPT_NAME% help for help
    pause
    exit /b 1
)

REM Main startup logic
echo Checking system environment...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found
    echo Please install Python 3.8+ or run %SCRIPT_NAME% setup
    pause
    exit /b 1
)

REM Check virtual environment
set VENV_PYTHON=venv\Scripts\python.exe
set VENV_PIP=venv\Scripts\pip.exe

if not exist "%VENV_PYTHON%" (
    echo Virtual environment not found
    goto :SETUP_ENV
)

REM Check critical dependencies using virtual environment Python
echo Checking critical dependencies...
%VENV_PYTHON% -c "import fastapi, sqlalchemy, playwright, httpx" >nul 2>&1
if errorlevel 1 (
    echo Missing critical dependencies
    call :INSTALL_DEPS
)

REM Playwright browser check removed (using Puter.js SDK instead)
REM echo Checking Playwright browser...
REM %VENV_PYTHON% -m playwright install chromium

REM Clean Python cache (optional)
echo Cleaning temporary cache...
if exist "__pycache__" rmdir /s /q "__pycache__" 2>nul
if exist "*.pyc" del /q "*.pyc" 2>nul

REM Start service
echo.
echo ========================================
echo Starting Puter Python Manager
echo ========================================
echo Service URL: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo Admin Interface: http://127.0.0.1:8000/static/index.html
echo Data Directory: %CD%\data
echo Start Time: %date% %time%
echo ========================================
echo.
echo Press Ctrl+C to stop service
echo.

REM Run application using virtual environment Python
echo Opening browser in 2 seconds...
ping -n 3 127.0.0.1 >nul
start http://127.0.0.1:8000
%VENV_PYTHON% app.py

REM If service exits abnormally
echo.
echo Service stopped
echo Possible configuration issue, try running %SCRIPT_NAME% setup
pause
exit /b 1

REM ====== Subroutines ======

:SETUP_ENV
echo Environment not ready, starting auto-configuration...
set /p AUTO_SETUP="Automatically configure environment? (y/n): "
if /i "%AUTO_SETUP%"=="y" (
    call setup.bat
    echo Configuration complete, restarting...
    call %SCRIPT_NAME%
    exit /b 0
) else (
    echo Please manually run %SCRIPT_NAME% setup
    pause
    exit /b 1
)

:INSTALL_DEPS
echo Installing dependencies...
if exist "requirements.txt" (
    echo Installing from requirements.txt...
    %VENV_PIP% install -r requirements.txt
    if errorlevel 1 (
        echo Installation failed, trying to upgrade pip...
        %VENV_PYTHON% -m pip install --upgrade pip
        %VENV_PIP% install -r requirements.txt
    )
) else (
    echo requirements.txt not found
    goto :SETUP_ENV
)
echo Dependencies installed
exit /b 0

:UPDATE_DEPS
echo Updating dependencies...
if exist "%VENV_PIP%" (
    echo Updating dependencies...
    %VENV_PIP% install --upgrade -r requirements.txt
    echo Dependencies updated
) else (
    echo Virtual environment not found
    goto :SETUP_ENV
)

echo Updating Playwright browser...
%VENV_PYTHON% -m playwright install --upgrade chromium
echo Update complete
exit /b 0