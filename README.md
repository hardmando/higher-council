# higher-council

A multi-AI deliberation system that routes queries to the best AI model or consults a council of models for complex questions.

## Features

- **Smart Routing** - Automatically selects the best AI profile for your query
- **AI Council** - Multiple models deliberate and a judge synthesizes the best answer
- **Chat History** - Save and resume conversations
- **Web Search** - Integrated real-time search with Brave API
- **Performance Optimized** - CPU-only mode prevents system freezing (if lacking VRAM)
- **Terminal UI** - TUI with rich formatting

## Quick Start

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download models
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
ollama pull phi3.5:3.8b

# 3. Clone and setup
git clone https://github.com/YOUR_USERNAME/ai-council.git
cd ai-council
chmod +x launcher.sh

# 4. Run
./launcher.sh
```

## AI Profiles

| Profile | Speed | Best For |
|---------|-------|----------|
| **SIMPLE** | ~5-8s | Quick facts, definitions |
| **CODE** | ~10-15s | Programming, debugging |
| **RESEARCH** | ~25-35s | Complex topics, multiple perspectives |
| **CREATIVE** | ~10-15s | Writing, brainstorming |
| **CURRENT** | ~30-40s | Recent events (with web search) |

## Usage

### Terminal UI (Recommended)
```bash
./launcher.sh  # Select option 1
```

### Interactive CLI
```bash
python ai_council.py -i
```

### Quick Query
```bash
python ai_router.py "your question here"
```

### With Specific Profile
```bash
python ai_router.py "your code question" --profile CODE
```

## Configuration

On first run, you'll be prompted to configure:
- Brave Search API key (optional, for web search)
- CPU thread count (defaults to optimal)
- Model preferences

Config stored in: `~/.config/ai-council/config.json`

**Example config:**
```json
{
  "api_keys": {
    "brave_search": "YOUR_API_KEY"
  },
  "ollama": {
    "num_gpu": 0,
    "num_threads": 6
  }
}
```

## Requirements

- Python 3.8+
- Ollama
- 16GB RAM (minimum)
- ~10GB disk space for models

## Architecture

```
Query → Router (Preprocessor) → Profile Selection
                                     ↓
                    ┌────────────────┴────────────────┐
                    ↓                                  ↓
              Single Model                      AI Council
              (SIMPLE/CODE/CREATIVE)           (3 models + Judge)
                    ↓                                  ↓
                 Answer                        Synthesized Answer
```

## Keyboard Shortcuts (TUI)

- `Enter` - Send message
- `Ctrl+Q` - Quit
- `Ctrl+C` - Clear chat
- `Ctrl+S` - Toggle web search

## Commands

```bash
# Setup
python config.py setup          # Configure settings
python config.py optimize       # Optimize performance

# Chat management
python chat_manager.py list     # List saved chats
python chat_manager.py show <id>  # View chat
python chat_manager.py export <id> markdown  # Export chat

# System
./launcher.sh                   # Main menu
python speed_test.py            # Performance test
```

## Troubleshooting

### System Freezing
GPU usage can cause freezes on some systems. This is fixed by using CPU-only mode (default).

To verify:
```bash
python config.py verify
```

### Slow Performance
```bash
# Optimize Ollama
python config.py optimize
sudo systemctl restart ollama
```

### Models Not Found
```bash
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
ollama pull phi3.5:3.8b
```

## Performance Tips

- Use **SIMPLE** for quick queries
- **CODE** profile has specialized models
- **RESEARCH** is thorough but slow (3-4 models)
- Disable web search when not needed: `--no-search`
- Pre-load models: `ollama run llama3.2:3b "warmup"`

## Project Structure

```
ai-council/
├── ai_council.py       # Council system with judge
├── ai_router.py        # Smart query router
├── ai_tui.py          # Terminal UI
├── config.py          # Configuration manager
├── chat_manager.py    # Chat history & persistence
├── launcher.sh        # Main launcher script
└── config.example.json # Config template
```

## Contributing

Issues and pull requests welcome!

## License

MIT License

## Credits

Built with:
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Textual](https://textual.textualize.io/) - Terminal UI
- [Brave Search API](https://brave.com/search/api/) - Web search

---

**Note:** Keep your `config.json` private! It contains API keys. Never commit it to git (protected by `.gitignore`).
