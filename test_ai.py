import asyncio
import os
from ai_crawler import AICrawler
from analyzer import KeywordAnalyzer
from dotenv import load_dotenv

load_dotenv()

async def test_ai_crawler():
    print("Testing AI Crawler Initialization...")
    analyzer = KeywordAnalyzer()
    
    # Mock uni list
    universities = [{"name": "Test Uni", "url": "https://www.example.com"}]
    
    crawler = AICrawler(analyzer, universities, position_type="phd")
    
    if crawler.use_ai:
        print("✅ Gemini API Key found and configured.")
    else:
        print("⚠️ Gemini API Key NOT found. Falling back to heuristic.")
        
    print("AI Crawler initialized successfully.")

if __name__ == "__main__":
    asyncio.run(test_ai_crawler())
