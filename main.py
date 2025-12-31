# PhD Headhunter Agent v1.3 - Enhanced with Faculty & Inquiry Detection
import asyncio
import os
import argparse
import traceback
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from scraper import GlobalPortalScraper, UniversityScraper, ResearchGateScraper
from analyzer import KeywordAnalyzer
from utils import StateManager, EmailSender, is_phd_only, is_postdoc_only
from linkedin_scraper import LinkedInScraper
from llm_verifier import batch_verify_jobs, verify_job_history
from link_validator import validate_links_batch
from faculty_scraper import FacultyScraper, load_universities_from_file
from inquiry_detector import InquiryDetector
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

load_dotenv()

# Owner email for status notifications (always goes here)
OWNER_EMAIL = "amehrb@gmail.com"

def send_status_email(status: str, details: str = ""):
    """
    Send status notification email TO OWNER ONLY.
    status: 'STARTED', 'STOPPED', or 'SUCCESS'¬
    """
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_pass:
        print(f"⚠️ Cannot send status email (no credentials)")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    subjects = {
        "STARTED": "🚀 PhD Agent - Started Running",
        "STOPPED": "❌ PhD Agent - CRASHED/STOPPED",
        "SUCCESS": "✅ PhD Agent - Successfully Finished"
    }
    
    messages = {
        "STARTED": f"The PhD Headhunter Agent has started running.\n\nTime: {timestamp}\n\nYou will receive another email when it finishes or if it crashes.",
        "STOPPED": f"⚠️ The PhD Headhunter Agent has STOPPED unexpectedly!\n\nTime: {timestamp}\n\nError Details:\n{details}",
        "SUCCESS": f"The PhD Headhunter Agent has finished successfully!\n\nTime: {timestamp}\n\nCheck your inbox for the PhD positions report."
    }
    
    subject = subjects.get(status, f"PhD Agent - {status}")
    body = messages.get(status, details)
    
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = OWNER_EMAIL  # Always to owner
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
        print(f"📧 Status email sent to owner: {status}")
    except Exception as e:
        print(f"❌ Failed to send status email: {e}")

