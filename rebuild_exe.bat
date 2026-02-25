@echo off
cd /d "%~dp0"
echo Building mod_manager.exe ...
echo.

"C:\Program Files\Python314\python.exe" -m PyInstaller --onefile --windowed --name "mod_manager" --distpath "." --workpath "build" --specpath "build" "mod_manager.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Build failed. See output above.
    pause
    exit /b 1
)

rd /s /q "build" 2>nul

echo.
echo Done! mod_manager.exe has been rebuilt.
pause
