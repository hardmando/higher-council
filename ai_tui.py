#!/usr/bin/env python3
"""
AI Council Terminal UI - Updated with Chat History & Attachments
Requires: pip install rich textual
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Button, Static, Select, Label, ListView, ListItem
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual import events
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import asyncio
from datetime import datetime
import time
from pathlib import Path

# Import our AI systems
from ai_router import QueryRouter, ProfileManager, AIModel
from config import Config
from chat_manager import ChatManager, AttachmentManager

class ChatListScreen(Screen):
    """Screen to select from saved chats"""
    
    def __init__(self, chat_manager: ChatManager):
        super().__init__()
        self.chat_manager = chat_manager
        self.selected_chat_id = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container():
            yield Label("📚 Saved Chats", id="chat-list-title")
            yield ListView(id="chat-list")
            
            with Horizontal():
                yield Button("Load", variant="primary", id="btn-load-chat")
                yield Button("Delete", variant="error", id="btn-delete-chat")
                yield Button("Cancel", id="btn-cancel-chat")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Load chat list on mount"""
        chat_list = self.query_one("#chat-list", ListView)
        
        chats = self.chat_manager.list_chats()
        
        if not chats:
            chat_list.append(ListItem(Label("No saved chats")))
        else:
            for chat in chats:
                title = chat['title'][:50]
                msg_count = chat['message_count']
                updated = chat['updated_at'][:19]
                
                item = ListItem(
                    Label(f"{title}\n  {msg_count} messages | {updated}"),
                    id=f"chat-{chat['chat_id']}"
                )
                chat_list.append(item)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Store selected chat ID"""
        item_id = str(event.item.id)
        if item_id.startswith("chat-"):
            self.selected_chat_id = item_id.replace("chat-", "")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "btn-load-chat":
            if self.selected_chat_id:
                self.dismiss(("load", self.selected_chat_id))
        elif event.button.id == "btn-delete-chat":
            if self.selected_chat_id:
                self.chat_manager.delete_chat(self.selected_chat_id)
                self.dismiss(("delete", self.selected_chat_id))
        else:
            self.dismiss(None)

class AICouncilTUI(App):
    """Terminal UI for AI Council with Chat History"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #sidebar {
        width: 32;
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
    
    #chat-list-title {
        text-align: center;
        padding: 1;
        background: $primary;
        color: $text;
    }
    
    ListView {
        height: 20;
        border: solid $accent;
        margin: 1;
    }
    """
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "clear", "Clear Chat"),
        ("ctrl+s", "toggle_search", "Toggle Search"),
        ("ctrl+n", "new_chat", "New Chat"),
        ("ctrl+o", "open_chat", "Open Chat"),
        ("ctrl+e", "export_chat", "Export"),
    ]
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.chat_manager = ChatManager(self.config.get("storage.chats_dir"))
        self.attachment_manager = AttachmentManager(self.config.get("storage.attachments_dir"))
        self.router = None
        self.profile_manager = None
        self.current_profile = "AUTO"
        self.search_enabled = self.config.get("search.enabled", True)
        self.current_chat = self.chat_manager.new_chat()
        self.total_time = 0
    
    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header(show_clock=True)
        
        with Horizontal():
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("🤖 AI Council\n   v2.0", classes="status-box")
                yield Static(f"💬 Chat: {self.current_chat.title[:20]}", id="chat-info", classes="status-box")
                yield Static("Profile: AUTO", id="profile-status", classes="status-box")
                yield Static("🔍 Search: ON" if self.search_enabled else "🚫 Search: OFF", 
                           id="search-status", classes="status-box")
                yield Static("Queries: 0\nTotal: 0.0s\nAvg: 0.0s", id="stats", classes="status-box")
                
                yield Label("--- Profiles ---")
                yield Button("🎯 AUTO", id="btn-auto", classes="profile-button", variant="primary")
                yield Button("⚡ SIMPLE", id="btn-simple", classes="profile-button")
                yield Button("💻 CODE", id="btn-code", classes="profile-button")
                yield Button("🔬 RESEARCH", id="btn-research", classes="profile-button")
                yield Button("✨ CREATIVE", id="btn-creative", classes="profile-button")
                yield Button("🌐 CURRENT", id="btn-current", classes="profile-button")
                
                yield Label("--- Actions ---")
                yield Button("🔍 Toggle Search", id="btn-toggle-search", classes="profile-button")
                yield Button("💾 Save Chat", id="btn-save-chat", classes="profile-button")
                yield Button("📂 Open Chat", id="btn-open-chat", classes="profile-button")
                yield Button("📄 New Chat", id="btn-new-chat", classes="profile-button")
                yield Button("📤 Export", id="btn-export", classes="profile-button")
            
            # Main chat area
            with Vertical(id="chat-container"):
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
                
                with Container(id="input-container"):
                    yield Input(placeholder="Ask your question here... (Ctrl+N: new chat, Ctrl+O: open)", id="query-input")
                    yield Static("Enter: send | Ctrl+N: new | Ctrl+O: open | Ctrl+S: search | Ctrl+Q: quit", id="help-text")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize AI systems on startup"""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("🚀 Initializing AI Council v2.0...")
        
        # Initialize AI
        preprocessor = AIModel("Router", self.config.get("models.preprocessor"))
        self.router = QueryRouter(preprocessor)
        self.profile_manager = ProfileManager(
            ollama_url=self.config.get("ollama.url"),
            enable_search=self.search_enabled
        )
        
        chat_log.write("✅ AI systems ready!")
        chat_log.write("")
        
        # Welcome message
        welcome = Table.grid(padding=1)
        welcome.add_column(style="cyan", justify="left")
        welcome.add_row("🎉 Welcome to AI Council v2.0!")
        welcome.add_row("")
        welcome.add_row("✨ New Features:")
        welcome.add_row("  • Chat History - Conversations saved automatically")
        welcome.add_row("  • Ctrl+N - Start new chat")
        welcome.add_row("  • Ctrl+O - Load previous chat")
        welcome.add_row("  • Ctrl+S - Toggle web search")
        welcome.add_row("  • Ctrl+E - Export current chat")
        welcome.add_row("")
        welcome.add_row(f"⚙️  Config: {self.config.config_file}")
        welcome.add_row(f"💾 Chats: {self.chat_manager.chats_dir}")
        
        chat_log.write(Panel(welcome, title="[bold cyan]Welcome[/bold cyan]", border_style="cyan"))
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
        
        # Add to chat history
        self.current_chat.add_message("user", query)
        
        # Display user message
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("")
        chat_log.write(Panel(f"[bold cyan]{query}[/bold cyan]", title="👤 You", border_style="cyan"))
        
        # Process query
        await self.process_query(query)
        
        # Auto-save chat
        self.chat_manager.save_chat(self.current_chat)
        self.update_chat_info()
    
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
                
                chat_log.write(f"📋 Using: [bold green]{profile_name}[/bold green] profile")
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
            
            # Add to chat history
            self.current_chat.add_message("assistant", result['answer'], 
                                         metadata={"timing": result['timing'], "profile": profile_name})
            
            # Display answer
            chat_log.write("")
            chat_log.write(Panel(
                Markdown(result['answer']),
                title=f"[bold green]🤖 AI ({profile_name})[/bold green]",
                border_style="green"
            ))
            
            # Display timing
            timing_info = Table.grid(padding=0)
            timing_info.add_column(style="dim")
            timing_info.add_row(f"⏱️  {result['timing']['total']}s total")
            if result['timing']['preprocessing'] > 0.1:
                timing_info.add_row(f"   ├─ Prep: {result['timing']['preprocessing']}s")
                timing_info.add_row(f"   └─ Exec: {result['timing']['execution']}s")
            if result.get('search_enabled'):
                timing_info.add_row("   🔍 Web search used")
            
            chat_log.write(timing_info)
            
            # Update stats
            self.update_stats()
            
        except Exception as e:
            chat_log.write(f"[bold red]❌ Error:[/bold red] {str(e)}")
            import traceback
            chat_log.write(f"[dim]{traceback.format_exc()}[/dim]")
    
    def update_stats(self) -> None:
        """Update statistics display"""
        stats = self.query_one("#stats", Static)
        num_queries = self.current_chat.metadata.get("total_queries", 0)
        total_time = self.current_chat.metadata.get("total_time", 0)
        avg_time = total_time / num_queries if num_queries > 0 else 0
        
        stats.update(f"Queries: {num_queries}\nTotal: {total_time:.1f}s\nAvg: {avg_time:.1f}s")
    
    def update_chat_info(self) -> None:
        """Update chat info display"""
        chat_info = self.query_one("#chat-info", Static)
        title = self.current_chat.title[:20]
        msg_count = len(self.current_chat.messages)
        chat_info.update(f"💬 {title}\n   {msg_count} msgs")
    
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
        
        elif button_id == "btn-save-chat":
            self.action_save_chat()
        
        elif button_id == "btn-open-chat":
            await self.action_open_chat()
        
        elif button_id == "btn-new-chat":
            self.action_new_chat()
        
        elif button_id == "btn-export":
            self.action_export_chat()
        
        elif button_id in profile_map:
            self.current_profile = profile_map[button_id]
            profile_status = self.query_one("#profile-status", Static)
            profile_status.update(f"Profile: {self.current_profile}")
            
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write(f"✅ Switched to [bold]{self.current_profile}[/bold] profile")
    
    def action_clear(self) -> None:
        """Clear chat display (not history)"""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        chat_log.write(Panel("Chat display cleared (history preserved)", border_style="yellow"))
    
    def action_new_chat(self) -> None:
        """Start a new chat"""
        # Save current chat
        self.chat_manager.save_chat(self.current_chat)
        
        # Create new chat
        self.current_chat = self.chat_manager.new_chat()
        
        # Clear display
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        chat_log.write(Panel("📄 New chat started", border_style="green"))
        
        self.update_chat_info()
        self.update_stats()
    
    def action_save_chat(self) -> None:
        """Manually save current chat"""
        self.chat_manager.save_chat(self.current_chat)
        
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"💾 Chat saved: [bold]{self.current_chat.title}[/bold]")
        chat_log.write(f"   ID: {self.current_chat.chat_id}")
    
    async def action_open_chat(self) -> None:
        """Open a saved chat"""
        result = await self.push_screen_wait(ChatListScreen(self.chat_manager))
        
        if result:
            action, chat_id = result
            
            if action == "load":
                # Save current chat first
                self.chat_manager.save_chat(self.current_chat)
                
                # Load selected chat
                loaded_chat = self.chat_manager.load_chat(chat_id)
                if loaded_chat:
                    self.current_chat = loaded_chat
                    
                    # Clear and reload display
                    chat_log = self.query_one("#chat-log", RichLog)
                    chat_log.clear()
                    chat_log.write(f"📂 Loaded: [bold]{self.current_chat.title}[/bold]")
                    chat_log.write("")
                    
                    # Display chat history
                    for msg in self.current_chat.messages[-10:]:  # Last 10 messages
                        if msg.role == "user":
                            chat_log.write(Panel(msg.content, title="👤 You", border_style="cyan"))
                        elif msg.role == "assistant":
                            chat_log.write(Panel(Markdown(msg.content), title="🤖 AI", border_style="green"))
                        chat_log.write("")
                    
                    self.update_chat_info()
                    self.update_stats()
            
            elif action == "delete":
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write(f"🗑️  Deleted chat: {chat_id}")
    
    def action_export_chat(self) -> None:
        """Export current chat"""
        export_dir = Path("~/ai-council-exports").expanduser()
        export_dir.mkdir(exist_ok=True)
        
        # Export as markdown
        filename = f"chat_{self.current_chat.chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = export_dir / filename
        
        markdown_content = self.chat_manager.export_chat(self.current_chat.chat_id, "markdown")
        filepath.write_text(markdown_content)
        
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"📤 Exported to: [bold]{filepath}[/bold]")
    
    def action_toggle_search(self) -> None:
        """Toggle web search on/off"""
        self.search_enabled = not self.search_enabled
        self.profile_manager.toggle_search(self.search_enabled)
        
        # Update config
        self.config.set("search.enabled", self.search_enabled)
        
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
        # Save current chat before exiting
        self.chat_manager.save_chat(self.current_chat)
        self.exit()

def main():
    """Run the TUI"""
    # Check config exists
    config = Config()
    if not config.get("api_keys.brave_search"):
        print("⚠️  Configuration needed!")
        print("Run: python config.py setup")
        return
    
    app = AICouncilTUI()
    app.run()

if __name__ == "__main__":
    main()
