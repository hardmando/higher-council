"""
Chat history and context management
Saves conversations and allows resuming
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import hashlib

class ChatMessage:
    """Represents a single message in chat"""
    def __init__(self, role: str, content: str, timestamp: Optional[str] = None, 
                 metadata: Optional[Dict] = None):
        self.role = role  # 'user', 'assistant', 'system'
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {})
        )

class Chat:
    """Represents a conversation with history"""
    def __init__(self, chat_id: Optional[str] = None, title: Optional[str] = None):
        self.chat_id = chat_id or self._generate_id()
        self.title = title or "New Chat"
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.metadata = {
            "profile": "AUTO",
            "search_enabled": True,
            "total_queries": 0,
            "total_time": 0.0
        }
    
    def _generate_id(self) -> str:
        """Generate unique chat ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the chat"""
        msg = ChatMessage(role, content, metadata=metadata)
        self.messages.append(msg)
        self.updated_at = datetime.now().isoformat()
        
        # Update stats
        if role == "user":
            self.metadata["total_queries"] += 1
        if metadata and "timing" in metadata:
            self.metadata["total_time"] += metadata["timing"].get("total", 0)
        
        # Auto-generate title from first user message
        if not self.title or self.title == "New Chat":
            if role == "user" and len(content) > 0:
                self.title = content[:50] + ("..." if len(content) > 50 else "")
    
    def get_context(self, max_messages: int = 10) -> List[Dict]:
        """Get recent messages for context"""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [msg.to_dict() for msg in recent]
    
    def to_dict(self) -> Dict:
        """Serialize chat to dict"""
        return {
            "chat_id": self.chat_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "messages": [msg.to_dict() for msg in self.messages]
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Deserialize chat from dict"""
        chat = cls(chat_id=data["chat_id"], title=data["title"])
        chat.created_at = data["created_at"]
        chat.updated_at = data["updated_at"]
        chat.metadata = data.get("metadata", {})
        chat.messages = [ChatMessage.from_dict(msg) for msg in data.get("messages", [])]
        return chat

