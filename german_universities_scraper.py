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
    
    async def scrape_university_portal(self, page, uni, position_type="phd"):
        """Scrape a single university's job portal"""
        name = uni['name']
        job_url = uni['job_portal_url']
        base_url = uni['base_url']
        
        print(f"  Scraping {name} ({position_type})...")
        
        try:
            # Navigate to job portal
            await page.goto(job_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Extract job listings - using generic selectors
            jobs_data = await page.evaluate('''({position_type}) => {
                const results = [];
                const seen = new Set();
                const type = position_type;
                
                // Keywords based on position type
                let typeKeywords = [];
                let excludeKeywords = [];
                
                if (type === 'phd') {
                    typeKeywords = ['phd', 'ph.d', 'doctoral', 'doctorate', 'doktorand', 'doktorandin', 'promotionsstelle', 'wissenschaftliche mitarbeiter'];
                    excludeKeywords = ['postdoc', 'post-doc', 'professor', 'secretary', 'office'];
                } else {
                    typeKeywords = ['postdoc', 'post-doc', 'post doctoral', 'research associate', 'fellow', 'tenure track', 'assistant professor', 'group leader'];
                    excludeKeywords = ['phd student', 'doctoral candidate', 'secretary', 'office'];
                }
                
                // Find all links
                const links = document.querySelectorAll('a');
                
                links.forEach(link => {
                    const text = link.innerText.trim().toLowerCase();
                    const href = link.href;
                    
                    if (!href || seen.has(href) || text.length < 10 || text.length > 300) {
                        return;
                    }
                    
                    // Check inclusion
                    if (typeKeywords.some(kw => text.includes(kw))) {
                        // Check exclusion
                        if (!excludeKeywords.some(ex => text.includes(ex))) {
                            seen.add(href);
                            results.push({
                                title: link.innerText.trim(),
                                url: href
                            });
                        }
                    }
                });
                
                // Also check for job containers
                const containers = document.querySelectorAll(
                    '[class*="job"], [class*="stelle"], [class*="position"], ' +
                    '[class*="vacancy"], article, .listing'
                );
                
                containers.forEach(container => {
                    const text = container.innerText.toLowerCase();
                    
                    if (!typeKeywords.some(kw => text.includes(kw))) {
                        return;
                    }
                    
                    if (excludeKeywords.some(ex => text.includes(ex))) {
                        return;
                    }
                    
                    const link = container.querySelector('a');
                    if (link && link.href && !seen.has(link.href)) {
                        seen.add(link.href);
                        
                        // Try to find title
                        const titleEl = container.querySelector('h1, h2, h3, h4, .title');
                        const title = titleEl ? titleEl.innerText.trim() : 
                                     link.innerText.trim() || (type === 'phd' ? 'PhD Position' : 'PostDoc Position');
                        
                        results.push({
                            title: title,
                            url: link.href
                        });
                    }
                });
                
                return results;
            }''', position_type)
            
            if len(jobs_data) > 0:
                print(f"    Found {len(jobs_data)} positions at {name}")
            
            for job in jobs_data:
                # Double check with Python (redundant but safe)
                title_lower = job['title'].lower()
                
                if position_type == "phd":
                    if any(skip in title_lower for skip in ['postdoc', 'professor', 'associate professor']):
                        continue
                else:
                    if 'phd student' in title_lower or 'doctoral candidate' in title_lower:
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
    
    async def scrape(self, browser, position_type="phd"):
        """Scrape all German universities"""
        print("=" * 60)
        print(f"SCRAPING GERMAN UNIVERSITIES (35+ institutions) - Type: {position_type}")
        print("=" * 60)
        
        page = await browser.new_page()
        
        for uni in self.universities:
            await self.scrape_university_portal(page, uni, position_type)
            await asyncio.sleep(1)  # Be polite
        
        await page.close()
        
        print(f"\n✅ German Universities: Total {len(self.jobs)} positions found")
        return self.jobs
