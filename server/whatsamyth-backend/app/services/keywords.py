"""
Keyword and Entity Extraction
Extracts key terms, entities, and assertions from claims for better evidence search.
"""

import re
import logging
from typing import List, Dict, Set, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """
    Extracts keywords, entities, and key phrases from claims.
    Used to improve evidence search accuracy.
    """

    # Stop words to filter out
    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'this', 'these', 'those', 'we', 'you',
        'they', 'them', 'been', 'have', 'had', 'having', 'do', 'does', 'did'
    }

    # Important keywords that should always be kept
    IMPORTANT_KEYWORDS = {
        # Health
        'vaccine', 'covid', 'corona', 'virus', 'cure', 'treatment', 'medicine',
        'doctor', 'hospital', 'disease', 'symptom', 'pandemic', 'epidemic',

        # Tech
        'whatsapp', 'facebook', 'google', '5g', 'phone', 'internet', 'app',
        'technology', 'radiation', 'microchip', 'tracking',

        # Authority
        'government', 'minister', 'pm', 'president', 'official', 'announce',
        'declare', 'statement', 'said', 'confirmed',

        # Actions
        'shutdown', 'ban', 'illegal', 'arrest', 'death', 'kill', 'cause',
        'prevent', 'cure', 'proven', 'study', 'research',

        # Misinformation markers
        'hoax', 'fake', 'false', 'true', 'fact', 'myth', 'rumor'
    }

    # Patterns for entity extraction
    ENTITY_PATTERNS = {
        'person': r'\b(?:PM|President|Minister|Dr\.?|Mr\.?|Mrs\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'organization': r'\b(WHO|CDC|FDA|NASA|WhatsApp|Facebook|Google|PIB|NDMA|Ministry\s+of\s+\w+)',
        'time': r'\b(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?|\d{1,2}\s*(?:am|pm|AM|PM))',
        'date': r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
        'number': r'\b(\d+(?:\.\d+)?)\s*(?:%|percent|times|hours|days|years)',
    }

    def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10
    ) -> List[str]:
        """
        Extract important keywords from text.

        Args:
            text: Input text
            max_keywords: Maximum number of keywords to return

        Returns:
            List of keywords ordered by importance
        """
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)

        # Filter and count
        filtered_words = []
        for word in words:
            if len(word) > 2:  # Skip very short words
                if word in self.IMPORTANT_KEYWORDS:
                    filtered_words.append(word)
                elif word not in self.STOP_WORDS:
                    filtered_words.append(word)

        # Count frequency
        word_freq = Counter(filtered_words)

        # Boost important keywords
        for word in word_freq:
            if word in self.IMPORTANT_KEYWORDS:
                word_freq[word] *= 3

        # Get top keywords
        top_keywords = [word for word, _ in word_freq.most_common(max_keywords)]

        return top_keywords

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.

        Args:
            text: Input text

        Returns:
            Dict mapping entity type to list of entities
        """
        entities = {}

        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Deduplicate and clean
                unique_matches = list(set(match.strip() for match in matches if match.strip()))
                if unique_matches:
                    entities[entity_type] = unique_matches

        return entities

    def extract_key_phrases(
        self,
        text: str,
        max_phrases: int = 5
    ) -> List[str]:
        """
        Extract key phrases (2-4 word combinations).

        Args:
            text: Input text
            max_phrases: Maximum number of phrases

        Returns:
            List of key phrases
        """
        # Normalize text
        text = re.sub(r'\s+', ' ', text).strip()

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        phrases = []

        for sentence in sentences:
            words = sentence.lower().split()

            # Extract 2-4 word phrases containing important keywords
            for i in range(len(words)):
                for phrase_len in [2, 3, 4]:
                    if i + phrase_len <= len(words):
                        phrase_words = words[i:i+phrase_len]

                        # Check if phrase contains important keyword
                        if any(word in self.IMPORTANT_KEYWORDS for word in phrase_words):
                            # Check if not all stop words
                            if not all(word in self.STOP_WORDS for word in phrase_words):
                                phrase = ' '.join(phrase_words)
                                phrases.append(phrase)

        # Deduplicate and limit
        unique_phrases = list(dict.fromkeys(phrases))  # Preserve order
        return unique_phrases[:max_phrases]

    def build_search_queries(
        self,
        text: str,
        max_queries: int = 3
    ) -> List[str]:
        """
        Build optimized search queries for evidence search.

        Args:
            text: Claim text
            max_queries: Maximum number of queries to generate

        Returns:
            List of search queries
        """
        queries = []

        # Extract components
        keywords = self.extract_keywords(text, max_keywords=5)
        entities = self.extract_entities(text)
        phrases = self.extract_key_phrases(text, max_phrases=3)

        # Query 1: Key phrase + "fact check" or "debunk"
        if phrases:
            queries.append(f'"{phrases[0]}" fact check')

        # Query 2: Top keywords combined
        if len(keywords) >= 2:
            top_keywords = ' '.join(keywords[:3])
            queries.append(f"{top_keywords} verification")

        # Query 3: Entity-focused (if person/org mentioned)
        if 'person' in entities and entities['person']:
            person = entities['person'][0]
            if keywords:
                queries.append(f'"{person}" {keywords[0]} official statement')
        elif 'organization' in entities and entities['organization']:
            org = entities['organization'][0]
            queries.append(f'{org} {keywords[0] if keywords else "statement"}')
        elif keywords:
            # Fallback: just top keywords
            queries.append(f"{' '.join(keywords[:2])} hoax myth")

        # Limit and return
        return queries[:max_queries]


# Global singleton
_keyword_extractor: Optional[KeywordExtractor] = None


def get_keyword_extractor() -> KeywordExtractor:
    """Get the global keyword extractor instance."""
    global _keyword_extractor

    if _keyword_extractor is None:
        _keyword_extractor = KeywordExtractor()

    return _keyword_extractor
