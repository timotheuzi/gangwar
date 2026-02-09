@echo off
REM Windows batch script for running Gangwar executable

echo Gangwar Game Launcher
echo =====================
echo.

REM Kill any existing instances of gangwar
echo Checking for existing gangwar instances...
tasklist /FI "IMAGENAME eq gangwar.exe" 2>NUL | find /I /N "gangwar.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Killing existing gangwar instances...
    taskkill /F /IM gangwar.exe 2>NUL
    timeout /t 2 /nobreak >nul
)

REM Try to run the executable
if exist "gangwar.exe" (
    echo Found executable: gangwar.exe
    echo Running Gangwar executable...
    start "" gangwar.exe
    goto :eof
)

if exist "gangwar" (
    echo Found executable: gangwar
    echo Running Gangwar executable...
    start "" gangwar
    goto :eof
)

REM Fallback to Python
echo No executable found in current directory.
echo Falling back to Python...

REM Check if we're in the dist directory and need to go up
if exist "..\src\app.py" (
    echo Changing to parent directory...
    cd ..
)

REM Check if app.py exists
if not exist "src\app.py" (
    echo Error: src\app.py not found!
    echo Please ensure you're running this from the correct directory.
    pause
    exit /b 1
)

REM Find Python executable
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD=python3
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Python not found!
        echo Please install Python and try again.
        pause
        exit /b 1
    )
)

echo Using Python: %PYTHON_CMD%

REM Check if requirements are installed
%PYTHON_CMD% -c "import flask, flask_socketio" >nul 2>&1
if errorlevel 1 (
    echo Installing required dependencies...
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo Failed to install dependencies. Please install manually:
        echo %PYTHON_CMD% -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo Starting Gangwar with Python...
%PYTHON_CMD% app.py
