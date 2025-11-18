#!/bin/bash
# AI Council Launcher Script v2.0
# Now with config management, chat history, and performance optimization

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
VENV_DIR="council_env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/ai-council"
DATA_DIR="$HOME/.local/share/ai-council"

# Print functions
print_header() {
    clear
    echo -e "${CYAN}"
    echo "======================================"
    echo "     🤖 AI COUNCIL v2.0 🤖"
    echo "======================================"
    echo -e "${NC}"
}

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

# Check if command exists
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
    print_success "Python 3 found: $(python3 --version)"
    
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
        if systemctl is-active --quiet ollama 2>/dev/null; then
            sudo systemctl start ollama
        else
            ollama serve &
            sleep 3
        fi
    fi
    print_success "Ollama is running"
    
    echo ""
}

# Check configuration
check_config() {
    print_info "Checking configuration..."
    
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        print_warning "Configuration not found!"
        print_info "Running setup wizard..."
        echo ""
        python3 config.py setup
        echo ""
    else
        print_success "Configuration found"
    fi
}

# Check data directories
check_directories() {
    print_info "Checking data directories..."
    
    mkdir -p "$DATA_DIR/chats"
    mkdir -p "$DATA_DIR/attachments"
    
    print_success "Data directories ready"
    echo "  - Chats: $DATA_DIR/chats"
    echo "  - Attachments: $DATA_DIR/attachments"
    echo ""
}

# Check and pull required models
check_models() {
    print_info "Checking AI models..."
    
    # Read models from config if exists
    if [ -f "$CONFIG_DIR/config.json" ]; then
        REQUIRED_MODELS=$(python3 -c "
import json
try:
    with open('$CONFIG_DIR/config.json') as f:
        config = json.load(f)
        models = [config['models']['preprocessor'], config['models']['simple'], config['models']['code']]
        models.extend(config['models']['council'])
        print(' '.join(set(models)))
except:
    print('llama3.2:3b qwen2.5:3b phi3.5:3.8b')
" 2>/dev/null || echo "llama3.2:3b qwen2.5:3b phi3.5:3.8b")
    else
        REQUIRED_MODELS="llama3.2:3b qwen2.5:3b phi3.5:3.8b"
    fi
    
    MISSING_MODELS=()
    
    for model in $REQUIRED_MODELS; do
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
    echo ""
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
    echo ""
}

# Performance check and optimization
check_performance() {
    print_info "Checking performance configuration..."
    
    if [ -f "/etc/systemd/system/ollama.service.d/override.conf" ]; then
        print_success "Ollama optimized"
        
        # Show current settings
        if grep -q "OLLAMA_NUM_THREAD" /etc/systemd/system/ollama.service.d/override.conf; then
            THREADS=$(grep "OLLAMA_NUM_THREAD" /etc/systemd/system/ollama.service.d/override.conf | cut -d'=' -f2 | tr -d '"')
            echo "  CPU Threads: $THREADS"
        fi
    else
        print_warning "Ollama not optimized for performance"
        echo "  Run 'Optimize Performance' from menu"
    fi
    echo ""
}

# Main menu
show_menu() {
    print_header
    
    # Show system status
    echo -e "${CYAN}System Status:${NC}"
    
    # Ollama
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "  Ollama:  ${GREEN}●${NC} Running"
    else
        echo -e "  Ollama:  ${RED}●${NC} Not running"
    fi
    
    # Config
    if [ -f "$CONFIG_DIR/config.json" ]; then
        echo -e "  Config:  ${GREEN}●${NC} Ready"
    else
        echo -e "  Config:  ${YELLOW}●${NC} Needs setup"
    fi
    
    # Chats
    CHAT_COUNT=$(ls -1 "$DATA_DIR/chats" 2>/dev/null | wc -l)
    echo -e "  Chats:   ${GREEN}●${NC} $CHAT_COUNT saved"
    
    echo ""
    echo -e "${CYAN}Main Menu:${NC}"
    echo ""
    echo "  1) 🖥️  Launch Terminal UI (TUI)"
    echo "  2) 💬 Launch Interactive Council"
    echo "  3) 🎯 Quick Query (Router)"
    echo "  4) ⚡ Optimize Performance"
    echo ""
    echo "  5) 📚 Manage Chats"
    echo "  6) ⚙️  Configuration"
    echo "  7) 🔧 System Status"
    echo "  8) 📦 Manage Models"
    echo "  9) 🧪 Run Tests"
    echo ""
    echo "  0) 🚪 Exit"
    echo ""
    read -p "Select option [0-9]: " choice
}

# Launch TUI
launch_tui() {
    print_info "Launching Terminal UI..."
    source "$VENV_DIR/bin/activate"
    python3 ai_tui.py
}

# Launch interactive CLI
launch_cli() {
    print_info "Launching Interactive Council..."
    source "$VENV_DIR/bin/activate"
    python3 ai_council.py -i --show-timing
}

# Quick query
quick_query() {
    read -p "Enter your question: " query
    if [ -n "$query" ]; then
        print_info "Processing query..."
        source "$VENV_DIR/bin/activate"
        python3 ai_router.py "$query" --time
    fi
    read -p "Press Enter to continue..."
}

# Optimize performance
optimize_performance() {
    print_info "Running performance optimization..."
    echo ""
    
    python3 config.py optimize
    
    echo ""
    print_success "Optimization complete!"
    print_info "Restart Ollama for changes to take effect"
    
    read -p "Restart Ollama now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl restart ollama
        print_success "Ollama restarted"
    fi
    
    read -p "Press Enter to continue..."
}

# Manage chats
manage_chats() {
    while true; do
        print_header
        echo -e "${CYAN}Chat Management${NC}"
        echo ""
        echo "  1) List all chats"
        echo "  2) View chat"
        echo "  3) Export chat"
        echo "  4) Delete chat"
        echo "  5) Export all chats"
        echo "  0) Back to main menu"
        echo ""
        read -p "Select option: " chat_choice
        
        case $chat_choice in
            1)
                python3 chat_manager.py list
                read -p "Press Enter to continue..."
                ;;
            2)
                read -p "Enter chat ID: " chat_id
                python3 chat_manager.py show "$chat_id" | less
                ;;
            3)
                read -p "Enter chat ID: " chat_id
                read -p "Format (markdown/json/txt) [markdown]: " format
                format=${format:-markdown}
                
                output_file="chat_${chat_id}.${format}"
                python3 chat_manager.py export "$chat_id" "$format" > "$output_file"
                print_success "Exported to: $output_file"
                read -p "Press Enter to continue..."
                ;;
            4)
                read -p "Enter chat ID: " chat_id
                read -p "Are you sure? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    python3 chat_manager.py delete "$chat_id"
                    print_success "Chat deleted"
                fi
                read -p "Press Enter to continue..."
                ;;
            5)
                export_dir="$HOME/ai-council-exports"
                mkdir -p "$export_dir"
                
                print_info "Exporting all chats to: $export_dir"
                
                python3 -c "
