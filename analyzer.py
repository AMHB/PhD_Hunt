import re

class KeywordAnalyzer:
    def __init__(self):
        self.categories = {
            "Core Network Tech": [
                r"Open RAN", r"O-RAN", r"vRAN", r"6G", r"5G Advanced", 
                r"Non-Terrestrial Networks", r"NTN", r"Satellite Communications", 
                r"SDN", r"NFV", r"Segment Routing", r"Network Slicing"
            ],
            "AI & Intelligence": [
                r"Semantic Communication", r"Integrated Sensing and Communications", 
                r"ISAC", r"Federated Learning", r"Edge AI", r"Network Intelligence", 
                r"Digital Twin"
            ],
            "Physical Layer": [
                r"Terahertz", r"THz", r"Massive MIMO", r"Beamforming", r"Signal Processing"
            ],
            "Cybersecurity": [
                r"Network Security", r"Zero Trust", r"ZTA", r"Post-Quantum Cryptography", 
                r"PQC", r"Blockchain", r"Supply Chain Security", r"IoT Security"
            ]
        }
        
        # Compile regexes for performance
        self.compiled_patterns = {}
        for cat, phrases in self.categories.items():
            # Create a single regex for the category: \b(phrase1|phrase2)\b
            # We escape phrases just in case, though most are alphanumeric
            safe_phrases = [re.escape(p) for p in phrases]
            pattern_str = r"(?i)\b(" + "|".join(safe_phrases) + r")\b"
            self.compiled_patterns[cat] = re.compile(pattern_str)

    def analyze_text(self, text):
        """
        Returns a list of matched categories found in the text.
        """
        matched_categories = []
        if not text:
            return matched_categories
            
        for cat, pattern in self.compiled_patterns.items():
            if pattern.search(text):
                matched_categories.append(cat)
        
        return matched_categories

    def is_relevant(self, text):
        """
        Returns True if at least one keyword matches.
        """
        return len(self.analyze_text(text)) > 0
