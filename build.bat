@echo off
echo ========================================
echo Building TimerApp Executable...
echo ========================================
echo.

REM Clean previous build files
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist TimerApp.spec del /q TimerApp.spec
echo.

REM Build the executable
echo Building executable with PyInstaller...
pyinstaller --onefile --windowed --name "TimerApp" main.py
echo.

REM Check if build was successful
if exist dist\TimerApp.exe (
    echo ========================================
    echo Build Successful!
    echo ========================================
    echo.
    echo Executable location: dist\TimerApp.exe
    echo File size:
    dir dist\TimerApp.exe | find "TimerApp.exe"
    echo.
    echo You can now run: dist\TimerApp.exe
) else (
    echo ========================================
    echo Build Failed!
    echo ========================================
    echo Please check the error messages above.
)

echo.
pause
