import asyncio
from playwright.async_api import async_playwright
import urllib.parse
from analyzer import KeywordAnalyzer
from datetime import datetime

class BaseScraper:
    def __init__(self, analyzer: KeywordAnalyzer):
        self.analyzer = analyzer
        self.jobs = [] # List of dicts

    async def scrape(self, browser):
        raise NotImplementedError

class GlobalPortalScraper(BaseScraper):
    def __init__(self, analyzer: KeywordAnalyzer, custom_keywords=None):
        super().__init__(analyzer)
        
        # If custom_keywords provided (Mode 2), use ONLY those
        # Otherwise use hardcoded default keywords (Mode 1)
        if custom_keywords:
            self.search_terms = custom_keywords
        else:
            # Expanded search terms for your CV keywords (Mode 1 default)
            self.search_terms = [
                "6G", "5G", "Open RAN", "O-RAN", "vRAN",
                "Network Slicing", "ISAC", "Terahertz", "THz",
                "Zero Trust", "Post-Quantum", "PQC",
                "Federated Learning", "Edge AI", "Digital Twin",
                "Massive MIMO", "Beamforming", "Signal Processing",
                "Network Security", "IoT Security", "SDN", "NFV",
                "Satellite Communications", "NTN", "Wireless Communications", "electrical Engineering", "electronic engineering", "communication systems",
                "IOT", "Zero Trust", "communication engineering"]
        
        # Target countries - Germany, Austria, Switzerland (DACH) + Nordic
        self.target_countries = [
            "Germany", "Austria", "Switzerland",
            "Norway", "Finland", "Sweden", "Denmark"
        ]
        
    async def scrape_findaphd(self, page):
        print("Scraping FindAPhD (DACH + Nordic focus)...")
        
        # Cookie banner handling
        try:
            await page.goto("https://www.findaphd.com", timeout=30000)
            cookie_btn = await page.query_selector("#onetrust-accept-btn-handler")
            if cookie_btn:
                await cookie_btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass
        
        seen_urls = set()
        
        # Country-specific URL slugs for FindAPhD
        country_slugs = {
            "Germany": "germany",
            "Austria": "austria", 
            "Switzerland": "switzerland",
            "Norway": "norway",
            "Finland": "finland",
            "Sweden": "sweden",
            "Denmark": "denmark"
        }
        
        # Search each country + keyword combination
        for country, slug in country_slugs.items():
            for term in self.search_terms:
                # URL format: https://www.findaphd.com/phds/germany/?Keywords=6G
                url = f"https://www.findaphd.com/phds/{slug}/?Keywords={urllib.parse.quote(term)}"
                print(f"Searching FindAPhD [{country}] for: {term}")
                
                try:
                    await page.goto(url, timeout=45000)
                    
                    try:
                        await page.wait_for_selector("#SearchResults, .resultsRow", timeout=10000)
                    except:
                        print(f"  No results for {term} in {country}")
                        continue

                    jobs_data = await page.evaluate('''() => {
                        const results = [];
                        const rows = document.querySelectorAll('.resultsRow');
                        
                        rows.forEach(row => {
                            const cardLink = row.querySelector('a.card');
                            if (!cardLink) return;
                            
                            const titleEl = cardLink.querySelector('h3');
                            const title = titleEl ? titleEl.innerText.trim() : '';
                            const link = cardLink.getAttribute('href') || '';
                            
                            const uniEl = row.querySelector('.phd-result__dept-inst--title');
                            const uni = uniEl ? uniEl.innerText.trim() : 'Unknown';
                            const fullText = cardLink.innerText;
                            
                            if (title.length > 5 && link) {
                                results.push({ title, fullText, link, uni });
                            }
                        });
                        
                        return results;
                    }''')
                    
                    if len(jobs_data) > 0:
                        print(f"  Found {len(jobs_data)} jobs for '{term}' in {country}")
                    
                    for job in jobs_data:
                        link = job['link']
                        if link.startswith("/"):
                            link = "https://www.findaphd.com" + link
                        
                        if link in seen_urls:
                            continue
                        seen_urls.add(link)
                        
                        self.jobs.append({
                            "title": job['title'],
                            "university": job['uni'],
                            "url": link,
                            "found_date": datetime.now().strftime("%Y-%m-%d"),
                            "source": f"FindAPhD ({country})"
                        })
                        
                except Exception as e:
                    print(f"Error scraping FindAPhD {country}/{term}: {e}")

    async def scrape_academicpositions(self, page):
        print("Scraping Academic Positions...")
        base_url = "https://academicpositions.com/find-jobs"
        
        for term in self.search_terms[:10]:  # Limit to avoid rate limiting
            url = f"{base_url}?q={urllib.parse.quote(term + ' PhD')}"
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)  # Extra wait for JS
                
                # Get all job links
                links = await page.evaluate('''() => {
                    const results = [];
                    const items = document.querySelectorAll('a[href*="/ad/"], a[href*="/jobs/"], .job-listing a, article a');
                    items.forEach(item => {
                        const title = item.innerText.trim();
                        if (title.length > 10 && !title.includes('Sign') && !title.includes('Log')) {
                            results.push({title: title, url: item.href});
                        }
                    });
                    return results;
                }''')
                
                print(f"  Found {len(links)} potential jobs for '{term}'")
                
                for job in links:
                    combined_text = job['title']
                    if self.analyzer.is_relevant(combined_text) or term.lower() in combined_text.lower():
                        self.jobs.append({
                            "title": job['title'],
                            "university": "AcademicPositions",
                            "url": job['url'],
                            "found_date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "AcademicPositions"
                        })
            except Exception as e:
                print(f"Error scraping AcademicPositions for {term}: {e}")

    async def scrape_euraxess(self, page):
        """Scrape EURAXESS for PhD positions in DACH + Nordic countries"""
        print("Scraping EURAXESS (DACH + Nordic focus)...")
        
        # EURAXESS country codes
        country_codes = {
            "Germany": "de",
            "Austria": "at",
            "Switzerland": "ch",
            "Norway": "no",
            "Finland": "fi",
            "Sweden": "se",
            "Denmark": "dk"
        }
        
        seen_urls = set()
        
        for country, code in country_codes.items():
            # EURAXESS search URL with country filter
            url = f"https://euraxess.ec.europa.eu/jobs/search?keywords=PhD&countries%5B%5D={code}"
            print(f"Searching EURAXESS [{country}]...")
            
            try:
                await page.goto(url, timeout=45000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                # Get job listings
                jobs_data = await page.evaluate('''() => {
                    const results = [];
                    const items = document.querySelectorAll('.views-row, .job-item, article');
                    
                    items.forEach(item => {
                        const titleEl = item.querySelector('h2 a, h3 a, .title a, a.job-title');
                        if (!titleEl) return;
                        
                        const title = titleEl.innerText.trim();
                        const link = titleEl.href || titleEl.getAttribute('href') || '';
                        
                        const orgEl = item.querySelector('.organization, .employer, .institution');
                        const org = orgEl ? orgEl.innerText.trim() : 'Unknown';
                        
                        if (title.length > 5 && link) {
                            results.push({ title, link, org });
                        }
                    });
                    
                    return results;
                }''')
                
                if len(jobs_data) > 0:
                    print(f"  Found {len(jobs_data)} jobs in {country}")
                
                for job in jobs_data:
                    link = job['link']
                    if link.startswith("/"):
                        link = "https://euraxess.ec.europa.eu" + link
                    
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    # Check relevance
                    if self.analyzer.is_relevant(job['title']):
                        self.jobs.append({
                            "title": job['title'],
                            "university": job['org'],
                            "url": link,
                            "found_date": datetime.now().strftime("%Y-%m-%d"),
                            "source": f"EURAXESS ({country})"
                        })
                        
            except Exception as e:
                print(f"Error scraping EURAXESS {country}: {e}")

    async def scrape_academics_de(self, page):
        """Scrape academics.de - Primary DACH academic job portal"""
        print("Scraping academics.de (DACH focus)...")
        
        seen_urls = set()
        
        for term in self.search_terms[:15]:  # Limit to avoid rate limiting
            # academics.de search URL
            url = f"https://www.academics.de/jobs/doktorand?keywords={urllib.parse.quote(term)}"
            print(f"  Searching academics.de for: {term}")
            
            try:
                await page.goto(url, timeout=45000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                jobs_data = await page.evaluate('''() => {
                    const results = [];
                    const items = document.querySelectorAll('.job-item, .result-item, article, .listing-item, [class*="job"]');
                    
                    items.forEach(item => {
                        const titleEl = item.querySelector('h2 a, h3 a, .title a, a.job-title, [class*="title"] a');
                        if (!titleEl) return;
                        
                        const title = titleEl.innerText.trim();
                        const link = titleEl.href || titleEl.getAttribute('href') || '';
                        
                        const orgEl = item.querySelector('.employer, .company, .organization, [class*="employer"]');
                        const org = orgEl ? orgEl.innerText.trim() : 'Unknown';
                        
                        if (title.length > 5 && link) {
                            results.push({ title, link, org });
                        }
                    });
                    
                    return results;
                }''')
                
                if len(jobs_data) > 0:
                    print(f"    Found {len(jobs_data)} jobs for '{term}'")
                
                for job in jobs_data:
                    link = job['link']
                    if link.startswith("/"):
                        link = "https://www.academics.de" + link
                    
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    self.jobs.append({
                        "title": job['title'],
                        "university": job['org'],
                        "url": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "academics.de"
                    })
                    
            except Exception as e:
                print(f"Error scraping academics.de for {term}: {e}")

    async def scrape_daad(self, page):
        """Scrape DAAD PhDGermany database"""
        print("Scraping DAAD PhDGermany...")
        
        # DAAD PhD search URL
        url = "https://www.daad.de/en/study-and-research-in-germany/phd-studies-and-research/phd-germany/"
        
        try:
            await page.goto(url, timeout=45000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # Try to find the PhD database link or listings
            jobs_data = await page.evaluate('''() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="phd"], a[href*="doctoral"], a[href*="promotion"]');
                
                links.forEach(link => {
                    const title = link.innerText.trim();
                    const href = link.href || '';
                    
                    if (title.length > 10 && href && !href.includes('javascript')) {
                        results.push({ title, link: href, org: 'DAAD' });
                    }
                });
                
                return results;
            }''')
            
            if len(jobs_data) > 0:
                print(f"  Found {len(jobs_data)} DAAD resources")
            
            for job in jobs_data:
                if self.analyzer.is_relevant(job['title']):
                    self.jobs.append({
                        "title": job['title'],
                        "university": "DAAD",
                        "url": job['link'],
                        "found_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "DAAD PhDGermany"
                    })
                    
        except Exception as e:
            print(f"Error scraping DAAD: {e}")

    async def scrape_ieee(self, page):
        """Scrape IEEE Jobs for PhD/research positions"""
        print("Scraping IEEE Jobs...")
        
        seen_urls = set()
        
        for term in self.search_terms[:10]:
            # IEEE Jobs search URL
            url = f"https://jobs.ieee.org/jobs/?keywords={urllib.parse.quote(term + ' PhD')}&location=Germany"
            print(f"  Searching IEEE Jobs for: {term}")
            
            try:
                await page.goto(url, timeout=45000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                jobs_data = await page.evaluate('''() => {
                    const results = [];
                    const items = document.querySelectorAll('.job-item, .result, article, [class*="job"], .listing');
                    
                    items.forEach(item => {
                        const titleEl = item.querySelector('h2 a, h3 a, .title a, a[class*="title"]');
                        if (!titleEl) return;
                        
                        const title = titleEl.innerText.trim();
                        const link = titleEl.href || titleEl.getAttribute('href') || '';
                        
                        const orgEl = item.querySelector('.company, .employer, [class*="company"]');
                        const org = orgEl ? orgEl.innerText.trim() : 'IEEE';
                        
                        if (title.length > 5 && link) {
                            results.push({ title, link, org });
                        }
                    });
                    
                    return results;
                }''')
                
                if len(jobs_data) > 0:
                    print(f"    Found {len(jobs_data)} jobs for '{term}'")
                
                for job in jobs_data:
                    if job['link'] in seen_urls:
                        continue
                    seen_urls.add(job['link'])
                    
                    self.jobs.append({
                        "title": job['title'],
                        "university": job['org'],
                        "url": job['link'],
                        "found_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "IEEE Jobs"
                    })
                    
            except Exception as e:
                print(f"Error scraping IEEE Jobs for {term}: {e}")

    async def scrape_applykite(self, page):
        """Scrape ApplyKite for PhD positions in Germany/Europe"""
        print("Scraping ApplyKite...")
        
        # ApplyKite PhD positions
        urls = [
            "https://applykite.com/phd-positions/germany",
            "https://applykite.com/phd-positions/austria",
            "https://applykite.com/phd-positions/switzerland"
        ]
        
        seen_urls = set()
        
        for base_url in urls:
            print(f"  Checking {base_url}...")
            try:
                await page.goto(base_url, timeout=45000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                jobs_data = await page.evaluate('''() => {
                    const results = [];
                    const items = document.querySelectorAll('article, .position, .job-card, [class*="job"], [class*="position"], .listing');
                    
                    items.forEach(item => {
                        const titleEl = item.querySelector('h2 a, h3 a, .title a, a[class*="title"], h2, h3');
                        if (!titleEl) return;
                        
                        const title = titleEl.innerText.trim();
                        let link = titleEl.href || titleEl.getAttribute('href') || '';
                        if (!link) {
                            const parentLink = item.querySelector('a');
                            link = parentLink ? parentLink.href : '';
                        }
                        
                        const orgEl = item.querySelector('.university, .institution, .employer, [class*="uni"]');
                        const org = orgEl ? orgEl.innerText.trim() : 'ApplyKite';
                        
                        if (title.length > 5 && link) {
                            results.push({ title, link, org });
                        }
                    });
                    
                    return results;
                }''')
                
                if len(jobs_data) > 0:
                    print(f"    Found {len(jobs_data)} positions")
                
                for job in jobs_data:
                    link = job['link']
                    if link.startswith("/"):
                        link = "https://applykite.com" + link
                    
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    # Check if it's a PhD position (not PostDoc)
                    title_lower = job['title'].lower()
                    if 'postdoc' in title_lower or 'professor' in title_lower:
                        continue
                    
                    self.jobs.append({
                        "title": job['title'],
                        "university": job['org'],
                        "url": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "ApplyKite"
                    })
                    
            except Exception as e:
                print(f"Error scraping ApplyKite: {e}")

    async def scrape(self, browser):
        page = await browser.new_page()
        await self.scrape_findaphd(page)
        await self.scrape_euraxess(page)
        await self.scrape_academics_de(page)
        await self.scrape_daad(page)
        await self.scrape_ieee(page)
        await self.scrape_applykite(page)
        await self.scrape_academicpositions(page)
        await page.close()
        return self.jobs

class DeepUniversityCrawler(BaseScraper):
    """
    Comprehensive BFS crawler that deeply explores university websites
    to find PhD positions, professor pages, research labs, and any
    mention of open PhD positions.
    """
    
    def __init__(self, analyzer: KeywordAnalyzer, universities):
        super().__init__(analyzer)
        self.universities = universities
        
        # Crawling configuration
        self.max_depth = 3          # How many levels deep to crawl
        self.max_pages = 50         # Max pages per university (reduced for reasonable time)
        self.crawl_delay = 0.3      # Seconds between requests
        
        # High-priority URL patterns (crawl first)
        self.priority_patterns = [
            'career', 'job', 'position', 'vacanc', 'stellen', 'arbeit',
            'phd', 'doctoral', 'doktorand', 'promov', 'dissertation',
            'research', 'wissenschaft', 'forsch',
            'people', 'faculty', 'professor', 'staff', 'team', 'member',
            'lab', 'group', 'institut', 'department', 'lehrstuhl',
            'open', 'hiring', 'join', 'apply', 'bewerbung'
        ]
        
        # PhD-related keywords to detect on pages
        self.phd_keywords = [
            'phd position', 'phd student', 'doctoral candidate', 
            'doktorand', 'doktorandin', 'promotionsstelle',
            'graduate research', 'dissertation', 'doctoral program',
            'seeking phd', 'open phd', 'phd opening', 'phd vacancy',
            'looking for phd', 'wissenschaftlicher mitarbeiter',
            'wissenschaftliche mitarbeiterin', 'forschungsstelle',
            'open to receiving cv', 'apply for phd', 'phd applications',
            'doctoral position', 'research assistant', 'phd candidate',
            'fully funded phd', 'phd scholarship', 'phd fellowship',
            'join our group', 'join our team', 'join our lab',
            'prospective phd', 'phd opportunities', 'phd program',
            'we are hiring', 'positions available', 'open positions',
            'stellenangebot', 'stellenausschreibung', 'stelle frei'
        ]
        
        # Keywords indicating professor/group pages seeking students
        self.professor_seeking_keywords = [
            'i am looking for', 'we are looking for', 'seeking motivated',
            'open for applications', 'accepting phd students',
            'contact me if interested', 'send your cv',
            'motivated students', 'prospective students welcome',
            'phd positions available in my group', 'open for phd',
            'interested in joining', 'currently recruiting',
            'suche doktorand', 'doktoranden gesucht'
        ]
        
        # URL patterns to skip
        self.skip_patterns = [
            '.pdf', '.doc', '.ppt', '.xls', '.zip', '.png', '.jpg', '.gif',
            'mailto:', 'javascript:', 'tel:', '#', 'facebook.com', 'twitter.com',
            'linkedin.com', 'youtube.com', 'instagram.com', 'login', 'logout',
            'impressum', 'datenschutz', 'privacy', 'cookie', 'legal'
        ]

    def _is_valid_url(self, url, base_domain):
        """Check if URL is valid for crawling"""
        if not url or len(url) < 10:
            return False
        
        # Skip external links
        if base_domain not in url:
            return False
        
        # Skip unwanted patterns
        url_lower = url.lower()
        for skip in self.skip_patterns:
            if skip in url_lower:
                return False
        
        return True

    def _calculate_priority(self, url):
        """Calculate crawl priority for a URL (higher = better)"""
        url_lower = url.lower()
        priority = 0
        
        for pattern in self.priority_patterns:
            if pattern in url_lower:
                priority += 10
        
        # Extra priority for direct PhD mentions
        if 'phd' in url_lower or 'doktorand' in url_lower:
            priority += 50
        
        # Extra priority for career/job pages
        if 'career' in url_lower or 'job' in url_lower or 'stellen' in url_lower:
            priority += 30
        
        # Extra priority for people/professor pages
        if 'people' in url_lower or 'professor' in url_lower or 'team' in url_lower:
            priority += 20
        
        return priority

    async def _extract_links(self, page, base_domain):
        """Extract all valid internal links from the current page"""
        try:
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(href => href && href.startsWith('http'));
            }''')
            
            valid_links = []
            for link in links:
                if self._is_valid_url(link, base_domain):
                    valid_links.append(link)
            
            return valid_links
        except:
            return []

    async def _scan_page_for_phd(self, page, url, uni_domain):
        """Scan current page for PhD-related content"""
        found_positions = []
        
        try:
            # Get page text content
            page_text = await page.evaluate('() => document.body.innerText.toLowerCase()')
            page_title = await page.title()
            
            # Check if page mentions PhD keywords
            has_phd_mention = False
            for keyword in self.phd_keywords:
                if keyword in page_text:
                    has_phd_mention = True
                    break
            
            if not has_phd_mention:
                return found_positions
            
            # Found PhD mention - extract relevant links/positions
            positions = await page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                
                // STRICT PhD keywords only
                const phdKeywords = ['phd', 'ph.d', 'doctoral', 'doctorate', 
                                    'doktorand', 'doktorandin', 'promotionsstelle',
                                    'dissertation'];
                
                // Keywords to EXCLUDE
                const excludeKeywords = ['postdoc', 'post-doc', 'professor', 'tenure',
                                        'senior engineer', 'software engineer', 'manager',
                                        'developer', 'programmer', 'consultant'];
                
                // Method 1: Find links with STRICT PhD keywords
                document.querySelectorAll('a').forEach(a => {
                    const text = a.innerText.trim().toLowerCase();
                    const href = a.href;
                    
                    if (href && !seen.has(href) && text.length > 10 && text.length < 200) {
                        // Check for exclusions first
                        if (excludeKeywords.some(ex => text.includes(ex))) {
                            return;
                        }
                        
                        // Must have explicit PhD keyword
                        if (phdKeywords.some(kw => text.includes(kw))) {
                            seen.add(href);
                            results.push({ title: a.innerText.trim(), url: href, source: 'phd_link' });
                        }
                    }
                });
                
                // Method 2: Find job listing containers with PhD mentions
                const containers = document.querySelectorAll(
                    '[class*="job"], [class*="position"], [class*="vacancy"], [class*="career"]'
                );
                containers.forEach(container => {
                    const link = container.querySelector('a');
                    if (link && link.href && !seen.has(link.href)) {
                        const text = container.innerText.toLowerCase();
                        
                        // Check for exclusions
                        if (excludeKeywords.some(ex => text.includes(ex))) {
                            return;
                        }
                        
                        // Must have explicit PhD keyword
                        if (phdKeywords.some(kw => text.includes(kw))) {
                            seen.add(link.href);
                            const title = link.innerText.trim() || 
                                         container.querySelector('h2, h3, h4, .title')?.innerText?.trim() || 
                                         'PhD Position';
                            results.push({
                                title: title,
                                url: link.href,
                                source: 'phd_container'
                            });
                        }
                    }
                });
                
                return results;
            }''')
            
            for pos in positions:
                if len(pos['title']) > 5 and pos['url']:
                    # Filter out non-PhD positions
                    title_lower = pos['title'].lower()
                    if 'postdoc' in title_lower or 'professor' in title_lower or 'tenure' in title_lower:
                        continue
                    
                    found_positions.append({
                        "title": pos['title'][:200],
                        "university": uni_domain,
                        "url": pos['url'],
                        "found_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": f"University Deep Crawl ({pos['source']})"
                    })
            
            # Method 3: Check if this is a professor page seeking students
            for seeking_kw in self.professor_seeking_keywords:
                if seeking_kw in page_text:
                    # This page is advertising for PhD students
                    found_positions.append({
                        "title": f"Professor/Group Page: {page_title[:100]}",
                        "university": uni_domain,
                        "url": url,
                        "found_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "Professor Page (seeking students)"
                    })
                    break
                    
        except Exception as e:
            pass
        
        return found_positions

    async def deep_crawl_university(self, page, uni_domain):
        """BFS deep crawl of a university website"""
        print(f"🔍 Deep crawling: {uni_domain}")
        
        # Prepare base URL
        if not uni_domain.startswith("http"):
            base_url = f"https://www.{uni_domain}"
        else:
            base_url = uni_domain
        
        base_domain = uni_domain.replace("www.", "")
        
        # BFS data structures
        visited = set()
        found_positions = []
        
        # Priority queue: (priority, depth, url)
        # Using list and sorting for simplicity
        queue = [(100, 0, base_url)]
        
        pages_crawled = 0
        
        while queue and pages_crawled < self.max_pages:
            # Sort by priority (descending) and depth (ascending)
            queue.sort(key=lambda x: (-x[0], x[1]))
            
            priority, depth, url = queue.pop(0)
            
            if url in visited:
                continue
            
            if depth > self.max_depth:
                continue
            
            visited.add(url)
            pages_crawled += 1
            
            try:
                # Visit page
                response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                
                if not response or response.status != 200:
                    continue
                
                await asyncio.sleep(self.crawl_delay)
                
                # Scan page for PhD positions
                positions = await self._scan_page_for_phd(page, url, uni_domain)
                
                # Deduplicate and add
                for pos in positions:
                    if pos['url'] not in visited:
                        found_positions.append(pos)
                
                # Extract links for further crawling
                if depth < self.max_depth:
                    links = await self._extract_links(page, base_domain)
                    
                    for link in links:
                        if link not in visited:
                            link_priority = self._calculate_priority(link)
                            queue.append((link_priority, depth + 1, link))
                
                # Progress indicator every 10 pages
                if pages_crawled % 10 == 0:
                    print(f"  📄 Crawled {pages_crawled} pages, found {len(found_positions)} positions...")
                    
            except Exception as e:
                continue
        
        print(f"  ✅ {uni_domain}: {pages_crawled} pages crawled, {len(found_positions)} positions found")
        
        return found_positions

    async def scrape(self, browser):
        """Main scraping method"""
        page = await browser.new_page()
        
        total_positions = 0
        
        for uni in self.universities:
            uni = uni.strip()
            if not uni or uni.startswith('#'):
                continue
            
            try:
                positions = await self.deep_crawl_university(page, uni)
                self.jobs.extend(positions)
                total_positions += len(positions)
            except Exception as e:
                print(f"  ❌ Error crawling {uni}: {e}")
        
        await page.close()
        
        print(f"\n🎓 Deep crawl complete: {total_positions} total positions from {len(self.universities)} universities")
        
        return self.jobs


# Alias for backwards compatibility
UniversityScraper = DeepUniversityCrawler

