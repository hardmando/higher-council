import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Optional
import re
import argparse
import time

class AICouncilMember:
    """Represents a single AI model in the council"""
    def __init__(self, name: str, model: str, specialty: str, ollama_url: str = "http://localhost:11434", web_searcher: Optional['WebSearcher'] = None):
        self.name = name
        self.model = model
        self.specialty = specialty
        self.ollama_url = ollama_url
        self.web_searcher = web_searcher
    
    async def generate(self, prompt: str, context: str = "", allow_search: bool = False) -> Dict:
        """Generate a response from this council member"""
        
        # If this model has web search capability and it's allowed, let it search
        search_performed = False
        if allow_search and self.web_searcher:
            needs_search = any(keyword in prompt.lower() for keyword in 
                             ["current", "latest", "recent", "today", "now", "2024", "2025"])
            
            if needs_search:
                print(f"  → {self.name} performing web search...")
                search_results = await self.web_searcher.search(prompt)
                if not search_results.startswith("Search error"):
                    context = f"{context}\n\nWeb Search Results:\n{search_results}" if context else f"Web Search Results:\n{search_results}"
                    search_performed = True
                    print(f"  ✓ {self.name} got search results")
        
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        
        async with aiohttp.ClientSession() as session:
            try:
                print(f"  → {self.name} thinking...")
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"  ✗ {self.name} failed: HTTP {response.status}")
                        return {
                            "member": self.name,
                            "model": self.model,
                            "specialty": self.specialty,
                            "response": f"HTTP Error {response.status}",
                            "success": False,
                            "used_search": search_performed
                        }
                    
                    result = await response.json()
                    response_text = result.get("response", "")
                    
                    if not response_text:
                        print(f"  ✗ {self.name} returned empty response")
                        return {
                            "member": self.name,
                            "model": self.model,
                            "specialty": self.specialty,
                            "response": "Empty response",
                            "success": False,
                            "used_search": search_performed
                        }
                    
                    print(f"  ✓ {self.name} responded ({len(response_text)} chars)")
                    return {
                        "member": self.name,
                        "model": self.model,
                        "specialty": self.specialty,
                        "response": response_text,
                        "success": True,
                        "used_search": search_performed
                    }
            except Exception as e:
                print(f"  ✗ {self.name} error: {str(e)}")
                return {
                    "member": self.name,
                    "model": self.model,
                    "specialty": self.specialty,
                    "response": f"Error: {str(e)}",
                    "success": False,
                    "used_search": search_performed
                }

class WebSearcher:
    """Handles web searches using Brave API"""
    def __init__(self, brave_api_key: Optional[str] = None):
        self.brave_api_key = brave_api_key
    
    async def search(self, query: str, num_results: int = 5) -> str:
        """Perform web search and return formatted results"""
        if not self.brave_api_key:
            return "Web search not configured"
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {
                    "Accept": "application/json",
                    "X-Subscription-Token": self.brave_api_key
                }
                params = {"q": query, "count": num_results}
                
                print(f"  → Querying Brave API: '{query}'")
                
                async with session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        return f"Search error: HTTP {response.status}"
                    
                    data = await response.json()
                    results = []
                    
                    web_results = data.get("web", {}).get("results", [])
                    print(f"  ✓ Got {len(web_results)} results")
                    
                    for idx, item in enumerate(web_results[:num_results], 1):
                        results.append(
                            f"{idx}. {item.get('title', 'No title')}\n"
                            f"   {item.get('description', 'No description')}\n"
                            f"   URL: {item.get('url', '')}"
                        )
                    
                    return "\n\n".join(results) if results else "No results found"
                    
            except Exception as e:
                return f"Search error: {str(e)}"

class AICouncil:
    """Manages the council of AI models with a judge"""
    def __init__(self, members: List[AICouncilMember], judge: AICouncilMember, web_searcher: Optional[WebSearcher] = None):
        self.members = members
        self.judge = judge
        self.web_searcher = web_searcher
    
    async def deliberate(self, query: str, use_search: bool = True, force_search: bool = False) -> Dict:
        """Main method: Get responses from all members, judge synthesizes best answer"""
        print(f"\n{'='*60}")
        print(f"COUNCIL QUERY: {query}")
        print(f"{'='*60}\n")
        
        # Check if we need web search
        search_context = ""
        should_search = force_search or (use_search and self._needs_web_search(query))
        
        if should_search and self.web_searcher:
            print(f"🔍 Performing web search...")
            search_results = await self.web_searcher.search(query)
            if not search_results.startswith("Search error"):
                print(f"✓ Search completed\n")
                search_context = f"Web Search Results:\n{search_results}\n\n"
        
        # Get responses from council members
        print("🤖 Gathering council responses...")
        responses = []
        for member in self.members:
            response = await member.generate(query, search_context, allow_search=use_search)
            responses.append(response)
        
        # Display responses
        print("\n" + "="*60)
        print("COUNCIL RESPONSES:")
        print("="*60)
        for resp in responses:
            if resp["success"]:
                badge = " 🔍" if resp.get("used_search") else ""
                print(f"\n[{resp['member']}]{badge}:")
                preview = resp['response'][:250] + "..." if len(resp['response']) > 250 else resp['response']
                print(preview)
        
        # Judge synthesizes
        print("\n" + "="*60)
        print("JUDGE DELIBERATION:")
        print("="*60 + "\n")
        
        final_result = await self._judge_synthesize(query, responses, search_context)
        return final_result
    
    def _needs_web_search(self, query: str) -> bool:
        """Determine if query needs web search"""
        keywords = [
            "current", "latest", "recent", "today", "news", "weather", 
            "2024", "2025", "now", "price", "cost", "how much", "pay",
            "stock", "who won", "what happened", "this week", "this month"
        ]
        return any(k in query.lower() for k in keywords)
    
    async def _judge_synthesize(self, query: str, responses: List[Dict], context: str) -> Dict:
        """Judge reviews all responses and synthesizes the best answer"""
        
        successful = [r for r in responses if r["success"]]
        if not successful:
            print("❌ No successful responses!")
            return None
        
        # Prepare responses for judge
        responses_text = ""
        for idx, resp in enumerate(successful, 1):
            responses_text += f"\n{'='*50}\nRESPONSE {idx} from {resp['member']}:\n{'='*50}\n{resp['response']}\n"
        
        judge_prompt = f"""You are a judge reviewing multiple AI responses. Your task is to synthesize the BEST possible answer.

QUERY: "{query}"

{responses_text}

Synthesize these responses into ONE comprehensive, accurate answer. Take the best ideas from each. Make it clear and complete. 

Provide ONLY the final answer - no preamble or meta-commentary."""

        print(f"🧑‍⚖️ {self.judge.name} reviewing and synthesizing...")
        
        judge_result = await self.judge.generate(judge_prompt, context, allow_search=False)
        
        if not judge_result["success"]:
            print("⚠️  Judge failed, using best response")
            return {
                "query": query,
                "final_answer": successful[0]["response"],
                "judge": "Fallback",
                "all_responses": responses,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"✓ {self.judge.name} synthesis complete\n")
        
        return {
            "query": query,
            "final_answer": judge_result["response"],
            "judge": self.judge.name,
            "all_responses": responses,
            "timestamp": datetime.now().isoformat()
        }