from chat_manager import ChatManager
cm = ChatManager()
chats = cm.list_chats()
for chat in chats:
    content = cm.export_chat(chat['chat_id'], 'markdown')
    with open('$export_dir/chat_' + chat['chat_id'] + '.md', 'w') as f:
        f.write(content)
    print(f\"Exported: {chat['title']}\")
"
                print_success "All chats exported to: $export_dir"
                read -p "Press Enter to continue..."
                ;;
            0)
                break
                ;;
        esac
    done
}

# Configuration menu
config_menu() {
    while true; do
        print_header
        echo -e "${CYAN}Configuration${NC}"
        echo ""
        echo "  1) Run setup wizard"
        echo "  2) Show current config"
        echo "  3) Edit config file"
        echo "  4) Reset to defaults"
        echo "  0) Back to main menu"
        echo ""
        read -p "Select option: " config_choice
        
        case $config_choice in
            1)
                python3 config.py setup
                read -p "Press Enter to continue..."
                ;;
            2)
                python3 config.py show | less
                ;;
            3)
                ${EDITOR:-nano} "$CONFIG_DIR/config.json"
                ;;
            4)
                read -p "Reset config to defaults? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    rm -f "$CONFIG_DIR/config.json"
                    python3 config.py setup
                fi
                read -p "Press Enter to continue..."
                ;;
            0)
                break
                ;;
        esac
    done
}

# System status
system_status() {
    print_header
    echo -e "${CYAN}System Status${NC}"
    echo "======================================"
    echo ""
    
    # Ollama status
    echo -e "${BLUE}Ollama Service:${NC}"
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_success "Running"
        echo ""
        echo "Installed models:"
        ollama list
    else
        print_error "Not running"
        echo "Start with: sudo systemctl start ollama"
    fi
    
    echo ""
    
    # Python environment
    echo -e "${BLUE}Python Environment:${NC}"
    if [ -d "$VENV_DIR" ]; then
        print_success "Virtual environment ready"
        source "$VENV_DIR/bin/activate"
        echo "Python: $(python3 --version)"
        echo "Packages:"
        pip list | grep -E "(aiohttp|rich|textual)" || echo "  (none installed)"
        deactivate
    else
        print_warning "Virtual environment not created"
    fi
    
    echo ""
    
    # Configuration
    echo -e "${BLUE}Configuration:${NC}"
    if [ -f "$CONFIG_DIR/config.json" ]; then
        print_success "Config file exists"
        echo "Location: $CONFIG_DIR/config.json"
        
        # Check for API key
        if grep -q '"brave_search": ""' "$CONFIG_DIR/config.json"; then
            print_warning "Brave API key not set"
        else
            print_success "Brave API key configured"
        fi
    else
        print_warning "Config file not found"
    fi
    
    echo ""
    
    # Data directories
    echo -e "${BLUE}Data Storage:${NC}"
    echo "Chats: $DATA_DIR/chats"
    CHAT_COUNT=$(ls -1 "$DATA_DIR/chats" 2>/dev/null | wc -l)
    echo "  Saved chats: $CHAT_COUNT"
    
    echo "Attachments: $DATA_DIR/attachments"
    ATTACH_COUNT=$(find "$DATA_DIR/attachments" -type f 2>/dev/null | wc -l)
    echo "  Stored files: $ATTACH_COUNT"
    
    echo ""
    
    # Performance settings
    echo -e "${BLUE}Performance:${NC}"
    if [ -f "/etc/systemd/system/ollama.service.d/override.conf" ]; then
        print_success "Ollama optimized"
        cat /etc/systemd/system/ollama.service.d/override.conf
    else
        print_warning "Ollama not optimized"
        echo "  Run option 4 from main menu to optimize"
    fi
    
    echo ""
    echo "======================================"
    read -p "Press Enter to continue..."
}

