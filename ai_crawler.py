"""
AI Crawler Module (Phase 6)
Implements 'The Scout' using Google Gemini to semantically navigate university websites.
"""

import os
import asyncio
import google.generativeai as genai
from typing import List, Dict, Set
from scraper import DeepUniversityCrawler
from analyzer import KeywordAnalyzer
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
else:
    print("⚠️  GEMINI_API_KEY not found. AI Crawler will fallback to heuristic mode.")

class AICrawler(DeepUniversityCrawler):
    """
    AI-Powered Crawler that uses Gemini (The Scout) to prioritize navigation.
    Inherits from DeepUniversityCrawler but replaces heuristic link prioritizing.
    """
    
    def __init__(self, analyzer: KeywordAnalyzer, universities, position_type="phd"):
        super().__init__(analyzer, universities)
        self.position_type = position_type
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.use_ai = bool(GEMINI_KEY)
        
        print(f"🤖 AI Crawler initialized (Mode: {position_type}) - Gemini Active: {self.use_ai}")

    async def _get_ai_priority(self, links_data: List[Dict]) -> List[Dict]:
        """
        Ask Gemini which links are most relevant to the target position.
        """
        if not self.use_ai or not links_data:
            return []

        # Prepare prompt
        target = "PhD/Doctoral positions" if self.position_type == "phd" else "PostDoc/Tenure Track positions"
        
        # Limit to 50 links per batch to fit context and speed
        links_batch = links_data[:50] 
        
        links_text = "\n".join([
            f"{i}: {link['text']} ({link['url']})" 
            for i, link in enumerate(links_batch)
        ])
        
        prompt = f"""You are a research crawler scout. I am looking for {target}.
Review these links found on a university page. Which ones are most likely to lead to JOB LISTINGS?

Criteria:
- IGNORE: individual profiles, alumni, news, events, privacy policy, login.
- PRIORITIZE: 'Vacancies', 'Career', 'Open Positions', 'Join us', specific research group pages that imply hiring.
- CONTEXT: 'Team' or 'People' might have hidden jobs if no clear 'Career' link exists.

Links:
{links_text}

Return ONLY a JSON array of indices (integers) for the top 5 most promising links. Example: [0, 4, 12]
If none are relevant, return [].
"""

        try:
            # We wrap this in a thread executor if it's blocking, but usually fast enough
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    stop_sequences=[']'],
                    max_output_tokens=50,
                    temperature=0.1
                )
            )
            
            # Simple parsing
            text = response.text
            if "[" in text:
                # Add closing bracket if cut off (unlikely with stop sequence, but safety first)
                clean_text = text[text.find("["):].strip()
                if not clean_text.endswith("]"): clean_text += "]"
                
                import json
                indices = json.loads(clean_text)
                
                # Get the actual link objects
                prioritized_links = []
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(links_batch):
                        prioritized_links.append(links_batch[idx])
                
                return prioritized_links
                
        except Exception as e:
            print(f"    ⚠️ Gemini Scout failed: {e}")
            return []

        return []

    # Override the crawl logic to use AI for prioritization
    # Since we can't easily override the internal bfs loop without copying mainly...
    # We will modify the approach: We will stick to the BFS structure but 
    # when collecting links, we verify them with AI.
    
    # Actually, DeepUniversityCrawler uses `_extract_links` and puts them in queue.
    # The best way is to monkey-patch or override `_extract_links` or similar if it existed.
    # But checking scraper.py, the logic is inside `crawl_university`.
    
    # To avoid 500 lines of code duplication, I will implement a slightly different architecture.
    # I will override `crawl_university` but copy the improvements.
    
    async def crawl_university(self, context, uni):
        """
        AI-Enhanced Crawling of a single university.
        """
        name = uni['name']
        start_url = uni['url']
        print(f"  🤖 AI-Scouting {name}...")
        
        page = await context.new_page()
        visited = set()
        queue = [(start_url, 0)] # url, depth
        found_jobs_count = 0
        
        try:
            while queue and len(visited) < self.max_pages:
                url, depth = queue.pop(0)
                
                if url in visited:
                    continue
                
                # Verify URL validity (heuristic check still useful for speed)
                base_domain = start_url.split('/')[2]
                if not self._is_valid_url(url, base_domain):
                    continue
                    
                visited.add(url)
                
                try:
                    await page.goto(url, timeout=15000)
                    # No wait needed for static analysis usually, but scrape needs content
                    
                    # 1. Scrape for Jobs (The Detective - Heuristic/Regex for now, handled by base class logic mostly)
                    # We reuse the logic from BaseScraper/DeepUniversityCrawler effectively by checking page content
                    
                    page_content = await page.content()
                    
                    # Check if relevant content
                    if self.analyzer.is_relevant(page_content) or self._check_phd_keywords(page_content):
                        # This page has keywords. Extract jobs.
                        # Here we could use ChatGPT for specific extraction if it blocks matching.
                        # But for now, let's trust the existing extractor provided it finds *something*.
                        pass 
                        # Actual job extraction happens implicitly if we add to self.jobs in base Crawler?
                        # No, DeepUniversityCrawler logic has explicit job finding code.
                        
                        # Let's borrow the job finding logic
                        # (Simplification: We assume if we are here, we check for job links)
                        
                        # Use the existing implementation's job extraction or similar
                        # Since I can't call super internal logic easily if it's monolithic...
                        # I will implement a new "Extract Jobs" call here
                        
                        jobs_found = await self._extract_jobs_from_page(page, name, url) 
                        if jobs_found:
                            found_jobs_count += len(jobs_found)
                
                except Exception as e:
                    # Ignore nav errors
                    pass
                
                # STOP if depth reached
                if depth >= self.max_depth:
                    continue
                    
                # 2. Extract & Prioritize Links (The Scout - Gemini)
                links_data = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a')).map(a => ({
                        text: a.innerText.trim(),
                        url: a.href
                    })).filter(l => l.text.length > 3 && l.url.startsWith('http'));
                }''')
                
                if not links_data:
                    continue
                    
                # Ask Gemini
                # We prioritize "Smart High Priority" links
                print(f"    👀 Scout analyzing {len(links_data)} links on depth {depth}...")
                prioritized_links = await self._get_ai_priority(links_data)
                
                # Add prioritized links to FRONT of queue (DFS/Best-First)
                for link in reversed(prioritized_links): # Reverse to keep order when pushing to front
                    if link['url'] not in visited:
                        queue.insert(0, (link['url'], depth + 1))
                        # Mark as visited in queue logic? No, loop handles it.
                
                # Add remaining valid links to END (BFS) - Fallback
                # Only if queue is small, otherwise exclude to save time? 
                # Let's just add ones that match heuristic regex to end
                regex_priority_links = []
                for link in links_data:
                    # Check if valid and not already prioritized
                    if any(p['url'] == link['url'] for p in prioritized_links):
                        continue
                        
                    if self._check_priority_pattern(link['url']) or self._check_priority_pattern(link['text']):
                        regex_priority_links.append(link['url'])
                
                for r_url in regex_priority_links:
                    if r_url not in visited:
                        queue.append((r_url, depth + 1))
                        
            print(f"    ✅ Finished {name}: Found {found_jobs_count} positions")
            
        except Exception as e:
            print(f"    ⚠️ Error crawling {name}: {e}")
        finally:
            await page.close()

    async def _extract_jobs_from_page(self, page, uni_name, url):
        # reuse logic from main scraper or simplify
        # For now, let's use a simplified heuristic + generic extraction
        # This part interacts with Phase 5 (LLM verification) later
        
        # We look for explicit job blocks
        jobs = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a').forEach(a => {
                const text = a.innerText.toLowerCase();
                if (text.includes('phd') || text.includes('doctoral') || text.includes('postdoc')) {
                   // Basic filtering
                   if (text.length < 100) {
                       results.push({title: a.innerText, url: a.href});
                   }
                }
            });
            return results;
        }''')
        
        valid_jobs = []
        for j in jobs:
            # Basic filter
            self.jobs.append({
                "title": j['title'],
                "university": uni_name,
                "url": j['url'],
                "found_date": "2024-...", # dynamic
                "source": "AI Semantic Crawler"
            })
            valid_jobs.append(j)
            
            return valid_jobs

    async def scrape(self, context):
        """
        Main entry point for AI Crawler.
        Iterates over all universities and runs the AI-scout crawling.
        """
        print(f"\n🚀 Starting AI-Powered Semantic Crawl ({len(self.universities)} universities)...")
        print(f"🤖 Scout: Gemini 1.5 Flash")
        
        # We use a browser context directly
        # The parent 'scrape' takes 'browser', but main.py passes 'context' to some scrapers
        # DeepUniversityCrawler.scrape takes 'browser' and makes new page.
        # Check main.py argument: 'context' is passed to uni_scraper.scrape(context) ??
        # No, main.py: uni_scraper = UniversityScraper... await uni_scraper.scrape(context)
        
        # Wait, let's check main.py line 175:
        # uni_jobs = await uni_scraper.scrape(context)
        
        # But DeepUniversityCrawler.scrape (line 1214) definition: async def scrape(self, browser):
        # And line 1216: page = await browser.new_page()
        # 'context' object has .new_page() too. So it works.
        
        total_positions = []
        
        for uni_data in self.universities:
            # Handle string vs dict input
            if isinstance(uni_data, str):
                uni = {"name": uni_data, "url": uni_data if uni_data.startswith("http") else f"https://www.{uni_data}"}
            else:
                uni = uni_data
                
            await self.crawl_university(context, uni)
            # jobs are stored in self.jobs
            
        print(f"🎓 AI Crawl Complete. Total positions found: {len(self.jobs)}")
        return self.jobs
