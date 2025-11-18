#!/usr/bin/env python3
"""
AI Council Terminal UI
Requires: pip install rich textual
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Button, Static, Select, Switch
from textual.containers import Container, Horizontal, Vertical
from textual import events
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import asyncio
from datetime import datetime
import time

# Import our AI systems
from ai_router import QueryRouter, ProfileManager, AIModel

class AICouncilTUI(App):
    """Terminal UI for AI Council"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary;
    }
    
    #chat-container {
        width: 1fr;
        height: 1fr;
    }
    
    #chat-log {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #input-container {
        height: auto;
        padding: 1;
        background: $panel;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    .status-box {
        height: auto;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }
    
    .profile-button {
        width: 100%;
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "clear", "Clear Chat"),
        ("ctrl+s", "toggle_search", "Toggle Search"),
    ]
    
    def __init__(self):
        super().__init__()
        self.router = None
        self.profile_manager = None
        self.current_profile = "AUTO"
        self.search_enabled = True
        self.history = []
        self.total_time = 0
    
    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header(show_clock=True)
        
        with Horizontal():
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("🤖 AI Council", classes="status-box")
                yield Static("Profile: AUTO", id="profile-status", classes="status-box")
                yield Static("🔍 Search: ON", id="search-status", classes="status-box")
                yield Static("Queries: 0\nTotal time: 0.0s\nAvg: 0.0s", id="stats", classes="status-box")
                
                yield Button("🎯 AUTO", id="btn-auto", classes="profile-button")
                yield Button("⚡ SIMPLE", id="btn-simple", classes="profile-button")
                yield Button("💻 CODE", id="btn-code", classes="profile-button")
                yield Button("🔬 RESEARCH", id="btn-research", classes="profile-button")
                yield Button("✨ CREATIVE", id="btn-creative", classes="profile-button")
                yield Button("🌐 CURRENT", id="btn-current", classes="profile-button")
                yield Button("🔍 Toggle Search", id="btn-toggle-search", classes="profile-button")
            
            # Main chat area
            with Vertical(id="chat-container"):
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
                
                with Container(id="input-container"):
                    yield Input(placeholder="Ask your question here...", id="query-input")
                    yield Static("Enter: send | Ctrl+Q: quit | Ctrl+C: clear | Ctrl+S: toggle search", id="help-text")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize AI systems on startup"""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("🚀 Initializing AI systems...")
        
        # Initialize AI
        preprocessor = AIModel("Router", "llama3.2:3b")
        self.router = QueryRouter(preprocessor)
        self.profile_manager = ProfileManager(enable_search=True)
        
        chat_log.write("✅ AI systems ready!")
        chat_log.write("")
        chat_log.write(Panel("Welcome to AI Council! Ask any question and I'll route it to the best AI profile.\n\nControls:\n• Ctrl+S: Toggle web search\n• Ctrl+C: Clear chat\n• Click buttons to switch profiles", 
                            title="[bold cyan]Welcome[/bold cyan]", 
                            border_style="cyan"))
        chat_log.write("")
        
        # Focus input
        self.query_one("#query-input", Input).focus()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user query submission"""
        query = event.value.strip()
        if not query:
            return
        
        # Clear input
        event.input.value = ""
        
        # Add to history
        self.history.append({"query": query, "timestamp": datetime.now()})
        
        # Display user message
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("")
        chat_log.write(Panel(f"[bold cyan]You:[/bold cyan] {query}", border_style="cyan"))
        
        # Process query
        await self.process_query(query)
    
    async def process_query(self, query: str) -> None:
        """Process and answer query"""
        chat_log = self.query_one("#chat-log", RichLog)
        profile_status = self.query_one("#profile-status", Static)
        
        start_time = time.time()
        
        try:
            # Route query
            if self.current_profile == "AUTO":
                chat_log.write("🔍 [italic]Analyzing query...[/italic]")
                routing = await self.router.analyze_query(query)
                profile_name = routing["profile"]
                reason = routing["reason"]
                needs_search = routing["needs_search"]
                
                chat_log.write(f"📋 Profile: [bold green]{profile_name}[/bold green]")
                chat_log.write(f"💡 {reason}")
                if needs_search and self.search_enabled:
                    chat_log.write("🔍 Web search enabled")
            else:
                profile_name = self.current_profile
                reason = "User selected"
                needs_search = profile_name == "CURRENT"
            
            profile_status.update(f"Profile: {profile_name}")
            
            # Show thinking indicator
            chat_log.write("")
            chat_log.write("💭 [italic]Thinking...[/italic]")
            
            # Get answer
            result = await self.profile_manager.execute_profile(profile_name, query, needs_search)
            
            query_time = time.time() - start_time
            self.total_time += query_time
            
            # Display answer
            chat_log.write("")
            chat_log.write(Panel(
                Markdown(result['answer']),
                title=f"[bold green]AI ({profile_name})[/bold green]",
                border_style="green"
            ))
            
            # Display timing
            timing_text = f"⏱️  [dim]Time: {result['timing']['total']}s"
            if result['timing']['preprocessing'] > 0.1:
                timing_text += f" (prep: {result['timing']['preprocessing']}s, exec: {result['timing']['execution']}s)"
            timing_text += "[/dim]"
            chat_log.write(timing_text)
            
            # Update stats
            self.update_stats()
            
        except Exception as e:
            chat_log.write(f"[bold red]Error:[/bold red] {str(e)}")
    
    def update_stats(self) -> None:
        """Update statistics display"""
        stats = self.query_one("#stats", Static)
        num_queries = len(self.history)
        avg_time = self.total_time / num_queries if num_queries > 0 else 0
        stats.update(f"Queries: {num_queries}\nTotal time: {self.total_time:.1f}s\nAvg: {avg_time:.1f}s")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle profile button clicks"""
        button_id = event.button.id
        
        profile_map = {
            "btn-auto": "AUTO",
            "btn-simple": "SIMPLE",
            "btn-code": "CODE",
            "btn-research": "RESEARCH",
            "btn-creative": "CREATIVE",
            "btn-current": "CURRENT"
        }
        
        if button_id == "btn-toggle-search":
            self.action_toggle_search()
        elif button_id in profile_map:
            self.current_profile = profile_map[button_id]
            profile_status = self.query_one("#profile-status", Static)
            profile_status.update(f"Profile: {self.current_profile}")
            
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write(f"✅ Switched to [bold]{self.current_profile}[/bold] profile")
    
    def action_clear(self) -> None:
        """Clear chat history"""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        chat_log.write(Panel("Chat cleared", border_style="yellow"))
    
    def action_toggle_search(self) -> None:
        """Toggle web search on/off"""
        self.search_enabled = not self.search_enabled
        self.profile_manager.toggle_search(self.search_enabled)
        
        search_status = self.query_one("#search-status", Static)
        status_text = "🔍 Search: ON" if self.search_enabled else "🚫 Search: OFF"
        search_status.update(status_text)
        
        chat_log = self.query_one("#chat-log", RichLog)
        if self.search_enabled:
            chat_log.write("✅ [bold green]Web search enabled[/bold green]")
        else:
            chat_log.write("🚫 [bold yellow]Web search disabled[/bold yellow]")
    
    def action_quit(self) -> None:
        """Quit application"""
        self.exit()

def main():
    """Run the TUI"""
    app = AICouncilTUI()
    app.run()

if __name__ == "__main__":
    main()