async def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(description='AI Council')
    parser.add_argument('query', nargs='?', help='Your question')
    parser.add_argument('--force-search', '-s', action='store_true', help='Force web search')
    parser.add_argument('--no-search', action='store_true', help='Disable web search')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    args = parser.parse_args()
    
    # Setup web search
    web_searcher = WebSearcher(brave_api_key="BSA3KHYeLRPoIytYKYNJUj0qrYwKagp")
    
    # Create council members
    members = [
        AICouncilMember("Sage", "llama3.2:3b", "General Knowledge", web_searcher=web_searcher),
        AICouncilMember("Scholar", "phi3.5:3.8b", "Technical Analysis", web_searcher=web_searcher),
        AICouncilMember("Engineer", "qwen2.5:3b", "Problem Solving", web_searcher=web_searcher),
    ]
    
    # Create judge
    judge = AICouncilMember("Judge", "llama3.2:3b", "Synthesis", web_searcher=web_searcher)
    
    # Create council
    council = AICouncil(members, judge, web_searcher)
    
    # Interactive mode
    if args.interactive:
        print("="*60)
        print("AI COUNCIL - Interactive Mode")
        print("="*60)
        print("Commands:")
        print("  Just type your question")
        print("  Add --search or -s to force web search")
        print("  Type 'search on/off' to toggle web search")
        print("  Type 'quit' or 'exit' to leave")
        print("="*60 + "\n")
        
        web_search_enabled = not args.no_search
        total_queries = 0
        total_time = 0.0
        
        while True:
            try:
                user_input = input("\n💬 Your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print(f"\n📊 Session stats: {total_queries} queries, {total_time:.1f}s total")
                    print("Goodbye! 👋")
                    break
                
                if user_input.lower() == 'search on':
                    web_search_enabled = True
                    print("✅ Web search enabled")
                    continue
                elif user_input.lower() == 'search off':
                    web_search_enabled = False
                    print("🚫 Web search disabled")
                    continue
                
                if not user_input:
                    continue
                
                # Check for --search flag in input
                force_search = '--search' in user_input or '-s' in user_input
                user_input = user_input.replace('--search', '').replace('-s', '').strip()
                
                start_time = time.time()
                result = await council.deliberate(user_input, use_search=web_search_enabled, force_search=force_search)
                query_time = time.time() - start_time
                
                if result:
                    total_queries += 1
                    total_time += query_time
                    
                    print("\n" + "="*60)
                    print("FINAL ANSWER:")
                    print("="*60)
                    print(f"\n{result['final_answer']}\n")
                    
                    # Timing info
                    print("="*60)
                    print(f"⏱️  Time: {query_time:.2f}s")
                    if args.show_timing:
                        avg_time = total_time / total_queries
                        print(f"   Session: {total_queries} queries, {total_time:.1f}s total, {avg_time:.1f}s avg")
                    print("="*60)
                    
            except KeyboardInterrupt:
                print(f"\n\n📊 Session stats: {total_queries} queries, {total_time:.1f}s total")
                print("Goodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        return
    
    # Single query
    if args.query:
        start_time = time.time()
        result = await council.deliberate(args.query, not args.no_search, args.force_search)
        query_time = time.time() - start_time
        
        if result:
            print("\n" + "="*60)
            print("FINAL ANSWER:")
            print("="*60)
            print(f"\n{result['final_answer']}\n")
            print(f"Synthesized by: {result['judge']}")
            
            search_users = [r['member'] for r in result['all_responses'] if r.get('used_search')]
            if search_users:
                print(f"Web search used by: {', '.join(search_users)}")
            
            print("="*60)
            print(f"⏱️  Time: {query_time:.2f}s")
            print("="*60)
    else:
        # Demo queries
        queries = [
            ("What is Python?", False),
            ("Latest AI news", True),
        ]
        
        for q, force in queries:
            result = await council.deliberate(q, not args.no_search, force)
            if result:
                print("\n" + "="*60)
                print("FINAL ANSWER:")
                print("="*60)
                print(f"\n{result['final_answer']}\n")

if __name__ == "__main__":
    asyncio.run(main())