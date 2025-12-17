@echo off
REM Windows Batch Setup script using uv for fast dependency installation
REM Usage: setup.bat

echo ==================================
echo 🚀 SETUP DATA SCIENCE CRAWLER
echo ==================================
echo.

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ uv is not installed!
    echo.
    echo 📦 Installing uv...
    echo    Using pip:
    echo    pip install uv
    echo.
    echo    Or using pipx:
    echo    pipx install uv
    echo.
    echo    Or download from: https://github.com/astral-sh/uv
    echo.
    pause
    exit /b 1
)

echo ✅ uv is installed
echo.

REM Create virtual environment
echo 📁 Creating virtual environment...
uv venv

echo ✅ Virtual environment created at .venv\
echo.

REM Activate virtual environment and install dependencies
echo 📦 Installing dependencies using uv...
call .venv\Scripts\activate.bat

REM Install dependencies using uv
uv pip install -r requirements.txt

echo.
echo ✅ Dependencies installed successfully!
echo.
echo ==================================
echo 📝 NEXT STEPS:
echo ==================================
echo.
echo 1. Activate virtual environment:
echo    .venv\Scripts\activate.bat
echo.
echo 2. Install Playwright browser (for Threads scraper):
echo    playwright install chromium
echo.
echo 3. Test crawlers:
echo    python test_twitter_crawler.py
echo    python test_scraper_quick.py
echo.
echo 4. Run crawlers:
echo    python twitter_entertainment_crawler.py
echo    python threads_scraper_complete.py
echo    python main.py
echo.
echo ==================================
pause