# Manage models
manage_models() {
    while true; do
        print_header
        echo -e "${CYAN}Model Management${NC}"
        echo ""
        echo "  1) List installed models"
        echo "  2) Download model"
        echo "  3) Remove model"
        echo "  4) Download recommended set"
        echo "  5) Update all models"
        echo "  0) Back to main menu"
        echo ""
        read -p "Select option: " model_choice
        
        case $model_choice in
            1)
                ollama list
                read -p "Press Enter to continue..."
                ;;
            2)
                read -p "Enter model name (e.g., llama3.2:3b): " model_name
                ollama pull "$model_name"
                read -p "Press Enter to continue..."
                ;;
            3)
                read -p "Enter model name to remove: " model_name
                read -p "Are you sure? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    ollama rm "$model_name"
                fi
                read -p "Press Enter to continue..."
                ;;
            4)
                print_info "Downloading recommended models..."
                MODELS=("llama3.2:3b" "qwen2.5:3b" "phi3.5:3.8b" "qwen2.5:7b")
                for model in "${MODELS[@]}"; do
                    print_info "Pulling $model..."
                    ollama pull "$model"
                done
                print_success "All recommended models downloaded"
                read -p "Press Enter to continue..."
                ;;
            5)
                print_info "Updating all models..."
                ollama list | tail -n +2 | awk '{print $1}' | while read model; do
                    print_info "Updating $model..."
                    ollama pull "$model"
                done
                print_success "All models updated"
                read -p "Press Enter to continue..."
                ;;
            0)
                break
                ;;
        esac
    done
}

# Run tests
run_tests() {
    print_header
    echo -e "${CYAN}Running Tests${NC}"
    echo "======================================"
    echo ""
    
    source "$VENV_DIR/bin/activate"
    
    # Test 1: Config
    print_info "Test 1: Configuration"
    if python3 config.py show >/dev/null 2>&1; then
        print_success "Config OK"
    else
        print_error "Config failed"
    fi
    echo ""
    
    # Test 2: Chat manager
    print_info "Test 2: Chat Manager"
    if python3 chat_manager.py list >/dev/null 2>&1; then
        print_success "Chat manager OK"
    else
        print_error "Chat manager failed"
    fi
    echo ""
    
    # Test 3: Simple query
    print_info "Test 3: Simple Query"
    echo "Query: 'What is 2+2?'"
    time python3 ai_router.py "What is 2+2?" --profile SIMPLE --no-preprocess
    echo ""
    
    # Test 4: Performance
    print_info "Test 4: Performance Benchmark"
    echo "Running 3 queries to measure average time..."
    
    total_time=0
    for i in {1..3}; do
        start=$(date +%s.%N)
        python3 ai_router.py "test $i" --profile SIMPLE --no-preprocess >/dev/null 2>&1
        end=$(date +%s.%N)
        elapsed=$(echo "$end - $start" | bc)
        total_time=$(echo "$total_time + $elapsed" | bc)
        echo "  Query $i: ${elapsed}s"
    done
    
    avg_time=$(echo "scale=2; $total_time / 3" | bc)
    echo ""
    print_success "Average time: ${avg_time}s"
    
    if (( $(echo "$avg_time < 10" | bc -l) )); then
        print_success "Performance: Excellent"
    elif (( $(echo "$avg_time < 20" | bc -l) )); then
        print_success "Performance: Good"
    else
        print_warning "Performance: Consider optimization"
    fi
    
    echo ""
    echo "======================================"
    read -p "Press Enter to continue..."
}

# Main loop
main() {
    # Initial setup
    check_prerequisites
    check_config
    check_directories
    check_models
    setup_venv
    check_performance
    
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
                ;;
            4)
                optimize_performance
                ;;
            5)
                manage_chats
                ;;
            6)
                config_menu
                ;;
            7)
                system_status
                ;;
            8)
                manage_models
                ;;
            9)
                run_tests
                ;;
            0)
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
