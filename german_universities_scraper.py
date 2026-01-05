"""
German Universities Scraper
Dedicated scraper for 35+ German universities with known job portal URLs
"""

import asyncio
import json
from datetime import datetime
from analyzer import KeywordAnalyzer


class GermanUniversitiesScraper:
    """Scrape German university job portals for PhD positions"""
    
    def __init__(self, analyzer: KeywordAnalyzer, config_file="german_universities.json"):
        self.analyzer = analyzer
        self.jobs = []
        
        # Load university configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            self.universities = json.load(f)
        
        print(f"Loaded {len(self.universities)} German universities")
    
    async def scrape_university_portal(self, page, uni):
        """Scrape a single university's job portal"""
        name = uni['name']
        job_url = uni['job_portal_url']
        base_url = uni['base_url']
        
        print(f"  Scraping {name}...")
        
        try:
            # Navigate to job portal
            await page.goto(job_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Extract job listings - using generic selectors
            jobs_data = await page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                
                // PhD keywords
                const phdKeywords = ['phd', 'ph.d', 'doctoral', 'doctorate', 
                                    'doktorand', 'doktorandin', 'promotionsstelle',
                                    'wissenschaftliche mitarbeiter', 'wissenschaftlicher mitarbeiter'];
                
                // Find all links
                const links = document.querySelectorAll('a');
                
                links.forEach(link => {
                    const text = link.innerText.trim().toLowerCase();
                    const href = link.href;
                    
                    if (!href || seen.has(href) || text.length < 10 || text.length > 300) {
                        return;
                    }
                    
                    // Check if it mentions PhD
                    if (phdKeywords.some(kw => text.includes(kw))) {
                        seen.add(href);
                        results.push({
                            title: link.innerText.trim(),
                            url: href
                        });
                    }
                });
                
                // Also check for job containers
                const containers = document.querySelectorAll(
                    '[class*="job"], [class*="stelle"], [class*="position"], ' +
                    '[class*="vacancy"], article, .listing'
                );
                
                containers.forEach(container => {
                    const text = container.innerText.toLowerCase();
                    
                    if (!phdKeywords.some(kw => text.includes(kw))) {
                        return;
                    }
                    
                    const link = container.querySelector('a');
                    if (link && link.href && !seen.has(link.href)) {
                        seen.add(link.href);
                        
                        // Try to find title
                        const titleEl = container.querySelector('h1, h2, h3, h4, .title');
                        const title = titleEl ? titleEl.innerText.trim() : 
                                     link.innerText.trim() || 'PhD Position';
                        
                        results.push({
                            title: title,
                            url: link.href
                        });
                    }
                });
                
                return results;
            }'''            )
            
            if len(jobs_data) > 0:
                print(f"    Found {len(jobs_data)} positions at {name}")
            
            for job in jobs_data:
                # Additional filtering
                title_lower = job['title'].lower()
                
                # Skip non-PhD positions
                if any(skip in title_lower for skip in ['postdoc', 'professor', 'professor', 'office', 'secretary']):
                    continue
                
                self.jobs.append({
                    "title": job['title'][:200],
                    "university": name,
                    "url": job['url'],
                    "found_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": f"German Universities ({name})"
                })
                
        except Exception as e:
            print(f"    Error scraping {name}: {e}")
    
    async def scrape(self, browser):
        """Scrape all German universities"""
        print("=" * 60)
        print("SCRAPING GERMAN UNIVERSITIES (35+ institutions)")
        print("=" * 60)
        
        page = await browser.new_page()
        
        for uni in self.universities:
            await self.scrape_university_portal(page, uni)
            await asyncio.sleep(1)  # Be polite
        
        await page.close()
        
        print(f"\n✅ German Universities: Total {len(self.jobs)} positions found")
        return self.jobs
