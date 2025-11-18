"""
Configuration management for AI Council
Keeps API keys and settings separate from code
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

class Config:
    """Manages configuration and API keys"""
    
    def __init__(self, config_dir: str = "~/.config/ai-council"):
        self.config_dir = Path(config_dir).expanduser()
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Create default config
            default_config = {
                "api_keys": {
                    "brave_search": "",
                    "openai": "",  # For future use
                },
                "ollama": {
                    "url": "http://localhost:11434",
                    "num_threads": 0,  # 0 = auto-detect
                    "num_gpu": -1,  # -1 = auto, 0 = CPU only, >0 = specific GPU layers
                },
                "models": {
                    "preprocessor": "llama3.2:3b",
                    "simple": "llama3.2:3b",
                    "code": "qwen2.5:7b",
                    "creative": "llama3.2:3b",
                    "council": ["llama3.2:3b", "phi3.5:3.8b", "qwen2.5:3b"],
                    "judge": "llama3.2:3b"
                },
                "search": {
                    "enabled": True,
                    "default_results": 5
                },
                "performance": {
                    "cpu_threads": 0,  # 0 = auto
                    "context_length": 2048,
                    "batch_size": 512
                },
                "storage": {
                    "chats_dir": "~/.local/share/ai-council/chats",
                    "attachments_dir": "~/.local/share/ai-council/attachments"
                }
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get config value by dot notation (e.g., 'api_keys.brave_search')"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value):
        """Set config value by dot notation"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save_config(self.config)
    
    def get_brave_api_key(self) -> Optional[str]:
        """Get Brave Search API key"""
        key = self.get("api_keys.brave_search")
        if not key:
            print("⚠️  Brave API key not configured!")
            print(f"   Set it with: echo 'YOUR_KEY' > {self.config_dir}/brave_api_key")
            print("   Or edit: " + str(self.config_file))
        return key
    
    def setup_wizard(self):
        """Interactive setup wizard"""
        print("🔧 AI Council Configuration Wizard")
        print("="*60)
        
        # API Keys
        print("\n📋 API Keys (optional, press Enter to skip):")
        brave_key = input("Brave Search API key: ").strip()
        if brave_key:
            self.set("api_keys.brave_search", brave_key)
        
        # Performance
        print("\n⚡ Performance Settings:")
        print("CPU Threads (0 = auto-detect, default is optimal):")
        threads = input("Number of threads [0]: ").strip()
        if threads:
            self.set("performance.cpu_threads", int(threads))
        
        print("\nGPU Usage (-1 = auto, 0 = CPU only, >0 = GPU layers):")
        gpu = input("GPU setting [-1]: ").strip()
        if gpu:
            self.set("ollama.num_gpu", int(gpu))
        
        # Models
        print("\n🤖 Models (press Enter to keep defaults):")
        print(f"Current CODE model: {self.get('models.code')}")
        code_model = input("CODE model [qwen2.5:7b]: ").strip()
        if code_model:
            self.set("models.code", code_model)
        
        print("\n✅ Configuration saved!")
        print(f"📁 Config file: {self.config_file}")
        print("\nYou can edit it directly or run this wizard again.")

def setup_ollama_performance(config: Config):
    """Configure Ollama for optimal performance"""
    import subprocess
    import multiprocessing
    
    # Get CPU count
    cpu_count = multiprocessing.cpu_count()
    threads = config.get("performance.cpu_threads", 0)
    
    if threads == 0:
        # Auto-detect: use 80% of available cores
        threads = max(1, int(cpu_count * 0.8))
    
    print(f"💻 CPU Configuration:")
    print(f"   Total cores: {cpu_count}")
    print(f"   Using threads: {threads}")
    
    # Create systemd override for Ollama
    override_dir = Path("/etc/systemd/system/ollama.service.d")
    override_file = override_dir / "override.conf"
    
    gpu_layers = config.get("ollama.num_gpu", -1)
    
    override_content = f"""[Service]
Environment="OLLAMA_NUM_THREAD={threads}"
Environment="OLLAMA_NUM_GPU={gpu_layers}"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
"""
    
    try:
        if os.geteuid() == 0:  # Running as root
            override_dir.mkdir(parents=True, exist_ok=True)
            with open(override_file, 'w') as f:
                f.write(override_content)
            
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "restart", "ollama"], check=True)
            print("✅ Ollama configured for performance")
        else:
            print("\n⚠️  To apply performance settings, run as root:")
            print(f"sudo python -c 'from config import *; setup_ollama_performance(Config())'")
            print("\nOr manually create:")
            print(f"  {override_file}")
            print("With content:")
            print(override_content)
    except Exception as e:
        print(f"⚠️  Could not configure Ollama: {e}")
        print("Run manually or check permissions")

if __name__ == "__main__":
    import sys
    
    config = Config()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            config.setup_wizard()
        elif sys.argv[1] == "optimize":
            setup_ollama_performance(config)
        elif sys.argv[1] == "show":
            print(json.dumps(config.config, indent=2))
    else:
        print("Usage:")
        print("  python config.py setup     # Run setup wizard")
        print("  python config.py optimize  # Optimize Ollama performance")
        print("  python config.py show      # Show current config")
