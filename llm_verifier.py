"""
LLM Verifier Module
Uses ChatGPT to verify and filter job postings before sending emails.
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

def _get_openai_client():
    """
    Lazily create an OpenAI client only when an API key exists.
    This keeps non-LLM parts of the system usable without OPENAI_API_KEY.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception:
        return None


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
        client = _get_openai_client()
        if not client:
            raise RuntimeError("OPENAI_API_KEY not set (LLM verification disabled)")

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
        print(f"⚠️ LLM verification skipped/failed: {str(e)}")
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


def verify_job_history(jobs: List[Dict], keywords: str, relevance_threshold: int = 5) -> List[Dict]:
    """
    Re-verify previously discovered jobs for continued relevance.
    Uses LLM to score each job on relevance (0-10 scale) and filter out low-scoring items.
    
    Args:
        jobs: List of previously found job dictionaries
        keywords: Current search keywords
        relevance_threshold: Minimum score (0-10) to keep job (default: 5)
    
    Returns:
        List of jobs scoring above threshold
    """
    if not jobs:
        return []
    
    print(f"\n🔍 Re-verifying {len(jobs)} previously discovered positions for relevance...")
    
    # Prepare jobs for relevance scoring
    jobs_text = "\n\n".join([
        f"Job {i+1}:\n"
        f"Title: {job.get('title', 'N/A')}\n"
        f"Institution: {job.get('university', job.get('institution', 'N/A'))}\n"
        f"Found Date: {job.get('found_date', 'Unknown')}\n"
        f"URL: {job.get('url', 'N/A')}"
        for i, job in enumerate(jobs)
    ])
    
    prompt = f"""You are a PhD job listing relevance evaluator. Score each of these previously discovered positions on relevance to the current search.

Current search keywords: {keywords}

Scoring criteria (0-10 scale):
- 9-10: Highly relevant, specific position matching keywords perfectly
- 7-8: Very relevant, matches most keywords
- 5-6: Moderately relevant, matches some keywords
- 3-4: Weakly relevant, tangentially related
- 0-2: Not relevant, wrong field or generic posting

Red flags (automatically score ≤4):
- Generic titles: "PhD Positions", "Open Positions", "Join Our Team"
- URLs to general career pages (not specific postings)
- Completely unrelated to keywords
- Titles suggesting non-PhD positions (postdoc, professor, engineer, technician)

Jobs to score:
{jobs_text}

Respond ONLY with a JSON array of scores (0-10) in order. Example: [8, 3, 9, 2, 7]
Array must have exactly {len(jobs)} scores.
"""
    
    try:
        client = _get_openai_client()
        if not client:
            raise RuntimeError("OPENAI_API_KEY not set (LLM verification disabled)")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise job relevance scorer. Respond only with valid JSON arrays of integers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON array
        import json
        scores = json.loads(result_text)
        
        if len(scores) != len(jobs):
            print(f"⚠️ Score array length mismatch. Expected {len(jobs)}, got {len(scores)}")
            return jobs  # Return all if scoring failed
        
        # Filter jobs by relevance threshold
        relevant_jobs = []
        filtered_count = 0
        
        for job, score in zip(jobs, scores):
            if score >= relevance_threshold:
                relevant_jobs.append(job)
            else:
                filtered_count += 1
                print(f"  ❌ Filtered (score {score}/10): {job.get('title', 'Unknown')[:60]}")
        
        print(f"✅ Relevance verification complete: {len(relevant_jobs)} relevant, {filtered_count} filtered")
        return relevant_jobs
        
    except Exception as e:
        print(f"⚠️ LLM relevance scoring skipped/failed: {str(e)}")
        print("Returning all jobs without LLM filtering...")
        return jobs


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


def deep_verify_positions(jobs: List[Dict], keywords: str, position_type: str = "phd") -> List[Dict]:
    """
    Phase 5: Deep verification using GPT-4o-mini to score and filter positions.
    This provides more accurate filtering to eliminate false positives.
    
    Args:
        jobs: List of job dictionaries
        keywords: Search keywords for relevance checking
        position_type: 'phd' or 'postdoc'
    
    Returns:
        Only positions with relevance score >= 6 and confirmed as valid type
    """
    if not jobs or len(jobs) == 0:
        return []
    
    print(f"🤖 Deep verifying {len(jobs)} positions ({position_type}) with GPT-4o-mini...")
    
    verified_jobs = []
    
    # Process in batches of 10 for efficiency
    batch_size = 10
    
    target_role = "PhD/Doctoral position" if position_type == "phd" else "PostDoc/Tenure Track position"
    forbidden_role = "PostDoc/Professor" if position_type == "phd" else "PhD Student"
    
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        
        # Prepare batch for verification
        jobs_text = "\n\n".join([
            f"Position {j+1}:\n"
            f"Title: {job.get('title', 'N/A')}\n"
            f"University: {job.get('university', job.get('institution', 'N/A'))}\n"
            f"URL: {job.get('url', 'N/A')}"
            for j, job in enumerate(batch)
        ])
        
        prompt = f"""You are an expert academic job validator. For each position below, provide:
1. is_valid_type: true/false (Is this genuinely a {target_role}? NOT {forbidden_role}, NOT general program info)
2. relevance_score: 0-10 (How relevant is this to keywords: {keywords})  
3. reason: Brief justification (max 20 words)

Keywords: {keywords}
Target Type: {target_role}

Positions to evaluate:
{jobs_text}

Respond ONLY with valid JSON array like:
[
  {{"position": 1, "is_valid_type": true, "relevance_score": 8, "reason": "Clear match"}},
  {{"position": 2, "is_valid_type": false, "relevance_score": 3, "reason": "Wrong position type"}}
]
"""
        
        try:
            client = _get_openai_client()
            if not client:
                raise RuntimeError("OPENAI_API_KEY not set (LLM verification disabled)")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a PhD job listing expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            import json
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            evaluations = json.loads(result_text)
            
            # Filter based on criteria
            for eval_item in evaluations:
                pos_idx = eval_item.get("position", 0) - 1
                if 0 <= pos_idx < len(batch):
                    job = batch[pos_idx]
                    
                    is_valid = eval_item.get("is_valid_type", False)
                    # Backward compatibility for old prompt structure if model hallucinates
                    if "is_phd" in eval_item and position_type == "phd":
                         is_valid = eval_item["is_phd"]
                         
                    score = eval_item.get("relevance_score", 0)
                    reason = eval_item.get("reason", "")
                    
                    # Keep only if it's a valid position AND score is high enough
                    # Stricter threshold (>= 8) to reduce noisy / generic links
                    if is_valid and score >= 8:
                        job['llm_score'] = score
                        job['llm_reason'] = reason
                        verified_jobs.append(job)
                    else:
                        print(f"  ❌ Filtered: {job.get('title', '')[:60]}... (Valid:{is_valid}, Score:{score})")
            
        except Exception as e:
            print(f"  ⚠️ Deep verification skipped/failed: {e}")
            # If verification is disabled or fails, keep all (fail-safe)
            verified_jobs.extend(batch)
    
    print(f"✅ Deep verification: {len(verified_jobs)}/{len(jobs)} positions passed filtering")
    return verified_jobs
