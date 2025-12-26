"""
LinkedIn Scraper Module
Scrapes job postings from LinkedIn using Playwright with authentication.
"""
import os
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()


class LinkedInScraper:
    def __init__(self):
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.browser = None
        self.context = None
        self.page = None
    
    async def login(self):
        """Login to LinkedIn using Playwright"""
        try:
            print("🔐 Logging into LinkedIn...")
            await self.page.goto('https://www.linkedin.com/login', wait_until='networkidle')
            
            # Fill login form
            await self.page.fill('input#username', self.email)
            await self.page.fill('input#password', self.password)
            await self.page.click('button[type="submit"]')
            
            # Wait for navigation after login
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            
            # Check if login was successful
            if '/feed' in self.page.url or '/jobs' in self.page.url:
                print("✅ LinkedIn login successful")
                return True
            else:
                print("⚠️ LinkedIn login may have failed")
                return False
                
        except Exception as e:
            print(f"❌ LinkedIn login failed: {str(e)}")
            return False
    
    async def search_jobs(self, keywords: str, location: str = "Worldwide", job_type: str = "phd") -> List[Dict]:
        """
        Search for jobs on LinkedIn
        
        Args:
            keywords: Search keywords
            location: Job location
            job_type: 'phd' or 'postdoc'
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Construct search query
            search_query = f"{keywords} {job_type} position"
            base_url = f"https://www.linkedin.com/jobs/search/?keywords={search_query.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            
            print(f"🔍 Searching LinkedIn for: {search_query}")
            await self.page.goto(base_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Scroll to load more jobs
            for _ in range(3):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
            
            # Extract job listings
            job_cards = await self.page.query_selector_all('.job-search-card')
            
            for card in job_cards[:20]:  # Limit to 20 jobs
                try:
                    # Extract job details
                    title_elem = await card.query_selector('.base-search-card__title')
                    company_elem = await card.query_selector('.base-search-card__subtitle')
                    link_elem = await card.query_selector('a.base-card__full-link')
                    location_elem = await card.query_selector('.job-search-card__location')
                    
                    if title_elem and link_elem:
                        title = (await title_elem.inner_text()).strip()
                        company = (await company_elem.inner_text()).strip() if company_elem else "Unknown"
                        url = await link_elem.get_attribute('href')
                        location_text = (await location_elem.inner_text()).strip() if location_elem else location
                        
                        # Clean URL (remove tracking parameters)
                        if '?' in url:
                            url = url.split('?')[0]
                        
                        jobs.append({
                            'title': title,
                            'institution': company,
                            'location': location_text,
                            'url': url,
                            'source': 'LinkedIn'
                        })
                
                except Exception as e:
                    print(f"⚠️ Error extracting job card: {str(e)}")
                    continue
            
            print(f"✅ Found {len(jobs)} jobs on LinkedIn")
            
        except Exception as e:
            print(f"❌ LinkedIn job search failed: {str(e)}")
        
        return jobs
    
    async def scrape(self, keywords: str, position_type: str = "phd") -> List[Dict]:
        """
        Main scraping method
        
        Args:
            keywords: Search keywords
            position_type: 'phd' or 'postdoc'
        
        Returns:
            List of job dictionaries
        """
        playwright = await async_playwright().start()
        
        try:
            # Launch browser
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
            
            # Login
            login_success = await self.login()
            
            if not login_success:
                print("⚠️ Skipping LinkedIn scraping due to login failure")
                return []
            
            # Search jobs
            jobs = await self.search_jobs(keywords, job_type=position_type)
            
            return jobs
            
        except Exception as e:
            print(f"❌ LinkedIn scraping error: {str(e)}")
            return []
            
        finally:
            # Cleanup
            if self.browser:
                await self.browser.close()
            await playwright.stop()


# Standalone test function
async def test_linkedin_scraper():
    """Test LinkedIn scraper"""
    scraper = LinkedInScraper()
    jobs = await scraper.scrape("Machine Learning AI", "phd")
    
    print(f"\n📋 Found {len(jobs)} jobs")
    for i, job in enumerate(jobs[:5], 1):
        print(f"\n{i}. {job['title']}")
        print(f"   Company: {job['institution']}")
        print(f"   URL: {job['url']}")


if __name__ == "__main__":
    asyncio.run(test_linkedin_scraper())
