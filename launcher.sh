#!/bin/bash
# AI Council Launcher Script
# Automatically sets up and launches the AI Council system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VENV_DIR="council_env"
BRAVE_API_KEY="BSA3KHYeLRPoIytYKYNJUj0qrYwKagp"

# Function to print colored messages
print_info() {
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found"
    
    # Check Ollama
    if ! command_exists ollama; then
        print_error "Ollama is not installed"
        print_info "Install with: curl -fsSL https://ollama.com/install.sh | sh"
        exit 1
    fi
    print_success "Ollama found"
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_warning "Ollama is not running, starting it..."
        sudo systemctl start ollama || ollama serve &
        sleep 3
    fi
    print_success "Ollama is running"
}

# Check and pull required models
check_models() {
    print_info "Checking AI models..."
    
    REQUIRED_MODELS=("llama3.2:3b" "qwen2.5:3b" "phi3.5:3.8b")
    MISSING_MODELS=()
    
    for model in "${REQUIRED_MODELS[@]}"; do
        if ! ollama list | grep -q "$model"; then
            MISSING_MODELS+=("$model")
        fi
    done
    
    if [ ${#MISSING_MODELS[@]} -ne 0 ]; then
        print_warning "Missing models: ${MISSING_MODELS[*]}"
        read -p "Download missing models? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for model in "${MISSING_MODELS[@]}"; do
                print_info "Downloading $model..."
                ollama pull "$model"
            done
        else
            print_error "Required models not available"
            exit 1
        fi
    fi
    
    print_success "All models ready"
}

# Setup Python virtual environment
setup_venv() {
    print_info "Setting up Python environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Install/upgrade dependencies
    print_info "Installing dependencies..."
    pip install --upgrade pip -q
    pip install aiohttp rich textual -q
    
    print_success "Dependencies installed"
}

# Check Docker for SearXNG (optional)
check_docker() {
    if command_exists docker; then
        if ! docker ps | grep -q searxng; then
            print_info "SearXNG not running. Using Brave API."
        else
            print_success "SearXNG is running"
        fi
    fi
}

# Main menu
show_menu() {
    clear
    echo "======================================"
    echo "     🤖 AI COUNCIL LAUNCHER 🤖"
    echo "======================================"
    echo ""
    echo "1) Launch Terminal UI (TUI)"
    echo "2) Launch Interactive CLI"
    echo "3) Quick Query (command line)"
    echo "4) Check System Status"
    echo "5) Download/Update Models"
    echo "6) Run Tests"
    echo "7) Exit"
    echo ""
    read -p "Select option [1-7]: " choice
}

# Launch TUI
launch_tui() {
    print_info "Launching Terminal UI..."
    source "$VENV_DIR/bin/activate"
    python3 ai_tui.py
}

# Launch interactive CLI
launch_cli() {
    print_info "Launching Interactive CLI..."
    source "$VENV_DIR/bin/activate"
    python3 ai_council.py -i
}

# Quick query
quick_query() {
    read -p "Enter your question: " query
    if [ -n "$query" ]; then
        print_info "Processing query..."
        source "$VENV_DIR/bin/activate"
        python3 ai_router.py "$query"
    fi
}

# System status
check_status() {
    print_info "System Status"
    echo "======================================"
    
    # Ollama status
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_success "Ollama: Running"
        echo "Models installed:"
        ollama list
    else
        print_error "Ollama: Not running"
    fi
    
    echo ""
    
    # Python environment
    if [ -d "$VENV_DIR" ]; then
        print_success "Python venv: Ready"
    else
        print_warning "Python venv: Not created"
    fi
    
    echo ""
    
    # Docker/SearXNG
    if command_exists docker && docker ps | grep -q searxng; then
        print_success "SearXNG: Running"
    else
        print_info "SearXNG: Not running (using Brave API)"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

# Download models
download_models() {
    print_info "Available model options:"
    echo "1) Essential (3B models) - ~6GB"
    echo "2) Complete (3B + 7B) - ~10GB"
    echo "3) Minimal (1B-2B only) - ~3GB"
    read -p "Select [1-3]: " model_choice
    
    case $model_choice in
        1)
            MODELS=("llama3.2:3b" "qwen2.5:3b" "phi3.5:3.8b")
            ;;
        2)
            MODELS=("llama3.2:3b" "qwen2.5:3b" "qwen2.5:7b" "phi3.5:3.8b")
            ;;
        3)
            MODELS=("llama3.2:1b" "qwen2.5:1.5b" "gemma2:2b")
            ;;
        *)
            print_error "Invalid choice"
            return
            ;;
    esac
    
    for model in "${MODELS[@]}"; do
        print_info "Pulling $model..."
        ollama pull "$model"
    done
    
    print_success "Models downloaded"
    read -p "Press Enter to continue..."
}

# Run tests
run_tests() {
    print_info "Running tests..."
    source "$VENV_DIR/bin/activate"
    
    # Test simple query
    print_info "Test 1: Simple query"
    echo "Testing: 'What is Python?'"
    python3 ai_router.py "What is Python?" --profile SIMPLE
    
    echo ""
    read -p "Press Enter to continue with more tests..."
    
    # Test code query
    print_info "Test 2: Code query"
    echo "Testing: 'Write a Python function to reverse a string'"
    python3 ai_router.py "Write a Python function to reverse a string" --profile CODE
    
    print_success "Tests complete"
    read -p "Press Enter to continue..."
}

# Main loop
main() {
    # Initial setup
    check_prerequisites
    check_models
    setup_venv
    check_docker
    
    # Main menu loop
    while true; do
        show_menu
        case $choice in
            1)
                launch_tui
                ;;
            2)
                launch_cli
                ;;
            3)
                quick_query
                read -p "Press Enter to continue..."
                ;;
            4)
                check_status
                ;;
            5)
                download_models
                ;;
            6)
                run_tests
                ;;
            7)
                print_info "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                sleep 1
                ;;
        esac
    done
}

# Run main
main