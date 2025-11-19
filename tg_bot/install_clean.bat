@echo off
echo Installing dependencies in clean virtual environment...
echo.

REM Activate virtual environment
call venv_clean\Scripts\activate.bat

REM Upgrade pip and tools
python -m pip install --upgrade pip setuptools wheel

REM Install dependencies
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo Installation failed. Trying alternative approach...
    echo.

    REM Try installing without strict versions
    pip install --upgrade pydantic pydantic-settings
    pip install aiogram httpx python-dotenv loguru aiolimiter tenacity ujson selenium webdriver-manager beautifulsoup4 undetected-chromedriver setuptools

    if %errorlevel% neq 0 (
        echo.
        echo All installation methods failed.
        echo Please check the error messages above.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Dependencies installed successfully!
echo You can now run the bot with: python src/bot.py
echo.
pause
