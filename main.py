# PhD Headhunter Agent v1.1 - CI/CD Test - 2024-12-24
import asyncio
import os
import traceback
from datetime import datetime
from playwright.async_api import async_playwright
from scraper import GlobalPortalScraper, UniversityScraper
from analyzer import KeywordAnalyzer
from utils import StateManager, EmailSender, is_phd_only
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

load_dotenv()

def send_status_email(status: str, details: str = ""):
    """
    Send a simple status notification email.
    status: 'STARTED', 'STOPPED', or 'SUCCESS'
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
        msg["To"] = gmail_user
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
        print(f"📧 Status email sent: {status}")
    except Exception as e:
        print(f"❌ Failed to send status email: {e}")

async def main():
    print("Starting PhD Headhunter Agent...")
    print("Focus: Germany, Austria, Switzerland, Nordic countries")
    print("Filter: PhD positions only (excluding PostDoc/Professor)")
    print("-" * 50)
    
    # 1. Load Config
    with open("universities.txt", "r", encoding="utf-8") as f:
        universities = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    analyzer = KeywordAnalyzer()
    state_manager = StateManager()
    
    # 2. Run Scrapers
    all_found_jobs = []
    
    async with async_playwright() as p:
        # Launch browser (headless=True for VPS, False for local debugging)
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )

        # Create a context with a real user agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        # 2a. Scrape Global Portals
        print("\n📡 Running Global Portal Scraper...")
        gp_scraper = GlobalPortalScraper(analyzer)
        gp_jobs = await gp_scraper.scrape(context)
        all_found_jobs.extend(gp_jobs)
        print(f"✓ Found {len(gp_jobs)} jobs from global portals")

        # 2b. Scrape Universities
        print(f"\n🏫 Running University Scraper ({len(universities)} institutions)...")
        uni_scraper = UniversityScraper(analyzer, universities)
        uni_jobs = await uni_scraper.scrape(context)
        all_found_jobs.extend(uni_jobs)
        print(f"✓ Found {len(uni_jobs)} jobs from universities")
        
        # 2c. Recheck previously discovered positions
        print("\n🔄 Rechecking previously discovered positions...")
        page = await context.new_page()
        active_old_jobs = await state_manager.recheck_jobs(page)
        await page.close()
        
        await browser.close()

    # 3. Filter for PhD-only positions
    print("\n🔍 Filtering for PhD-only positions...")
    phd_jobs = [job for job in all_found_jobs if is_phd_only(job["title"])]
    excluded_count = len(all_found_jobs) - len(phd_jobs)
    print(f"  Kept: {len(phd_jobs)} PhD positions")
    print(f"  Excluded: {excluded_count} PostDoc/Professor positions")

    # 4. Process Results
    new_jobs = []
    
    for job in phd_jobs:
        if state_manager.is_new(job["url"]):
            new_jobs.append(job)
            state_manager.add_job(job)
    
    # Get previously discovered active jobs (excluding today's new ones)
    old_jobs = [j for j in active_old_jobs if j["url"] not in [nj["url"] for nj in new_jobs]]

    # 5. Report
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY")
    print(f"  🆕 New Positions: {len(new_jobs)}")
    print(f"  📂 Previously Discovered (still active): {len(old_jobs)}")
    print("=" * 50)
    
    # 6. Send Email
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    
    if gmail_user and gmail_pass:
        print("\n📧 Sending email report...")
        sender = EmailSender(gmail_user, gmail_pass)
        sender.send_email(gmail_user, new_jobs, old_jobs)
    else:
        print("\n⚠️ Skipped email (credentials not found in .env)")

def run_with_notifications():
    """Wrapper that sends status emails on start, crash, and success"""
    
    # Send STARTED notification
    send_status_email("STARTED")
    
    try:
        # Run the main program
        asyncio.run(main())
        
        # Send SUCCESS notification
        send_status_email("SUCCESS")
        
    except Exception as e:
        # Send STOPPED notification with error details
        error_details = traceback.format_exc()
        send_status_email("STOPPED", error_details)
        raise  # Re-raise so the error is logged

if __name__ == "__main__":
    run_with_notifications()

