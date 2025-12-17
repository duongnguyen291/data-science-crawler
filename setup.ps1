# PowerShell Setup script using uv for fast dependency installation
# Usage: .\setup.ps1

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "🚀 SETUP DATA SCIENCE CRAWLER" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Check if uv is installed
try {
    $uvVersion = uv --version
    Write-Host "✅ uv is installed: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ uv is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "📦 Installing uv..." -ForegroundColor Yellow
    Write-Host "   Using pip:"
    Write-Host "   pip install uv"
    Write-Host ""
    Write-Host "   Or using pipx:"
    Write-Host "   pipx install uv"
    Write-Host ""
    Write-Host "   Or download from: https://github.com/astral-sh/uv"
    Write-Host ""
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "📁 Creating virtual environment..." -ForegroundColor Yellow
uv venv

Write-Host "✅ Virtual environment created at .venv\" -ForegroundColor Green

# Activate virtual environment and install dependencies
Write-Host ""
Write-Host "📦 Installing dependencies using uv..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Install dependencies using uv
uv pip install -r requirements.txt

Write-Host ""
Write-Host "✅ Dependencies installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "📝 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Activate virtual environment:"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "2. Install Playwright browser (for Threads scraper):"
Write-Host "   playwright install chromium"
Write-Host ""
Write-Host "3. Test crawlers:"
Write-Host "   python test_twitter_crawler.py"
Write-Host "   python test_scraper_quick.py"
Write-Host ""
Write-Host "4. Run crawlers:"
Write-Host "   python twitter_entertainment_crawler.py"
Write-Host "   python threads_scraper_complete.py"
Write-Host "   python main.py"
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan

