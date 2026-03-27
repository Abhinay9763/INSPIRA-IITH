#!/bin/bash

# AI Interview Preparation Platform - Stage 2 Startup Script
# This script sets up and starts the Stage 2 backend server

set -e

echo "🚀 AI Interview Preparation Platform - Stage 2"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
print_status "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION found"

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    print_error "This script must be run from the project root directory (where backend/ folder is located)"
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Dependencies installed"

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env file and add your FEATHERLESS_API_KEY before starting the server"
        echo ""
        echo "To edit the .env file:"
        echo "  nano .env"
        echo "  or"
        echo "  code .env"
        echo ""
        read -p "Press Enter after you've added your API key to .env..."
    else
        print_error ".env file not found and .env.example doesn't exist"
        print_error "Please create a .env file with FEATHERLESS_API_KEY=your_key_here"
        exit 1
    fi
else
    print_success ".env file found"
fi

# Check if FEATHERLESS_API_KEY is set
source .env
if [ -z "$FEATHERLESS_API_KEY" ] || [ "$FEATHERLESS_API_KEY" = "your_featherless_api_key_here" ]; then
    print_error "FEATHERLESS_API_KEY not set in .env file"
    print_error "Please edit .env and add your Featherless API key"
    exit 1
fi

print_success "FEATHERLESS_API_KEY is configured"

# Start the server
print_status "Starting the Stage 2 backend server..."
echo ""
echo "🌐 Server will be available at:"
echo "   • API: http://localhost:8000"
echo "   • Docs: http://localhost:8000/docs"
echo "   • Health: http://localhost:8000/health"
echo ""
echo "📖 To test the API, run in another terminal:"
echo "   python example_usage.py"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd backend
python main.py