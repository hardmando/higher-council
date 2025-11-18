import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Optional
import re
import time

class AIModel:
    """Simple wrapper for a single AI model"""
    def __init__(self, name: str, model: str, ollama_url: str = "http://localhost:11434"):
        self.name = name
        self.model = model
        self.ollama_url = ollama_url
    
    async def generate(self, prompt: str, system: str = "") -> Dict:
        """Generate response from this model"""
        async with aiohttp.ClientSession() as session:
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        return {"success": False, "response": f"Error: HTTP {response.status}"}
                    
                    result = await response.json()
                    message = result.get("message", {})
                    content = message.get("content", "")
                    
                    return {"success": True, "response": content}
            except Exception as e:
                return {"success": False, "response": f"Error: {str(e)}"}

class QueryRouter:
    """Routes queries to appropriate AI profile based on intent"""
    def __init__(self, preprocessor: AIModel):
        self.preprocessor = preprocessor
    
    async def analyze_query(self, query: str) -> Dict:
        """Analyze query and determine best routing"""
        
        routing_prompt = f"""Analyze this query and determine the best AI profile to handle it.

Query: "{query}"

Available profiles:
1. SIMPLE - Quick factual questions, definitions, simple explanations (use smallest/fastest model)
2. CODE - Programming, debugging, code review, technical implementation
3. RESEARCH - Complex topics needing multiple perspectives, research, detailed analysis
4. CREATIVE - Writing, brainstorming, creative content
5. CURRENT - Questions needing real-time web search (news, prices, recent events)

Respond in this EXACT format:
PROFILE: [profile name]
REASON: [one sentence why]
NEEDS_SEARCH: [yes/no]

Example:
PROFILE: CODE
REASON: User is asking for help debugging Python code
NEEDS_SEARCH: no"""

        result = await self.preprocessor.generate(routing_prompt)
        
        if not result["success"]:
            # Fallback to simple heuristics
            return self._fallback_routing(query)
        
        response = result["response"]
        
        # Parse response
        profile = "SIMPLE"
        reason = "Fallback routing"
        needs_search = False
        
        for line in response.split('\n'):
            if line.startswith('PROFILE:'):
                profile = line.split(':', 1)[1].strip().upper()
            elif line.startswith('REASON:'):
                reason = line.split(':', 1)[1].strip()
            elif line.startswith('NEEDS_SEARCH:'):
                needs_search = 'yes' in line.lower()
        
        return {
            "profile": profile,
            "reason": reason,
            "needs_search": needs_search,
            "original_query": query
        }
    
    def _fallback_routing(self, query: str) -> Dict:
        """Simple keyword-based routing if preprocessor fails"""
        query_lower = query.lower()
        
        # Check for code keywords
        code_keywords = ["code", "program", "function", "debug", "error", "python", "javascript", "java", "c++", "syntax"]
        if any(kw in query_lower for kw in code_keywords):
            return {"profile": "CODE", "reason": "Code keywords detected", "needs_search": False}
        
        # Check for current events
        current_keywords = ["latest", "recent", "today", "news", "current", "now", "2024", "2025"]
        if any(kw in query_lower for kw in current_keywords):
            return {"profile": "CURRENT", "reason": "Current events keywords", "needs_search": True}
        
        # Check for research indicators
        research_keywords = ["explain", "compare", "analyze", "why", "how does", "research", "study"]
        if any(kw in query_lower for kw in research_keywords) and len(query.split()) > 10:
            return {"profile": "RESEARCH", "reason": "Complex research question", "needs_search": False}
        
        # Check for creative
        creative_keywords = ["write", "story", "poem", "creative", "imagine", "brainstorm"]
        if any(kw in query_lower for kw in creative_keywords):
            return {"profile": "CREATIVE", "reason": "Creative content request", "needs_search": False}
        
        # Default to simple
        return {"profile": "SIMPLE", "reason": "Simple factual question", "needs_search": False}

