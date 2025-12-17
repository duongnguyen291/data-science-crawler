#!/bin/bash
# Setup script using uv for fast dependency installation
# Usage: bash setup.sh

set -e  # Exit on error

echo "=================================="
echo "🚀 SETUP DATA SCIENCE CRAWLER"
echo "=================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed!"
    echo ""
    echo "📦 Installing uv..."
    echo "   On macOS/Linux:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "   Or using pip:"
    echo "   pip install uv"
    echo ""
    echo "   Or using pipx:"
    echo "   pipx install uv"
    echo ""
    exit 1
fi

echo "✅ uv is installed: $(uv --version)"

# Create virtual environment
echo ""
echo "📁 Creating virtual environment..."
uv venv

# Get the venv path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    VENV_PATH=".venv/Scripts/activate"
else
    # macOS/Linux
    VENV_PATH=".venv/bin/activate"
fi

echo "✅ Virtual environment created at .venv/"

# Activate virtual environment and install dependencies
echo ""
echo "📦 Installing dependencies using uv..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # macOS/Linux
    source .venv/bin/activate
fi

# Install dependencies using uv
uv pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "=================================="
echo "📝 NEXT STEPS:"
echo "=================================="
echo ""
echo "1. Activate virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "   .venv\\Scripts\\activate"
else
    echo "   source .venv/bin/activate"
fi
echo ""
echo "2. Install Playwright browser (for Threads scraper):"
echo "   playwright install chromium"
echo ""
echo "3. Test crawlers:"
echo "   python test_twitter_crawler.py"
echo "   python test_scraper_quick.py"
echo ""
echo "4. Run crawlers:"
echo "   python twitter_entertainment_crawler.py"
echo "   python threads_scraper_complete.py"
echo "   python main.py"
echo ""
echo "=================================="