class ChatManager:
    """Manages multiple chats and persistence"""
    def __init__(self, chats_dir: str = "~/.local/share/ai-council/chats"):
        self.chats_dir = Path(chats_dir).expanduser()
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self.current_chat: Optional[Chat] = None
    
    def new_chat(self, title: Optional[str] = None) -> Chat:
        """Create a new chat"""
        self.current_chat = Chat(title=title)
        return self.current_chat
    
    def save_chat(self, chat: Optional[Chat] = None):
        """Save chat to disk"""
        chat = chat or self.current_chat
        if not chat:
            return
        
        chat_file = self.chats_dir / f"{chat.chat_id}.json"
        with open(chat_file, 'w') as f:
            json.dump(chat.to_dict(), f, indent=2)
    
    def load_chat(self, chat_id: str) -> Optional[Chat]:
        """Load chat from disk"""
        chat_file = self.chats_dir / f"{chat_id}.json"
        if not chat_file.exists():
            return None
        
        with open(chat_file, 'r') as f:
            data = json.load(f)
        
        self.current_chat = Chat.from_dict(data)
        return self.current_chat
    
    def list_chats(self) -> List[Dict]:
        """List all saved chats"""
        chats = []
        for chat_file in sorted(self.chats_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
            with open(chat_file, 'r') as f:
                data = json.load(f)
            chats.append({
                "chat_id": data["chat_id"],
                "title": data["title"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "message_count": len(data.get("messages", [])),
                "metadata": data.get("metadata", {})
            })
        return chats
    
    def delete_chat(self, chat_id: str):
        """Delete a chat"""
        chat_file = self.chats_dir / f"{chat_id}.json"
        if chat_file.exists():
            chat_file.unlink()
    
    def export_chat(self, chat_id: str, format: str = "markdown") -> str:
        """Export chat in various formats"""
        chat = self.load_chat(chat_id)
        if not chat:
            return ""
        
        if format == "markdown":
            output = f"# {chat.title}\n\n"
            output += f"Created: {chat.created_at}\n"
            output += f"Messages: {len(chat.messages)}\n\n"
            output += "---\n\n"
            
            for msg in chat.messages:
                role_emoji = "👤" if msg.role == "user" else "🤖"
                output += f"## {role_emoji} {msg.role.title()}\n"
                output += f"*{msg.timestamp}*\n\n"
                output += f"{msg.content}\n\n"
                output += "---\n\n"
            
            return output
        
        elif format == "json":
            return json.dumps(chat.to_dict(), indent=2)
        
        elif format == "txt":
            output = f"{chat.title}\n"
            output += f"{'='*60}\n\n"
            
            for msg in chat.messages:
                output += f"[{msg.role.upper()}] {msg.timestamp}\n"
                output += f"{msg.content}\n\n"
            
            return output
        
        return ""

class AttachmentManager:
    """Manages file attachments"""
    def __init__(self, attachments_dir: str = "~/.local/share/ai-council/attachments"):
        self.attachments_dir = Path(attachments_dir).expanduser()
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
    
    def save_attachment(self, file_path: str, chat_id: str) -> Dict:
        """Save an attachment and return metadata"""
        source_path = Path(file_path).expanduser()
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create chat-specific directory
        chat_dir = self.attachments_dir / chat_id
        chat_dir.mkdir(exist_ok=True)
        
        # Copy file
        dest_path = chat_dir / source_path.name
        import shutil
        shutil.copy2(source_path, dest_path)
        
        # Generate metadata
        metadata = {
            "filename": source_path.name,
            "original_path": str(source_path),
            "stored_path": str(dest_path),
            "size": dest_path.stat().st_size,
            "mime_type": self._get_mime_type(dest_path),
            "uploaded_at": datetime.now().isoformat()
        }
        
        return metadata
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Guess MIME type from extension"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"
    
    def read_text_file(self, file_path: str) -> str:
        """Read text content from file"""
        path = Path(file_path)
        try:
            return path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return path.read_text(encoding='latin-1')
    
    def process_attachment(self, file_path: str) -> Dict:
        """Process attachment and extract usable content"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        result = {
            "filename": path.name,
            "type": "unknown",
            "content": None,
            "summary": ""
        }
        
        # Text files
        if ext in ['.txt', '.md', '.py', '.js', '.java', '.c', '.cpp', '.h', '.json', '.xml', '.yaml', '.yml', '.toml']:
            result["type"] = "text"
            result["content"] = self.read_text_file(file_path)
            result["summary"] = f"Text file ({len(result['content'])} chars)"
        
        # PDFs
        elif ext == '.pdf':
            result["type"] = "pdf"
            result["summary"] = "PDF file (text extraction not implemented)"
            # TODO: Add PDF text extraction using pypdf or similar
        
        # Images
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            result["type"] = "image"
            result["summary"] = f"Image file: {path.name}"
            # TODO: Add image analysis using vision models
        
        # Documents
        elif ext in ['.doc', '.docx']:
            result["type"] = "document"
            result["summary"] = "Word document (extraction not implemented)"
            # TODO: Add document parsing
        
        return result

# CLI for testing
if __name__ == "__main__":
    import sys
    
    manager = ChatManager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "list":
            chats = manager.list_chats()
            print(f"\n📚 Saved Chats ({len(chats)}):\n")
            for chat in chats:
                print(f"  [{chat['chat_id']}] {chat['title']}")
                print(f"      Updated: {chat['updated_at']}")
                print(f"      Messages: {chat['message_count']}")
                print()
        
        elif cmd == "show" and len(sys.argv) > 2:
            chat_id = sys.argv[2]
            chat = manager.load_chat(chat_id)
            if chat:
                print(f"\n💬 Chat: {chat.title}\n")
                for msg in chat.messages:
                    role_emoji = "👤" if msg.role == "user" else "🤖"
                    print(f"{role_emoji} [{msg.timestamp}]")
                    print(f"   {msg.content[:100]}...")
                    print()
            else:
                print(f"Chat {chat_id} not found")
        
        elif cmd == "export" and len(sys.argv) > 2:
            chat_id = sys.argv[2]
            format = sys.argv[3] if len(sys.argv) > 3 else "markdown"
            output = manager.export_chat(chat_id, format)
            print(output)
        
        elif cmd == "delete" and len(sys.argv) > 2:
            chat_id = sys.argv[2]
            manager.delete_chat(chat_id)
            print(f"Deleted chat {chat_id}")
    
    else:
        print("Usage:")
        print("  python chat_manager.py list")
        print("  python chat_manager.py show <chat_id>")
        print("  python chat_manager.py export <chat_id> [markdown|json|txt]")
        print("  python chat_manager.py delete <chat_id>")
