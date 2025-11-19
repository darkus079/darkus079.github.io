@echo off
echo Installing dependencies for Telegram bot...
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Please create one first:
    echo python -m venv .venv
    echo call .venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)

echo Updating pip and build tools...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Installing dependencies with binary-only packages...
pip install --only-binary=all -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo Binary-only installation failed. Trying mixed installation...
    pip install -r requirements.txt
)

if %errorlevel% neq 0 (
    echo.
    echo Installation failed. Please check the error messages above.
    echo You may need to install Microsoft Visual C++ Build Tools.
    echo Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo You can now run the bot with: python src/bot.py
echo.
pause
