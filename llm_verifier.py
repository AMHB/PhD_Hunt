"""
LLM Verifier Module
Uses ChatGPT to verify and filter job postings before sending emails.
"""
import os
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def verify_jobs_with_llm(jobs: List[Dict], keywords: str) -> List[Dict]:
    """
    Use ChatGPT to verify job postings and filter out invalid/duplicate links.
    
    Args:
        jobs: List of job dictionaries with 'title', 'url', 'institution' keys
        keywords: Search keywords used for relevance checking
    
    Returns:
        Filtered list of verified, unique job postings
    """
    if not jobs:
        return []
    
    # Prepare jobs for LLM verification
    jobs_text = "\n\n".join([
        f"Job {i+1}:\n"
        f"Title: {job.get('title', 'N/A')}\n"
        f"Institution: {job.get('institution', 'N/A')}\n"
        f"URL: {job.get('url', 'N/A')}"
        for i, job in enumerate(jobs)
    ])
    
    prompt = f"""You are a PhD job listing validator. Review these job postings and identify which ones are VALID.

A job is VALID if:
1. The title indicates a SPECIFIC position (not just "PhD Opportunities" or "General Applications")
2. It's relevant to these keywords: {keywords}
3. The URL appears to be a direct link to a job posting (not a general careers page)

A job is INVALID if:
- Generic title like "PhD Positions", "Open Positions", "Join Our Team"
- URL is a homepage or general careers page
- Completely irrelevant to the keywords

Jobs to verify:
{jobs_text}

Respond ONLY with a JSON array of valid job numbers (1-indexed). Example: [1, 3, 5, 7]
If ALL jobs are invalid, respond with: []
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise job listing validator. Respond only with valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON array from response
        import json
        valid_indices = json.loads(result_text)
        
        # Filter jobs based on valid indices (convert from 1-indexed to 0-indexed)
        verified_jobs = [jobs[i-1] for i in valid_indices if 0 < i <= len(jobs)]
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_jobs = []
        for job in verified_jobs:
            url = job.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append(job)
        
        return unique_jobs
        
    except Exception as e:
        print(f"⚠️ LLM verification failed: {str(e)}")
        print("Falling back to basic deduplication...")
        
        # Fallback: Just remove duplicates
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            url = job.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append(job)
        
        return unique_jobs


def batch_verify_jobs(jobs: List[Dict], keywords: str, batch_size: int = 20) -> List[Dict]:
    """
    Verify jobs in batches to handle large lists.
    
    Args:
        jobs: List of job dictionaries
        keywords: Search keywords
        batch_size: Number of jobs per batch
    
    Returns:
        All verified jobs combined
    """
    verified_jobs = []
    
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        verified_batch = verify_jobs_with_llm(batch, keywords)
        verified_jobs.extend(verified_batch)
    
    return verified_jobs
