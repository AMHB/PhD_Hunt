"""
Link Validator Module
Validates job posting URLs to filter out broken/dead links before sending to users.
"""
import asyncio
from typing import List, Dict
import requests
from requests.exceptions import RequestException, Timeout, SSLError


def validate_link_sync(url: str, timeout: int = 10) -> bool:
    """
    Synchronously validate a single link using HTTP HEAD request.
    Returns True if link is accessible (200, 301, 302), False otherwise.
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        # Accept 200 (OK), 301/302 (redirects), and some 403s (might require cookies/auth but exist)
        return response.status_code in [200, 301, 302, 403]
    except (RequestException, Timeout, SSLError, Exception):
        return False


async def validate_links_batch(jobs: List[Dict], max_workers: int = 10) -> List[Dict]:
    """
    Validate multiple job links concurrently.
    Returns only jobs with valid (accessible) links.
    
    Args:
        jobs: List of job dicts with 'url' key
        max_workers: Max concurrent validation requests
    
    Returns:
        List of jobs with valid links only
    """
    print(f"🔗 Validating {len(jobs)} links...")
    
    valid_jobs = []
    invalid_count = 0
    
    # Process in batches to avoid overwhelming the network
    batch_size = max_workers
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        
        # Run validation in thread pool (requests is blocking)
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, validate_link_sync, job['url'])
            for job in batch
        ]
        
        results = await asyncio.gather(*tasks)
        
        for job, is_valid in zip(batch, results):
            if is_valid:
                valid_jobs.append(job)
            else:
                invalid_count += 1
                print(f"  ❌ Broken link filtered: {job['url'][:80]}...")
    
    print(f"✅ Link validation complete: {len(valid_jobs)} valid, {invalid_count} broken")
    return valid_jobs


def validate_single_link(url: str) -> bool:
    """
    Quick validation of a single link (for testing).
    """
    return validate_link_sync(url, timeout=5)
