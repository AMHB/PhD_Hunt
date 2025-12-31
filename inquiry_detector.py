"""
PhD Inquiry Detector Module
Detects faculty/lab pages indicating openness to accepting PhD students.
Searches for phrases like "accepting PhD students", "looking for motivated students", etc.
"""
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse


class InquiryDetector:
    """
    Detects signals on faculty/research group pages indicating
    openness to accepting new PhD students.
    """
    
    def __init__(self):
        # Positive signals - English
        self.english_patterns = [
            # Direct acceptance statements
            r"accepting\s+(?:new\s+)?phd\s+(?:student|candidate)",
            r"looking\s+for\s+(?:motivated\s+)?(?:phd\s+)?(?:student|candidate)",
            r"seeking\s+(?:talented\s+)?(?:phd\s+)?(?:student|candidate|researcher)",
            r"recruiting\s+(?:phd\s+)?(?:student|candidate)",
            r"phd\s+(?:position|opening)s?\s+available",
            r"phd\s+(?:student|candidate)s?\s+wanted",
            r"interested\s+(?:student|candidate)s?\s+(?:should|are encouraged to)\s+(?:contact|apply)",
            r"open\s+to\s+(?:accepting|supervising)\s+(?:phd\s+)?student",
            r"currently\s+accepting\s+applications?\s+from\s+(?:phd\s+)?student",
            r"we\s+are\s+looking\s+for\s+phd\s+(?:student|candidate)",
            r"join\s+(?:our|my)\s+(?:research\s+)?(?:group|lab|team)\s+as\s+(?:a\s+)?phd",
            r"(?:phd|doctoral)\s+opportunities?\s+available",
            r"prospective\s+(?:phd\s+)?students?\s+(?:should|are encouraged to)\s+contact",
            r"we\s+have\s+(?:funded\s+)?phd\s+(?:position|opening)",
            r"always\s+(?:looking|interested)\s+in\s+(?:talented\s+)?(?:phd\s+)?student",
            r"year-round\s+phd\s+(?:recruitment|applications?)",
            r"all\s+year\s+(?:phd\s+)?applications?",
            
            # LinkedIn-specific patterns
            r"#phdposition",
            r"#phd(?:opportunity|opening|vacancy)",
            r"#hiring.*phd",
            r"dm\s+me\s+if\s+interested.*phd",
            r"apply\s+(?:now|here).*phd\s+(?:position|student)",
            r"we'?re\s+hiring.*phd",
            
            # PostDoc variants (if position_type is postdoc)
            r"accepting\s+postdoc\s+(?:application|candidate)",
            r"postdoc(?:toral)?\s+(?:position|opening)s?\s+available",
            r"seeking\s+postdoc(?:toral)?\s+(?:researcher|fellow)",
            r"recruiting\s+postdoc",
        ]
        
        # Positive signals - German
        self.german_patterns = [
            r"suchen?\s+(?:derzeit\s+)?doktorand(?:en|in)",
            r"promotionsstellen?\s+verfügbar",
            r"doktorarbeit(?:en)?\s+(?:möglich|verfügbar)",
            r"interessierte\s+(?:studierende|bewerber)\s+(?:können|sollten)\s+sich\s+(?:melden|bewerben)",
            r"zur\s+promotion\s+gesucht",
            r"phd-stelle(?:n)?\s+zu\s+vergeben",
            r"wir\s+suchen\s+doktorand",
            r"offene\s+promotionsstelle",
            r"bewerbungen?\s+für\s+(?:eine\s+)?promotion",
            r"postdoc-?stelle(?:n)?\s+verfügbar",
            r"suchen?\s+postdoc",
        ]
        
        # Negative signals - exclude these even if positive patterns match
        self.negative_patterns = [
            r"no\s+(?:longer\s+)?accepting\s+(?:application|student)",
            r"not\s+currently\s+accepting",
            r"position\s+(?:has\s+been\s+)?filled",
            r"(?:application|recruitment)\s+closed",
            r"deadline\s+passed",
            r"keine\s+(?:freie|offene)\s+stelle",
            r"nicht\s+mehr\s+verfügbar",
            r"stelle\s+besetzt",
        ]
        
        self.all_positive_patterns = self.english_patterns + self.german_patterns
    
    def scan_page_for_inquiry_signals(self, page_content: str, position_type: str = "phd") -> Dict:
        """
        Scan page content for signals indicating acceptance of PhD/PostDoc students.
        
        Args:
            page_content: Full text content of the page
            position_type: "phd" or "postdoc"
        
        Returns:
            Dict with keys: has_signal (bool), matched_patterns (list), context_snippets (list)
        """
        if not page_content:
            return {"has_signal": False, "matched_patterns": [], "context_snippets": []}
        
        page_lower = page_content.lower()
        
        # Check for negative signals first
        for neg_pattern in self.negative_patterns:
            if re.search(neg_pattern, page_lower, re.IGNORECASE):
                return {"has_signal": False, "matched_patterns": [], "context_snippets": [],
                        "rejection_reason": "negative_signal_detected"}
        
        matched_patterns = []
        context_snippets = []
        
        # Check positive patterns
        for pattern in self.all_positive_patterns:
            matches = re.finditer(pattern, page_lower, re.IGNORECASE)
            for match in matches:
                matched_patterns.append(pattern)
                
                # Extract context around match (±100 characters)
                start = max(0, match.start() - 100)
                end = min(len(page_content), match.end() + 100)
                snippet = page_content[start:end].strip()
                context_snippets.append(snippet)
        
        has_signal = len(matched_patterns) > 0
        
        return {
            "has_signal": has_signal,
            "matched_patterns": list(set(matched_patterns)),  # Deduplicate
            "context_snippets": context_snippets[:3],  # Limit to top 3 snippets
            "signal_strength": len(matched_patterns)  # More matches = stronger signal
        }
    
    def extract_contact_info(self, page_content: str) -> Dict[str, Optional[str]]:
        """
        Extract contact information from page content.
        
        Returns:
            Dict with keys: email, phone (if found)
        """
        contact_info = {"email": None, "phone": None}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, page_content)
        if email_matches:
            contact_info["email"] = email_matches[0]  # Take first email found
        
        # Phone pattern (international format)
        phone_pattern = r'\+?\d{1,4}[\s\-\.]?\(?\d{1,4}\)?[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,9}'
        phone_matches = re.findall(phone_pattern, page_content)
        if phone_matches:
            contact_info["phone"] = phone_matches[0]
        
        return contact_info
    
    def build_inquiry_opportunity(self, 
                                   professor_name: str,
                                   university: str,
                                   page_url: str,
                                   research_areas: str,
                                   country: str,
                                   signal_data: Dict,
                                   contact_info: Dict) -> Dict:
        """
        Build a structured inquiry opportunity object.
        
        Args:
            professor_name: Name of professor/PI
            university: University name
            page_url: URL of the page where signal was detected
            research_areas: Research interests/areas
            country: Country
            signal_data: Output from scan_page_for_inquiry_signals
            contact_info: Output from extract_contact_info
        
        Returns:
            Structured opportunity dict
        """
        return {
            "professor": professor_name,
            "university": university,
            "country": country,
            "research_areas": research_areas,
            "url": page_url,
            "email": contact_info.get("email", "N/A"),
            "signal_strength": signal_data.get("signal_strength", 0),
            "matched_patterns": signal_data.get("matched_patterns", []),
            "context_snippet": signal_data.get("context_snippets", [""])[0] if signal_data.get("context_snippets") else "",
            "source": "Inquiry Detection"
        }
    
    def is_relevant_page_type(self, url: str, page_title: str = "") -> bool:
        """
        Check if URL/page is likely to contain inquiry signals.
        Focus on faculty pages, group pages, personal websites.
        
        Args:
            url: Page URL
            page_title: Page title (optional)
        
        Returns:
            True if page type is relevant for inquiry detection
        """
        url_lower = url.lower()
        title_lower = page_title.lower() if page_title else ""
        
        # Relevant page indicators
        relevant_indicators = [
            "/faculty/", "/staff/", "/people/", "/team/",
            "/professor/", "/researcher/", "/principal-investigator/",
            "/group/", "/lab/", "/research-group/",
            "personnel", "mitarbeiter", "personal",
            "opportunities", "positions", "jobs", "careers",
            "join-us", "join", "recruiting", "openings",
        ]
        
        for indicator in relevant_indicators:
            if indicator in url_lower or indicator in title_lower:
                return True
        
        # Exclude generic pages
        exclude_indicators = [
            "/news/", "/events/", "/publications/",
            "/contact/", "/about/", "/sitemap/",
            ".pdf", ".doc", ".ppt",
        ]
        
        for exclude in exclude_indicators:
            if exclude in url_lower:
                return False
        
        return False  # Default: not relevant unless explicitly marked as relevant


def test_inquiry_detector():
    """Quick test of the inquiry detector"""
    detector = InquiryDetector()
    
    # Test case 1: Positive signal
    test_text_1 = """
    Dr. Smith's Research Group
    
    We are currently accepting PhD students interested in machine learning
    and computer vision. Prospective students should contact me at smith@university.edu
    """
    result = detector.scan_page_for_inquiry_signals(test_text_1)
    print(f"Test 1 - Has signal: {result['has_signal']}")
    print(f"  Matched patterns: {len(result['matched_patterns'])}")
    
    # Test case 2: Negative signal
    test_text_2 = """
    Our lab is no longer accepting applications for this year.
    """
    result2 = detector.scan_page_for_inquiry_signals(test_text_2)
    print(f"\nTest 2 - Has signal: {result2['has_signal']} (should be False)")
    
    # Test contact extraction
    contact = detector.extract_contact_info(test_text_1)
    print(f"\nTest 3 - Email extracted: {contact['email']}")


if __name__ == "__main__":
    test_inquiry_detector()
