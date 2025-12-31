"""
Faculty Scraper Module
Discovers professors and supervisors in specific research fields.
Scrapes university faculty directories, department pages, and research group pages.
"""
import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from analyzer import KeywordAnalyzer
from inquiry_detector import InquiryDetector


class FacultyScraper:
    """
    Scrapes university faculty directories to find professors
    working in specific research areas.
    """
    
    def __init__(self, analyzer: KeywordAnalyzer, universities: List[str], position_type: str = "phd"):
        """
        Args:
            analyzer: KeywordAnalyzer instance for matching research areas
            universities: List of university domain names or faculty page URLs
            position_type: "phd" or "postdoc"
        """
        self.analyzer = analyzer
        self.universities = universities
        self.position_type = position_type
        self.inquiry_detector = InquiryDetector()
        self.professors = []
        self.inquiry_opportunities = []
        
        # Common faculty directory URL patterns
        self.faculty_url_patterns = [
            "/faculty",
            "/people",
            "/staff",
            "/team",
            "/personnel",
            "/researchers",
            "/professors",
            "/mitarbeiter",  # German
            "/department/people",
            "/research/people",
        ]
        
    async def find_faculty_directory(self, page: Page, university_url: str) -> Optional[str]:
        """
        Attempt to find the faculty directory page for a university.
        
        Args:
            page: Playwright page object
            university_url: Base URL of university
        
        Returns:
            URL of faculty directory if found, None otherwise
        """
        # Parse university domain
        parsed = urlparse(university_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try common faculty directory patterns
        for pattern in self.faculty_url_patterns:
            test_url = urljoin(base_domain, pattern)
            try:
                response = await page.goto(test_url, timeout=10000, wait_until="domcontentloaded")
                if response and response.status == 200:
                    # Check if page looks like a faculty directory
                    page_text = await page.inner_text("body")
                    if self._looks_like_faculty_page(page_text):
                        print(f"  ✓ Found faculty directory: {test_url}")
                        return test_url
            except Exception:
                continue
        
        # Fallback: search main page for faculty links
        try:
            await page.goto(university_url, timeout=10000)
            faculty_link = await page.query_selector("a[href*='faculty'], a[href*='people'], a[href*='staff']")
            if faculty_link:
                href = await faculty_link.get_attribute("href")
                if href:
                    return urljoin(university_url, href)
        except Exception:
            pass
        
        return None
    
    def _looks_like_faculty_page(self, page_text: str) -> bool:
        """Check if page content looks like a faculty directory"""
        indicators = [
            "professor", "faculty", "staff", "researcher",
            "department of", "research group", "team member",
            "email", "office", "phone",
        ]
        page_lower = page_text.lower()
        matches = sum(1 for indicator in indicators if indicator in page_lower)
        return matches >= 3
    
    async def extract_professor_profiles(self, page: Page, faculty_url: str, university_name: str, country: str) -> List[Dict]:
        """
        Extract professor profiles from a faculty directory page.
        
        Args:
            page: Playwright page object
            faculty_url: URL of faculty directory
            university_name: Name of the university
            country: Country
        
        Returns:
            List of professor profile dicts
        """
        profiles = []
        
        try:
            await page.goto(faculty_url, timeout=15000, wait_until="networkidle")
            
            # Strategy 1: Look for structured faculty listings
            # Common patterns: <div class="faculty-member">, <div class="person">, etc.
            person_cards = await page.query_selector_all(
                "div.faculty, div.person, div.profile, div.staff-member, "
                "li.faculty, li.person, article.person, .team-member"
            )
            
            if person_cards:
                print(f"  Found {len(person_cards)} potential faculty members")
                for card in person_cards[:50]:  # Limit to first 50
                    profile = await self._extract_profile_from_card(card, university_name, country, faculty_url)
                    if profile:
                        profiles.append(profile)
            
            # Strategy 2: Look for links to individual faculty pages
            if len(profiles) < 5:  # If strategy 1 didn't work well
                faculty_links = await page.query_selector_all("a[href*='profile'], a[href*='~'], a[href*='/people/']")
                for link in faculty_links[:30]:  # Limit to 30 links
                    href = await link.get_attribute("href")
                    if href:
                        full_url = urljoin(faculty_url, href)
                        profile = await self._scrape_individual_faculty_page(page, full_url, university_name, country)
                        if profile:
                            profiles.append(profile)
        
        except Exception as e:
            print(f"  ⚠️ Error scraping {faculty_url}: {str(e)[:100]}")
        
        return profiles
    
    async def _extract_profile_from_card(self, card, university_name: str, country: str, base_url: str) -> Optional[Dict]:
        """Extract professor info from a faculty card/listing element"""
        try:
            # Extract name
            name_elem = await card.query_selector("h2, h3, h4, .name, .faculty-name, strong")
            name = await name_elem.inner_text() if name_elem else None
            
            if not name or len(name) < 3:
                return None
            
            # Extract title/position
            title_elem = await card.query_selector(".title, .position, .role, em, i")
            title = await title_elem.inner_text() if title_elem else "Professor"
            
            # Extract research areas/interests
            research_elem = await card.query_selector(".research, .interests, .expertise, .keywords, p")
            research_text = await research_elem.inner_text() if research_elem else ""
            
            # Extract personal page URL
            link_elem = await card.query_selector("a")
            personal_url = None
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    personal_url = urljoin(base_url, href)
            
            # Extract email
            email_elem = await card.query_selector("a[href^='mailto:']")
            email = None
            if email_elem:
                mailto = await email_elem.get_attribute("href")
                email = mailto.replace("mailto:", "") if mailto else None
            
            # Check if research areas match keywords
            if not self._matches_keywords(name + " " + title + " " + research_text):
                return None
            
            return {
                "name": name.strip(),
                "title": title.strip() if title else "Professor",
                "university": university_name,
                "country": country,
                "research_areas": research_text.strip()[:200] if research_text else "N/A",
                "url": personal_url or base_url,
                "email": email or "N/A",
                "source": "Faculty Directory"
            }
        
        except Exception:
            return None
    
    async def _scrape_individual_faculty_page(self, page: Page, url: str, university_name: str, country: str) -> Optional[Dict]:
        """Scrape an individual faculty member's page"""
        try:
            response = await page.goto(url, timeout=10000, wait_until="domcontentloaded")
            if not response or response.status != 200:
                return None
            
            page_text = await page.inner_text("body")
            
            # Extract name (usually in h1 or h2)
            name_elem = await page.query_selector("h1, h2")
            name = await name_elem.inner_text() if name_elem else "Unknown"
            
            # Check for keyword match
            if not self._matches_keywords(page_text):
                return None
            
            # Check for inquiry signals (accepting PhD students)
            signal_data = self.inquiry_detector.scan_page_for_inquiry_signals(page_text, self.position_type)
            
            # Extract research interests
            research_section = await page.query_selector("div.research, section.research, #research, .interests")
            research_text = await research_section.inner_text() if research_section else page_text[:500]
            
            # Extract email
            contact_info = self.inquiry_detector.extract_contact_info(page_text)
            
            profile = {
                "name": name.strip(),
                "title": "Professor",
                "university": university_name,
                "country": country,
                "research_areas": research_text.strip()[:200],
                "url": url,
                "email": contact_info.get("email", "N/A"),
                "source": "Faculty Page"
            }
            
            # If inquiry signal detected, add to inquiry opportunities
            if signal_data["has_signal"]:
                inquiry_opp = self.inquiry_detector.build_inquiry_opportunity(
                    professor_name=name.strip(),
                    university=university_name,
                    page_url=url,
                    research_areas=research_text.strip()[:200],
                    country=country,
                    signal_data=signal_data,
                    contact_info=contact_info
                )
                self.inquiry_opportunities.append(inquiry_opp)
                print(f"  💡 Inquiry opportunity detected: {name} at {university_name}")
            
            return profile
        
        except Exception:
            return None
    
    def _matches_keywords(self, text: str) -> bool:
        """Check if text contains any of the search keywords"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check against analyzer keywords
        for keyword in self.analyzer.keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    async def scrape_university(self, page: Page, university_url: str, university_name: str, country: str):
        """
        Scrape a single university for faculty members.
        
        Args:
            page: Playwright page
            university_url: Base URL of university or faculty page
            university_name: Name of university
            country: Country
        """
        print(f"\n📚 Scraping faculty from {university_name} ({country})...")
        
        # Find faculty directory
        faculty_url = await self.find_faculty_directory(page, university_url)
        
        if not faculty_url:
            print(f"  ⚠️ Could not find faculty directory for {university_name}")
            return
        
        # Extract professor profiles
        profiles = await self.extract_professor_profiles(page, faculty_url, university_name, country)
        
        # Add to results
        self.professors.extend(profiles)
        print(f"  ✓ Found {len(profiles)} relevant professors")
    
    async def scrape(self, browser):
        """
        Main scraping method - scrapes all universities.
        
        Args:
            browser: Playwright browser instance
        """
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"\n{'='*60}")
        print(f"🎓 FACULTY SCRAPER - Finding professors in your field")
        print(f"{'='*60}")
        print(f"Keywords: {', '.join(self.analyzer.keywords[:5])}")
        print(f"Universities to scrape: {len(self.universities)}")
        
        for i, university_data in enumerate(self.universities[:20], 1):  # Limit to 20 universities
            # Parse university data (could be URL or dict with name/country)
            if isinstance(university_data, str):
                university_url = university_data
                university_name = urlparse(university_url).netloc
                country = "Unknown"
            elif isinstance(university_data, dict):
                university_url = university_data.get("url", "")
                university_name = university_data.get("name", "Unknown")
                country = university_data.get("country", "Unknown")
            else:
                continue
            
            try:
                await self.scrape_university(page, university_url, university_name, country)
                await asyncio.sleep(2)  # Polite delay between universities
            except Exception as e:
                print(f"  ❌ Error scraping {university_name}: {str(e)[:100]}")
                continue
        
        await context.close()
        
        print(f"\n{'='*60}")
        print(f"✅ FACULTY SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total professors found: {len(self.professors)}")
        print(f"Inquiry opportunities: {len(self.inquiry_opportunities)}")
        
        return {
            "professors": self.professors,
            "inquiry_opportunities": self.inquiry_opportunities
        }


def load_universities_from_file(filename: str = "universities.txt") -> List[Dict]:
    """
    Load universities from file and structure them.
    
    Returns:
        List of dicts with keys: name, url, country
    """
    import os
    
    if not os.path.exists(filename):
        return []
    
    universities = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Try to parse line (format: "University Name | URL | Country")
            parts = [p.strip() for p in line.split("|")]
            
            if len(parts) >= 2:
                universities.append({
                    "name": parts[0],
                    "url": parts[1],
                    "country": parts[2] if len(parts) > 2 else "Unknown"
                })
            elif line.startswith("http"):
                # Just a URL
                universities.append({
                    "name": urlparse(line).netloc,
                    "url": line,
                    "country": "Unknown"
                })
    
    return universities
