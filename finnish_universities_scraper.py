"""
Finnish Universities Scraper
Scrapes Finnish universities for PhD positions
"""

import asyncio
from datetime import datetime
from analyzer import KeywordAnalyzer


class FinnishUniversitiesScraper:
    """Scrape Finnish universities for PhD positions"""
    
    def __init__(self, analyzer: KeywordAnalyzer):
        self.analyzer = analyzer
        self.jobs = []
        
        # Major Finnish universities with English pages
        self.universities = [
            {
                "name": "University of Helsinki",
                "base_url": "https://www.helsinki.fi/en",
                "job_url": "https://www.helsinki.fi/en/open-positions"
            },
            {
                "name": "Aalto University",
                "base_url": "https://www.aalto.fi/en",
                "job_url": "https://www.aalto.fi/en/open-positions"
            },
            {
                "name": "University of Turku",
                "base_url": "https://www.utu.fi/en",
                "job_url": "https://www.utu.fi/en/university/jobs-at-university"
            },
            {
                "name": "University of Oulu",
                "base_url": "https://www.oulu.fi/en",
                "job_url": "https://www.oulu.fi/en/for-applicants/open-positions"
            },
            {
                "name": "Tampere University",
                "base_url": "https://www.tuni.fi/en",
                "job_url": "https://www.tuni.fi/en/about-us/careers"
            },
            {
                "name": "University of Jyväskylä",
                "base_url": "https://www.jyu.fi/en",
                "job_url": "https://www.jyu.fi/en/university/vacancies"
            },
            {
                "name": "University of Eastern Finland",
                "base_url": "https://www.uef.fi/en",
                "job_url": "https://www.uef.fi/en/open-positions"
            },
            {
                "name": "Lappeenranta-Lahti University of Technology (LUT)",
                "base_url": "https://www.lut.fi/en",
                "job_url": "https://www.lut.fi/en/about-us/join-us"
            },
            {
                "name": "University of Vaasa",
                "base_url": "https://www.uwasa.fi/en",
                "job_url": "https://www.uwasa.fi/en/university/jobs-university"
            },
            {
                "name": "Åbo Akademi University",
                "base_url": "https://www.abo.fi/en",
                "job_url": "https://www.abo.fi/en/about-abo-akademi-university/vacant-positions/"
            },
            {
                "name": "Hanken School of Economics",
                "base_url": "https://www.hanken.fi/en",
                "job_url": "https://www.hanken.fi/en/about-hanken/work-hanken/open-positions"
            },
            {
                "name": "University of Lapland",
                "base_url": "https://www.ulapland.fi/EN",
                "job_url": "https://www.ulapland.fi/EN/Studying-and-Admission/Job-Opportunities"
            }
        ]
        
        print(f"Loaded {len(self.universities)} Finnish universities")
    
    async def scrape_university(self, page, uni):
        """Scrape a single Finnish university"""
        name = uni['name']
        job_url = uni['job_url']
        
        print(f"  Scraping {name}...")
        
        try:
            await page.goto(job_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Extract job listings
            jobs_data = await page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                
                // PhD keywords
                const phdKeywords = ['phd', 'ph.d', 'doctoral', 'doctorate', 
                                    'doctoral student', 'doctoral researcher',
                                    'graduate student', 'early-stage researcher'];
                
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
                
                // Check job containers
                const containers = document.querySelectorAll(
                    '[class*="job"], [class*="position"], [class*="vacancy"], ' +
                    'article, .listing, [class*="career"]'
                );
                
                containers.forEach(container => {
                    const text = container.innerText.toLowerCase();
                    
                    if (!phdKeywords.some(kw => text.includes(kw))) {
                        return;
                    }
                    
                    const link = container.querySelector('a');
                    if (link && link.href && !seen.has(link.href)) {
                        seen.add(link.href);
                        
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
            }''')
            
            if len(jobs_data) > 0:
                print(f"    Found {len(jobs_data)} positions at {name}")
            
            for job in jobs_data:
                # Filter
                title_lower = job['title'].lower()
                
                # Skip non-PhD
                if any(skip in title_lower for skip in ['postdoc', 'professor', 'associate professor']):
                    continue
                
                self.jobs.append({
                    "title": job['title'][:200],
                    "university": name,
                    "url": job['url'],
                    "found_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": f"Finnish Universities ({name})"
                })
                
        except Exception as e:
            print(f"    Error scraping {name}: {e}")
    
    async def scrape(self, browser):
        """Scrape all Finnish universities"""
        print("=" * 60)
        print("SCRAPING FINNISH UNIVERSITIES (12 institutions)")
        print("=" * 60)
        
        page = await browser.new_page()
        
        for uni in self.universities:
            await self.scrape_university(page, uni)
            await asyncio.sleep(1)
        
        await page.close()
        
        print(f"\n✅ Finnish Universities: Total {len(self.jobs)} positions found")
        return self.jobs
