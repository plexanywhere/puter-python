@echo off
setlocal enabledelayedexpansion
chcp 936 >nul 2>&1 || chcp 65001 >nul 2>&1 || echo.

echo ========================================
echo   Puter Python Manager Cleanup Script
echo ========================================
echo.

REM Handle command line arguments
set AUTO_CONFIRM=0
set AUTO_DB=0
if "%~1"=="/y" (
    set AUTO_CONFIRM=1
    set AUTO_DB=0
) else if "%~1"=="/yd" (
    set AUTO_CONFIRM=1
    set AUTO_DB=1
)

REM Ask for confirmation unless auto-confirm
if !AUTO_CONFIRM! EQU 0 (
    set /p CONFIRM="This will clean temporary files and cache. Continue? (y/n): "
    if /i not "%CONFIRM%"=="y" (
        echo Operation cancelled
        pause
        exit /b 0
    )
) else (
    echo Auto-confirm enabled, proceeding...
)

echo Cleaning...

REM Clean Python cache
echo Cleaning Python cache files...
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "*.pyc" del /q "*.pyc" 2>nul
if exist "*.pyo" del /q "*.pyo" 2>nul
if exist "*.pyd" del /q "*.pyd" 2>nul
if exist ".pytest_cache" rmdir /s /q ".pytest_cache" 2>nul
if exist ".coverage" del /q ".coverage" 2>nul
if exist ".mypy_cache" rmdir /s /q ".mypy_cache" 2>nul

REM Clean backup and temporary files
echo Cleaning backup and temporary files...
del /q "run_backup.bat" 2>nul
del /q "run_old.bat" 2>nul
del /q "run_output.txt" 2>nul
del /q "setup_log_*.txt" 2>nul
del /q "setup_output.txt" 2>nul
del /q "output2.txt" 2>nul
del /q "setup_backup.bat" 2>nul
REM Remove old start.bat if it exists
if exist "start.bat" (
    echo Removing old start.bat...
    del /q "start.bat" 2>nul
)

REM Clean log files
echo Cleaning log files...
if exist "data\logs\*" (
    del /q "data\logs\*" 2>nul
    echo Log files cleaned
)

REM Clean cache directory
echo Cleaning cache directory...
if exist "data\cache\*" (
    del /q "data\cache\*" 2>nul
    echo Cache files cleaned
)

REM Clean Playwright browser cache
echo Cleaning Playwright browser cache...
if exist "%USERPROFILE%\AppData\Local\ms-playwright" (
    rmdir /s /q "%USERPROFILE%\AppData\Local\ms-playwright" 2>nul
    echo Playwright cache cleaned
)

REM Clean temporary files
echo Cleaning temporary files...
del /q "*.log" 2>nul
del /q "nohup.out" 2>nul
del /q "debug.log" 2>nul

REM Optional: clean database (be careful)
if !AUTO_CONFIRM! EQU 1 (
    REM Auto-confirm mode
    if !AUTO_DB! EQU 1 (
        echo.
        echo Auto-clean database enabled, deleting database...
        if exist "puter.db" (
            del "puter.db" 2>nul
            echo Database file deleted
        ) else (
            echo Database file does not exist
        )
    ) else (
        REM Auto-confirm but not cleaning database, skip this section
        echo.
        echo Skipping database cleanup (auto-confirm mode).
    )
) else (
    REM Interactive mode
    echo.
    set /p CLEAN_DB="Clean database? This will delete all account data! (y/n): "
    if /i "%CLEAN_DB%"=="y" (
        if exist "puter.db" (
            del "puter.db" 2>nul
            echo Database file deleted
        ) else (
            echo Database file does not exist
        )
    )
)

REM Clean empty directories
echo Cleaning empty directories...
for /d %%d in (*) do (
    dir "%%d" /b /a 2>nul | findstr . >nul || rmdir "%%d" 2>nul
)

echo.
echo ========================================
echo Cleanup completed!
echo.
echo Notes:
echo   - Configuration files and environment not deleted
echo   - Account folders and data directories preserved
echo   - For complete reset, delete entire project directory
echo ========================================
echo.

pause
exit /b 0