"""
Claim Detection Service
Identifies whether text contains a verifiable claim and extracts canonical form.
Uses rule-based heuristics combined with sentence embeddings for classification.
"""

import re
import logging
from typing import Optional, List
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

# Lazy loading for heavy ML models
_embedding_model = None
_claim_trigger_embeddings = None


def _get_embedding_model():
    """Lazy load the sentence transformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            from app.config import get_settings
            settings = get_settings()
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            _embedding_model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            _embedding_model = None
    return _embedding_model


def _get_claim_trigger_embeddings() -> Optional[np.ndarray]:
    """
    Get pre-computed embeddings for claim trigger phrases.
    These are phrases that commonly appear in factual / misinformation claims.
    """
    global _claim_trigger_embeddings

    if _claim_trigger_embeddings is not None:
        return _claim_trigger_embeddings

    model = _get_embedding_model()
    if model is None:
        return None

    # Phrases that indicate factual claims (broader than just conspiracies)
    claim_trigger_phrases = [
        # Classic misinfo-ish patterns
        "scientists have discovered that",
        "studies prove that",
        "research shows that",
        "experts confirm that",
        "it has been proven that",
        "the government is hiding",
        "they don't want you to know",
        "breaking news reveals",
        "leaked documents show",
        "this cure will",
        "this treatment prevents",
        "vaccines cause",
        "this food causes cancer",
        "eating this will cure",
        "drinking this prevents",
        "the real truth about",
        "what they're not telling you",
        "exposed: the truth about",
        "fact: this actually",
        "warning: this common",
        "urgent: new evidence shows",
        "confirmed: government admits",
        "exposed: secret plan to",
        "shocking discovery reveals",
        "doctors are hiding this",

        # Neutral factual / newsy templates (non-misinfo)
        "X has won the election",
        "X has been elected as the president",
        "X has been appointed as the new CEO",
        "X will host the World Cup in 2030",
        "India will host the Commonwealth Games",
        "the government has announced a new policy",
        "the central bank has increased interest rates",
        "inflation has risen to 7 percent",
        "the unemployment rate has fallen",
        "India has signed a new trade agreement",
        "the court has ruled that",
        "the company reported record profits",
    ]

    try:
        _claim_trigger_embeddings = model.encode(
            claim_trigger_phrases, convert_to_numpy=True
        )
        logger.info(
            f"Generated {len(claim_trigger_phrases)} claim trigger embeddings"
        )
        return _claim_trigger_embeddings
    except Exception as e:
        logger.error(f"Failed to generate trigger embeddings: {e}")
        return None


# Rule-based patterns for claim detection
CLAIM_PATTERNS = [
    # Definitive statements
    r'\b(is|are|was|were|will be|has been|have been)\s+(proven|confirmed|discovered|revealed|shown)\b',
    r'\b(causes?|prevents?|cures?|kills?|protects?)\s+\w+',
    r'\b(always|never|100%|guaranteed|definitely|certainly)\b',
    
        # Urgency/emotional triggers
    r'\b(urgent|breaking|alert|warning|danger|shocking|incredible)\b',
    r'\b(share this|forward|must read|everyone should know)\b',

    # --- NEW: Disaster / weather alert patterns ---
    r'\b(cyclone|hurricane|typhoon|storm|earthquake|tsunami|floods?|landslide?s?)\b',
    r'\b(red|orange|yellow)\s+alert(s)?\b',
    r'\b(alert(s)?\s+issued|warning(s)?\s+issued)\b',
    r'\b(evacuate|evacuation|take shelter|seek shelter|emergency)\b',
    r'\b(death toll|casualties|injured|missing persons?)\b',
    r'\b(magnitude|intensity|category|level)\s+\d+\b',

    # Flat earth
    r'\bearth\s+is\s+flat\b',
    r'\bscam\b',
    r'\bhoax\b',
    r'\bconspiracy\b',

    # Health claims
    r'\b(vaccine|vaccination|covid|corona|virus|treatment|cure|medicine|drug)\b',
    r'\b(cancer|disease|illness|symptoms|side effects)\b',

    # Conspiracy indicators
    r'\b(government|they|officials|elites?|billionaires?)\s+(is|are|wants?|hid(e|ing)?|cover)',
    r'\b(secret|hidden|suppressed|censored|banned)\b',
    r'\b(don\'t want you to know|wake up|truth|exposed|leaked)\b',

    # Numerical claims
    r'\b\d+\s*(%|percent|times|x)\s*(more|less|higher|lower|better|worse)\b',
    r'\b(study|research|survey|poll)\s+(shows?|finds?|reveals?|proves?)\b',

    # Authority claims
    r'\b(scientists?|doctors?|experts?|researchers?|professors?)\s+(say|claim|confirm|discover)\b',
    r'\b(according to|based on|sources? say|reports? indicate)\b',

    # Urgency/emotional triggers
    r'\b(urgent|breaking|alert|warning|danger|shocking|incredible)\b',
    r'\b(share this|forward|must read|everyone should know)\b',
]

# High-priority patterns that should *always* be treated as claims
# (e.g., death / killed / passed away)
HIGH_PRIORITY_PATTERNS = [
    r'\b(is dead|has died|was found dead|has been found dead|passed away|died in|died at|was killed in|killed in)\b',
    r'\b(declared dead|pronounced dead)\b',
]

# Non-claim patterns (questions, opinions, etc.)
NON_CLAIM_PATTERNS = [
    r'^\s*(what|who|where|when|why|how|is|are|do|does|did|can|could|would|should)\s+.+\?\s*$',  # Questions
    r'\b(i think|i believe|in my opinion|personally|i feel|seems to me)\b',  # Opinions
    r'\b(maybe|perhaps|might|could be|possibly|i wonder)\b',  # Uncertainty
    r'^\s*(hi|hello|hey|good morning|good evening|thanks|thank you)\b',  # Greetings
    r'^\s*(lol|haha|hehe|😂|🤣|😆)\b',  # Casual chat
]

# Minimum text length to be considered a potential claim
MIN_CLAIM_LENGTH = 10
MAX_CLAIM_LENGTH = 5000


def _matches_any(patterns: List[str], text: str) -> bool:
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _is_high_priority_claim(text: str) -> bool:
    """
    Hard override for patterns that are *obviously* factual claims
    and should always be verified, regardless of other heuristics.
    """
    if not text:
        return False

    t = text.strip().lower()
    if len(t) < MIN_CLAIM_LENGTH:
        return False

    if _matches_any(HIGH_PRIORITY_PATTERNS, t):
        return True

    return False


def _rule_based_claim_score(text: str) -> float:
    """
    Calculate a claim score based on rule patterns.
    Returns a score between 0 and 1.
    """
    text_lower = text.lower().strip()

    # Quick rejections
    if len(text_lower) < MIN_CLAIM_LENGTH:
        return 0.0

    if len(text_lower) > MAX_CLAIM_LENGTH:
        return 0.0

    # Check for non-claim patterns
    for pattern in NON_CLAIM_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 0.0

    # Count matching claim patterns
    matches = 0
    for pattern in CLAIM_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches += 1

    # Normalize score (max 1.0)
    score = min(matches / 3.0, 1.0)
    return score


def _semantic_claim_score(text: str) -> float:
    """
    Calculate semantic similarity to known claim patterns.
    Uses sentence embeddings to compare against trigger phrases.
    Returns a score between 0 and 1.
    """
    model = _get_embedding_model()
    trigger_embeddings = _get_claim_trigger_embeddings()

    if model is None or trigger_embeddings is None:
        logger.warning("Semantic scoring unavailable, falling back to rule-based only")
        return 0.0

    try:
        # Get embedding for input text
        text_embedding = model.encode([text], convert_to_numpy=True)[0]

        # Calculate cosine similarities with all trigger phrases
        similarities = np.dot(trigger_embeddings, text_embedding) / (
            np.linalg.norm(trigger_embeddings, axis=1) * np.linalg.norm(text_embedding)
        )

        max_similarity = float(np.max(similarities))

        if max_similarity < 0.3:
            return 0.0

        return min(max_similarity, 1.0)

    except Exception as e:
        logger.error(f"Semantic scoring failed: {e}")
        return 0.0


def _looks_like_generic_fact(text: str) -> bool:
    """
    Fallback heuristic: does this look like a declarative, factual sentence
    about the world, even if it doesn't hit our narrow misinfo patterns?

    Example it should catch:
        "India has won a bid to host Commonwealth Games 2030."
    """
    t = text.strip()

    # Ignore questions
    if t.endswith("?"):
        return False

    # Ignore obvious opinion markers
    if _matches_any(NON_CLAIM_PATTERNS, t.lower()):
        return False

    # Needs at least one verb-ish auxiliary (very crude)
    if not re.search(r'\b(is|are|was|were|has|have|had|will|shall|won|lost)\b', t, re.IGNORECASE):
        return False

    tokens = t.split()
    if len(tokens) < 5:
        return False

    # Check for a year or any number (e.g., 2030)
    has_number = bool(re.search(r'\b\d{2,4}\b', t))

    # Check for at least one capitalized token (proper noun) not at start of sentence
    # This is crude but enough for "India", "Commonwealth", "Games", etc.
    cap_tokens = [tok for tok in tokens if re.match(r'^[A-Z][a-zA-Z]+$', tok)]
    has_proper_noun = len(cap_tokens) > 0

    # If we have at least a proper noun and a verb, treat as a generic fact
    if has_proper_noun or has_number:
        return True

    return False


def is_claim(text: str, threshold: float = 0.3, use_semantic: bool = True) -> bool:
    """
    Detect whether the given text contains a verifiable claim.

    Logic:
    1. Hard override for high-priority patterns (e.g., "has been found dead")
    2. Rule-based score (regex patterns)
    3. Optional semantic score via embeddings
    4. Take max(rule_score, semantic_score) and compare with threshold
    5. If still below threshold, fall back to generic fact heuristic
    """
    if not text or not isinstance(text, str):
        return False

    text = text.strip()
    if len(text) < MIN_CLAIM_LENGTH:
        return False

    # 1. High-priority override (death-type claims)
    if _is_high_priority_claim(text):
        logger.info(f"High-priority claim detected for text={text!r}")
        return True

    # 2. Rule-based score
    rule_score = _rule_based_claim_score(text)

    # 3. Optional semantic scoring
    if use_semantic:
        sem_score = _semantic_claim_score(text)
    else:
        sem_score = 0.0

    final_score = max(rule_score, sem_score)

    logger.info(
        f"ClaimDetection: rule_score={rule_score:.2f}, "
        f"semantic_score={sem_score:.2f}, final_score={final_score:.2f} "
        f"for text={text!r}"
    )

    # 4. Threshold decision
    if final_score >= threshold:
        return True

    # 5. Fallback: generic fact-like sentence heuristic
    if _looks_like_generic_fact(text):
        logger.info(f"Generic-fact heuristic triggered for text={text!r}")
        return True

    return False


def extract_canonical_claim(text: str) -> str:
    """
    Extract and normalize the core claim from a message.
    """
    if not text:
        return ""

    canonical = text.strip()

    # Remove common forwarding prefixes
    forward_prefixes = [
        r'^(fwd?|fw|forwarded?|shared?):\s*',
        r'^(re|reply):\s*',
        r'^\*+\s*forwarded\s+message\s*\*+\s*',
        r'^-+\s*forwarded\s+message\s*-+\s*',
    ]
    for prefix in forward_prefixes:
        canonical = re.sub(prefix, '', canonical, flags=re.IGNORECASE)

    # Remove URLs
    canonical = re.sub(r'https?://\S+', '', canonical)
    canonical = re.sub(r'www\.\S+', '', canonical)

    # Remove calls to action
    cta_patterns = [
        r'\b(share|forward|send)\s+(this|to|with)\s+.{0,50}$',
        r'\b(please|pls)\s+(share|forward|spread)\b',
        r'\b(must|have to|should)\s+(read|watch|see|share)\b',
        r'(spread\s+the\s+word|pass\s+it\s+on)',
    ]
    for pattern in cta_patterns:
        canonical = re.sub(pattern, '', canonical, flags=re.IGNORECASE)

    # Remove excessive punctuation and emojis
    canonical = re.sub(r'[!?]{2,}', '.', canonical)
    canonical = re.sub(r'\.{2,}', '.', canonical)
    canonical = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+',
        '',
        canonical,
    )

    canonical = re.sub(r'\s+', ' ', canonical).strip()

    if len(canonical) > 500:
        sentences = re.split(r'[.!?]+', canonical[:600])
        if len(sentences) > 1:
            canonical = '. '.join(sentences[:-1]) + '.'
        else:
            canonical = canonical[:500] + '...'

    return canonical


def detect_language(text: str) -> str:
    """
    Detect the language of the input text.

    Returns ISO 639-1 language code (e.g., 'en', 'hi', 'ta').
    Falls back to 'en' if detection fails.
    """
    if not text or len(text) < 10:
        return "en"

    # Simple heuristic-based detection for common Indian languages

    # Hindi/Devanagari script
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"

    # Tamil script
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "ta"

    # Telugu script
    if re.search(r'[\u0C00-\u0C7F]', text):
        return "te"

    # Bengali script
    if re.search(r'[\u0980-\u09FF]', text):
        return "bn"

    # Malayalam script
    if re.search(r'[\u0D00-\u0D7F]', text):
        return "ml"

    # Kannada script
    if re.search(r'[\u0C80-\u0CFF]', text):
        return "kn"

    # Gujarati script
    if re.search(r'[\u0A80-\u0AFF]', text):
        return "gu"

    # Arabic script (Urdu)
    if re.search(r'[\u0600-\u06FF]', text):
        return "ur"

    # Default to English for Latin script
    return "en"


def get_claim_topics(text: str, use_llm: bool = False) -> List[str]:
    """
    Extract potential topics from a claim text.
    """
    topics: List[str] = []
    text_lower = text.lower()

    topic_keywords = {
        "health": ["vaccine", "covid", "corona", "virus", "medicine", "cure", "treatment", "disease", "health", "hospital", "doctor"],
        "politics": ["government", "election", "politician", "minister", "party", "vote", "parliament", "law", "policy"],
        "science": ["research", "study", "scientist", "discovery", "experiment", "technology", "climate", "environment"],
        "finance": ["money", "bank", "economy", "tax", "investment", "stock", "bitcoin", "crypto", "loan"],
        "social": ["religion", "caste", "community", "riot", "protest", "violence", "discrimination"],
        "disaster": ["earthquake", "flood", "cyclone", "tsunami", "fire", "accident", "emergency"],
        "food": ["food", "water", "nutrition", "diet", "eating", "drinking", "organic"],
        "technology": ["phone", "internet", "5g", "radiation", "hacking", "privacy", "data", "whatsapp", "app"],
        "misinformation": ["hoax", "fake", "forward", "share", "urgent", "breaking", "secret", "exposed", "truth"],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            topics.append(topic)

    if use_llm and len(text) > 20:
        try:
            llm_topics = _extract_topics_with_llm(text)
            topics = list(set(topics + llm_topics))
        except Exception as e:
            logger.warning(f"LLM topic extraction failed: {e}")

    return topics if topics else ["general"]


def _extract_topics_with_llm(text: str) -> List[str]:
    """
    Placeholder for LLM-based topic extraction.
    """
    model = _get_embedding_model()
    if model is None:
        return []
    try:
        return []
    except Exception as e:
        logger.error(f"LLM topic extraction failed: {e}")
        return []