class ProfileManager:
    """Manages different AI profiles and routes queries"""
    def __init__(self, ollama_url: str = "http://localhost:11434", enable_search: bool = True):
        self.ollama_url = ollama_url
        self.enable_search = enable_search
        self.profiles = {}
        self._setup_profiles()
    
    def toggle_search(self, enabled: bool):
        """Enable or disable web search globally"""
        self.enable_search = enabled
    
    def _setup_profiles(self):
        """Setup available profiles"""
        # Import the council system
        from ai_council import AICouncilMember, AICouncil, WebSearcher
        
        # SIMPLE: Fast single model
        self.profiles["SIMPLE"] = {
            "type": "single",
            "model": AIModel("QuickAnswer", "llama3.2:3b", self.ollama_url),
            "description": "Fast answers for simple questions"
        }
        
        # CODE: Specialized coding model
        self.profiles["CODE"] = {
            "type": "single",
            "model": AIModel("CodeExpert", "qwen2.5:7b", self.ollama_url),
            "description": "Expert coding assistance",
            "system_prompt": "You are an expert programmer. Provide clear, working code with explanations."
        }
        
        # CREATIVE: Creative model
        self.profiles["CREATIVE"] = {
            "type": "single", 
            "model": AIModel("Creator", "llama3.2:3b", self.ollama_url),
            "description": "Creative writing and brainstorming",
            "system_prompt": "You are a creative writer. Be imaginative, engaging, and original."
        }
        
        # RESEARCH: Full council
        self.profiles["RESEARCH"] = {
            "type": "council",
            "description": "Multi-AI council for complex topics"
        }
        
        # CURRENT: With web search
        self.profiles["CURRENT"] = {
            "type": "council",
            "description": "Real-time information with web search",
            "force_search": True
        }
    
    async def execute_profile(self, profile_name: str, query: str, needs_search: bool = False) -> Dict:
        """Execute query using specified profile and return result with timing"""
        
        start_time = time.time()
        
        profile = self.profiles.get(profile_name)
        if not profile:
            return {
                "answer": "Unknown profile",
                "timing": {
                    "total": 0,
                    "preprocessing": 0,
                    "execution": 0
                }
            }
        
        # Override search if globally disabled
        if not self.enable_search:
            needs_search = False
        
        execution_start = time.time()
        
        if profile["type"] == "single":
            # Single model response
            model = profile["model"]
            system = profile.get("system_prompt", "")
            result = await model.generate(query, system)
            answer = result["response"]
        
        elif profile["type"] == "council":
            # Use council system
            from ai_council import AICouncilMember, AICouncil, WebSearcher
            
            # Setup web search only if enabled
            web_searcher = None
            if self.enable_search:
                web_searcher = WebSearcher(brave_api_key="BSA3KHYeLRPoIytYKYNJUj0qrYwKagp")
            
            # Create council
            members = [
                AICouncilMember("Sage", "llama3.2:3b", "General", web_searcher=web_searcher),
                AICouncilMember("Scholar", "phi3.5:3.8b", "Technical", web_searcher=web_searcher),
                AICouncilMember("Engineer", "qwen2.5:3b", "Practical", web_searcher=web_searcher),
            ]
            
            judge = AICouncilMember("Judge", "llama3.2:3b", "Synthesis", web_searcher=web_searcher)
            council = AICouncil(members, judge, web_searcher)
            
            force_search = profile.get("force_search", False) or needs_search
            result = await council.deliberate(query, use_search=self.enable_search, force_search=force_search)
            
            if result:
                answer = result["final_answer"]
            else:
                answer = "Council failed to generate response"
        
        execution_time = time.time() - execution_start
        total_time = time.time() - start_time
        
        return {
            "answer": answer,
            "timing": {
                "total": round(total_time, 2),
                "execution": round(execution_time, 2),
                "preprocessing": round(total_time - execution_time, 2)
            },
            "profile": profile_name,
            "search_enabled": self.enable_search and needs_search
        }

async def main():
    """Main router function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Router with Profiles')
    parser.add_argument('query', nargs='?', help='Your question')
    parser.add_argument('--profile', '-p', help='Force specific profile (SIMPLE/CODE/RESEARCH/CREATIVE/CURRENT)')
    parser.add_argument('--no-preprocess', action='store_true', help='Skip preprocessing, use specified profile or SIMPLE')
    parser.add_argument('--no-search', action='store_true', help='Disable web search globally')
    parser.add_argument('--time', '-t', action='store_true', help='Show detailed timing breakdown')
    
    args = parser.parse_args()
    
    # Initialize router
    preprocessor = AIModel("Router", "llama3.2:3b")
    router = QueryRouter(preprocessor)
    profile_manager = ProfileManager(enable_search=not args.no_search)
    
    if args.query:
        query = args.query
        overall_start = time.time()
        
        # Route the query
        if args.no_preprocess:
            profile_name = args.profile or "SIMPLE"
            reason = "Manual selection"
            needs_search = False
            routing_time = 0
        elif args.profile:
            profile_name = args.profile.upper()
            reason = "User specified"
            needs_search = False
            routing_time = 0
        else:
            routing_start = time.time()
            print("🔍 Analyzing query...")
            routing = await router.analyze_query(query)
            routing_time = time.time() - routing_start
            profile_name = routing["profile"]
            reason = routing["reason"]
            needs_search = routing["needs_search"]
        
        print(f"📋 Profile: {profile_name}")
        print(f"💡 Reason: {reason}")
        if not args.no_search and needs_search:
            print(f"🔍 Web search enabled")
        elif args.no_search:
            print(f"🚫 Web search disabled")
        print()
        print("="*60)
        
        # Execute
        result = await profile_manager.execute_profile(profile_name, query, needs_search)
        
        overall_time = time.time() - overall_start
        
        print("\n" + "="*60)
        print("ANSWER:")
        print("="*60)
        print(f"\n{result['answer']}\n")
        
        # Always show basic timing
        print("="*60)
        print("⏱️  TIMING:")
        print(f"  Total time: {result['timing']['total']}s")
        
        # Detailed timing if requested
        if args.time:
            print(f"  ├─ Routing: {routing_time:.2f}s")
            print(f"  ├─ Preprocessing: {result['timing']['preprocessing']}s")
            print(f"  └─ Execution: {result['timing']['execution']}s")
            if result.get('search_enabled'):
                print(f"  Note: Includes web search time")
        print("="*60 + "\n")
    else:
        print("Usage: python ai_router.py 'your question here'")
        print("       python ai_router.py 'your question' --profile CODE")
        print("       python ai_router.py 'your question' --no-search")
        print("       python ai_router.py 'your question' --time")

if __name__ == "__main__":
    asyncio.run(main())