async def main(recipient_email=None, custom_keywords=None, position_type="phd", 
               search_open_positions=True, search_inquiry_positions=False, search_professors=False):
    """
    Main PhD agent function.
    recipient_email: Email to send results to (defaults to OWNER_EMAIL)
    custom_keywords: Custom keywords to search for (comma-separated)
    position_type: "phd" for PhD/Doctoral, "postdoc" for PostDoc/Tenure Track
    search_open_positions: Search for open job postings (default: True)
    search_inquiry_positions: Search for inquiry opportunities on faculty pages (default: False)
    search_professors: Search for professors in the field (default: False)
    """
    pos_label = "PhD/Doctoral" if position_type == "phd" else "PostDoc/Tenure Track"
    
    print(f"Starting Academic Position Headhunter Agent...")
    print(f"Position Type: {pos_label}")
    print("Focus: Germany, Austria, Switzerland, Nordic countries + Europe")
    
    if position_type == "phd":
        print("Filter: PhD positions only (excluding PostDoc/Professor)")
    else:
        print("Filter: PostDoc/Tenure positions only (excluding PhD students)")
    
    print(f"\nSearch Types:")
    if search_open_positions:
        print("  ✓ Open Positions (Job Portals)")
    if search_inquiry_positions:
        print("  ✓ Inquiry Opportunities (Faculty Pages)")
    if search_professors:
        print("  ✓ Professors/Supervisors in Field")
    
    if recipient_email:
        print(f"\n📧 Results will be sent to: {recipient_email}")
    if custom_keywords:
        print(f"🔍 Custom keywords: {custom_keywords}")
    
    print("-" * 50)
    
    # 1. Load Config
    with open("universities.txt", "r", encoding="utf-8") as f:
        universities = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    # Initialize analyzer
    analyzer = KeywordAnalyzer()
    
    # Track keywords for scraper
    scraper_keywords = None
    
    if custom_keywords:
        # MODE 2 (Web Dashboard): Use ONLY custom keywords, clear defaults
        extra_keywords = [kw.strip() for kw in custom_keywords.split(",") if kw.strip()]
        if extra_keywords:
            # Clear default categories and use only custom keywords
            analyzer.categories.clear()
            analyzer.compiled_patterns.clear()
            
            # Add only the custom keywords
            analyzer.categories["Custom Keywords"] = extra_keywords
            import re
            safe_phrases = [re.escape(p) for p in extra_keywords]
            pattern_str = r"(?i)\b(" + "|".join(safe_phrases) + r")\b"
            analyzer.compiled_patterns["Custom Keywords"] = re.compile(pattern_str)
            print(f"  🔍 Using ONLY {len(extra_keywords)} custom keywords: {', '.join(extra_keywords)}")
            
            # Store custom keywords for scraper
            scraper_keywords = extra_keywords
    else:
        # MODE 1 (Cron/Default): Use hardcoded keywords from KeywordAnalyzer
        print("  🔍 Using default hardcoded keywords")
    
    state_manager = StateManager()
    
    # 2. Run Scrapers (conditionally based on search types)
    all_found_jobs = []
    inquiry_opportunities = []
    professors_list = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        # CONDITIONAL SCRAPING based on search type flags
        if search_open_positions:
            print("\n" + "="*60)
            print("🔍 SEARCHING FOR OPEN POSITIONS")
            print("="*60)
            
            # 2a. Scrape Global Portals
            print("\n📡 Running Global Portal Scraper...")
            gp_scraper = GlobalPortalScraper(analyzer, custom_keywords=scraper_keywords)
            gp_jobs = await gp_scraper.scrape(context)
            all_found_jobs.extend(gp_jobs)
            print(f"✓ Found {len(gp_jobs)} jobs from global portals")

            # 2b. Scrape Universities
            print(f"\n🏫 Running University Scraper ({len(universities)} institutions)...")
            uni_scraper = UniversityScraper(analyzer, universities)
            uni_jobs = await uni_scraper.scrape(context)
            all_found_jobs.extend(uni_jobs)
            print(f"✓ Found {len(uni_jobs)} jobs from universities")
            
            # 2c. Scrape ResearchGate
            print("\n🔬 Running ResearchGate Scraper...")
            try:
                rg_scraper = ResearchGateScraper(analyzer)
                rg_jobs = await rg_scraper.scrape(context)
                all_found_jobs.extend(rg_jobs)
                print(f"✓ Found {len(rg_jobs)} jobs from ResearchGate")
            except Exception as e:
                print(f"⚠️ ResearchGate scraping failed: {str(e)}")
            
            # 2d. Scrape LinkedIn
            print("\n💼 Running LinkedIn Scraper...")
            try:
                linkedin_scraper = LinkedInScraper()
                linkedin_keywords = custom_keywords if custom_keywords else "PhD position"
                linkedin_jobs = await linkedin_scraper.scrape(linkedin_keywords, position_type)
                all_found_jobs.extend(linkedin_jobs)
                print(f"✓ Found {len(linkedin_jobs)} jobs from LinkedIn")
            except Exception as e:
                print(f"⚠️ LinkedIn scraping failed: {str(e)}")
        
        # NEW: Faculty & Inquiry Scraping
        if search_inquiry_positions or search_professors:
            print("\n" + "="*60)
            print("👨‍🔬 SEARCHING FOR FACULTY & INQUIRY OPPORTUNITIES")
            print("="*60)
            
            # Load university data
            university_data = load_universities_from_file("universities.txt")
            if not university_data:
                # Fallback: use existing universities list
                university_data = [{"name": u, "url": u, "country": "Unknown"} for u in universities[:20]]
            
            # Initialize faculty scraper
            faculty_scraper = FacultyScraper(analyzer, university_data, position_type)
            
            # Run faculty scraper
            print(f"\n🎓 Scraping faculty directories from {len(university_data[:20])} universities...")
            try:
                faculty_results = await faculty_scraper.scrape(browser)
                
                if search_professors:
                    professors_list = faculty_results.get("professors", [])
                    print(f"✓ Found {len(professors_list)} relevant professors")
                
                if search_inquiry_positions:
                    inquiry_opportunities = faculty_results.get("inquiry_opportunities", [])
                    print(f"✓ Found {len(inquiry_opportunities)} inquiry opportunities")
            
            except Exception as e:
                print(f"⚠️ Faculty scraping failed: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Recheck previously discovered positions (only if searching open positions)
        active_old_jobs = []
        if search_open_positions:
            print("\n🔄 Rechecking previously discovered positions...")
            page = await context.new_page()
            active_old_jobs = await state_manager.recheck_jobs(page)
            await page.close()
        
        await browser.close()
    
    # 3. Link Validation - Filter out broken/dead links BEFORE LLM verification (only for open positions)
    if search_open_positions:
        print(f"\n📊 Total jobs found (before validation): {len(all_found_jobs)}")
        
        if all_found_jobs:
            print("\n🔗 Validating links to filter broken URLs...")
            try:
                valid_jobs = await validate_links_batch(all_found_jobs, max_workers=15)
                print(f"✅ After link validation: {len(valid_jobs)} have valid links")
                print(f"🗑️  Removed: {len(all_found_jobs) - len(valid_jobs)} broken/dead links")
                all_found_jobs = valid_jobs
            except Exception as e:
                print(f"⚠️ Link validation failed: {str(e)}")
                print("   Proceeding with unvalidated links...")
        
        # 4. LLM Verification - Filter invalid/duplicate jobs with ChatGPT
        print(f"\n📊 Jobs for LLM verification: {len(all_found_jobs)}")
        
        if all_found_jobs:
            print("\n🤖 Running LLM verification (ChatGPT filtering)...")
            try:
                verification_keywords = custom_keywords if custom_keywords else "PhD research position"
                verified_jobs = batch_verify_jobs(all_found_jobs, verification_keywords)
                print(f"✅ After LLM verification: {len(verified_jobs)} valid jobs")
                print(f"🗑️  Removed: {len(all_found_jobs) - len(verified_jobs)} invalid/duplicate jobs")
                all_found_jobs = verified_jobs
            except Exception as e:
                print(f"⚠️ LLM verification failed: {str(e)}")
                print("   Proceeding with unverified jobs...")
        
        # 5. Filter positions based on position_type
        if position_type == "phd":
            print("\n🔍 Filtering for PhD-only positions...")
            filtered_jobs = [job for job in all_found_jobs if is_phd_only(job["title"])]
            excluded_count = len(all_found_jobs) - len(filtered_jobs)
            print(f"  Kept: {len(filtered_jobs)} PhD positions")
            print(f"  Excluded: {excluded_count} PostDoc/Professor positions")
        else:  # postdoc
            print("\n🔍 Filtering for PostDoc/Tenure positions...")
            filtered_jobs = [job for job in all_found_jobs if is_postdoc_only(job["title"])]
            excluded_count = len(all_found_jobs) - len(filtered_jobs)
            print(f"  Kept: {len(filtered_jobs)} PostDoc/Tenure positions")
            print(f"  Excluded: {excluded_count} PhD/other positions")

        # 6. Process Results
        new_jobs = []
        
        for job in filtered_jobs:
            if state_manager.is_new(job["url"]):
                new_jobs.append(job)
                state_manager.add_job(job)
        
        # 7. Enhanced validation of old jobs
        print("\n🔍 Re-verifying previously discovered positions for relevance...")
        verification_keywords = custom_keywords if custom_keywords else "PhD research position"
        active_old_jobs = verify_job_history(active_old_jobs, verification_keywords, relevance_threshold=5)
        
        old_jobs = [j for j in active_old_jobs if j["url"] not in [nj["url"] for nj in new_jobs]]
    else:
        new_jobs = []
        old_jobs = []

    # 8. Report
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY")
    print(f"  🆕 New Positions: {len(new_jobs)}")
    print(f"  📂 Previously Discovered (still active): {len(old_jobs)}")
    if search_inquiry_positions:
        print(f"  💡 Inquiry Opportunities: {len(inquiry_opportunities)}")
    if search_professors:
        print(f"  👨‍🔬 Professors Found: {len(professors_list)}")
    print("=" * 50)
    
    # 9. Send Email to recipient (or owner if not specified)
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    
    # Use specified recipient or default to owner
    email_to = recipient_email if recipient_email else OWNER_EMAIL
    
    if gmail_user and gmail_pass:
        print(f"\n📧 Sending email report to {email_to}...")
        sender = EmailSender(gmail_user, gmail_pass)
        sender.send_email(
            email_to, 
            new_jobs, 
            old_jobs,
            inquiry_positions=inquiry_opportunities if search_inquiry_positions else None,
            professors=professors_list if search_professors else None
        )
    else:
        print("\n⚠️ Skipped email (credentials not found in .env)")

def run_with_notifications(recipient_email=None, custom_keywords=None, job_id=None, position_type="phd",
                           search_types="open"):
    """Wrapper that sends status emails on start, crash, and success"""
    from job_queue import acquire_lock, release_lock, is_locked, get_lock_info
    
    # Parse search types
    search_type_list = [s.strip() for s in search_types.split(",")]
    search_open_positions = "open" in search_type_list
    search_inquiry_positions = "inquiry" in search_type_list
    search_professors = "professors" in search_type_list
    
    # For Mode 1 (no job_id), check if locked and exit if so
    if job_id is None:  # Mode 1 - Manual/Cron run
        if is_locked():
            lock_info = get_lock_info()
            print("=" * 60)
            print("⚠️  CANNOT RUN - ANOTHER JOB IS IN PROGRESS")
            print("=" * 60)
            print(f"Since currently the server is running for another user's request,")
            print(f"you should try again later.")
            print(f"")
            print(f"Current job info:")
            print(f"  - Mode: {lock_info.get('mode', 'unknown')}")
            print(f"  - Started: {lock_info.get('started_at_str', 'unknown')}")
            print("=" * 60)
            return
        
        # Try to acquire lock for Mode 1
        if not acquire_lock("Mode 1 (Manual/Cron)", "cron", custom_keywords or "", recipient_email or ""):
            print("⚠️ Could not acquire lock. Try again later.")
            return
    
    # Send STARTED notification (to owner only)
    send_status_email("STARTED")
    
    try:
        # Run the main program with all parameters
        asyncio.run(main(
            recipient_email, 
            custom_keywords, 
            position_type,
            search_open_positions,
            search_inquiry_positions,
            search_professors
        ))
        
        # Send SUCCESS notification (to owner only)
        send_status_email("SUCCESS")
        
    except Exception as e:
        # Send STOPPED notification with error details (to owner only)
        error_details = traceback.format_exc()
        send_status_email("STOPPED", error_details)
        raise
    finally:
        # Only release lock if Mode 1 (we acquired it)
        if job_id is None:
            release_lock()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PhD Headhunter Agent v1.3")
    parser.add_argument("--recipient", "-r", type=str, help="Email address to send results to")
    parser.add_argument("--keywords", "-k", type=str, help="Custom keywords (comma-separated)")
    parser.add_argument("--job-id", "-j", type=str, help="Job ID (for Mode 2 queue processing)")
    parser.add_argument("--position-type", "-p", type=str, default="phd", 
                        choices=["phd", "postdoc"], help="Position type: phd or postdoc")
    parser.add_argument("--search-types", "-s", type=str, default="open",
                        help="Search types: comma-separated (open,inquiry,professors)")
    
    args = parser.parse_args()
    
    run_with_notifications(
        args.recipient, 
        args.keywords, 
        args.job_id, 
        args.position_type,
        args.search_types
    )
