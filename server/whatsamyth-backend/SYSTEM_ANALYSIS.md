# WhatsAMyth Backend - Current State Analysis

## ✅ What IS Working

### 1. **Claim Detection**
- ✓ Rule-based pattern matching (`app/services/detection.py:91-120`)
- ✓ Detects conspiracy indicators, health claims, authority claims, urgency triggers
- ✓ Filters out questions, opinions, greetings
- **Example**: WhatsApp shutdown hoax → Detected as claim ✓

### 2. **Canonical Claim Extraction**
- ✓ Removes forwarding prefixes ("FWD:", "Forwarded message")
- ✓ Strips URLs, emojis, excessive punctuation
- ✓ Removes calls-to-action ("Share this", "Forward to all")
- **Result**: Clean claim text for processing

### 3. **Clustering (Memory Check)**
- ✓ Uses sentence-transformers embeddings
- ✓ FAISS index for fast similarity search
- ✓ Checks if claim seen before (threshold: 0.75)
- ✓ If seen → returns existing verdict (instant)
- ✓ If new → creates new cluster & runs verification
- **Location**: `app/services/clustering.py`

### 4. **Memory Graph**
- ✓ Tracks claim clusters as nodes
- ✓ Tracks relationships between claims
- ✓ Detects spikes (sudden increase in messages)
- ✓ Persists to `/data/memory_graph.json`
- **Location**: `app/services/memory_graph.py`
- **Integration**: Line 210-218 in `app/routers/messages.py`

### 5. **Verification Pipeline**
- ✓ DuckDuckGo search for evidence
- ✓ Filters to authoritative domains (WHO, CDC, gov.in, PIB, fact-checkers)
- ✓ LLM analysis with flan-t5-base
- ✓ Multi-step prompting for T5 models
- **Location**: `app/services/verification.py`

### 6. **Structured Output**
- ✓ STATUS: TRUE/FALSE/MISLEADING/UNKNOWN
- ✓ CONFIDENCE: 0.0-1.0
- ✓ SHORT_REPLY: WhatsApp-ready message
- ✓ LONG_REPLY: Detailed explanation
- ✓ SOURCES: Evidence used

### 7. **TTS Audio Generation**
- ✓ Attempts to generate audio reply
- ✓ Uses pyttsx3 (cross-platform)
- ✓ Returns audio URL: `/media/replies/{message_id}.mp3`
- ⚠️ May fail if pyttsx3 not working or ffmpeg missing

---

## ❌ What's NOT Working (From Your Vision)

### 1. **Not "Agentic" Enough**
**Current**: Rule-based claim detection + full canonical text to LLM
**Your Vision**:
- Agent breaks down claim into key assertions
- Extracts specific keywords/entities
- Sends only relevant keywords to LLM
- More sophisticated decomposition

**Gap**: No keyword extraction or claim decomposition before LLM

### 2. **Rebuttals Not "Deadly"**
**Current Output**:
```
SHORT_REPLY: WhatsApp has never announced shutdowns or account deletion for not forwarding messages
```

**Your Vision** (punchy, authoritative):
```
❌ FALSE - This is a common hoax!

WhatsApp NEVER asks users to forward messages to avoid deletion. This fake message has been debunked by PIB Fact Check. DO NOT FORWARD.

Verified by: PIB, WhatsApp Official
```

**Gap**:
- No emoji/formatting in replies
- Not authoritative/commanding tone
- Missing "DO NOT FORWARD" warnings
- No citation of official sources

### 3. **Topic Detection Too Basic**
**Current**: Keyword matching (`app/services/detection.py:335-364`)
- Just checks if words like "vaccine", "covid" appear

**Your Vision**: LLM-based topic extraction
- Nuanced categorization
- Multi-label topics
- Detect emerging themes

### 4. **No Keyword/Entity Extraction**
**Current**: Sends entire canonical claim to LLM

**Your Vision**: Extract specific claims
- "WhatsApp shutting down 11:30pm-6am" → Entity: WhatsApp, Time: 11:30pm-6am, Claim: shutdown
- "PM Narendra Modi said..." → Authority: PM, Entity: Narendra Modi
- Target these specific elements for verification

---

## 📊 Current Flow (What Actually Happens)

```
User sends WhatsApp forward
       ↓
[1] Claim Detection (rule-based patterns)
       ↓
[2] Extract Canonical Claim (remove noise)
       ↓
[3] Generate Embedding (sentence-transformers)
       ↓
[4] Check Clustering (FAISS search)
       ├─→ Found similar? → Use existing verdict (INSTANT)
       └─→ New claim? → Continue
       ↓
[5] Run Verification:
    - DuckDuckGo search (authoritative domains)
    - Extract evidence snippets
    - LLM analysis (3-step for T5):
      Step 1: "Is this TRUE/FALSE?"
      Step 2: "Why is it false?" (short)
      Step 3: "Detailed explanation" (long)
    - Construct structured response
       ↓
[6] Save Verdict to DB
       ↓
[7] Update Memory Graph
    - Add cluster node
    - Detect spike (sudden increase)
       ↓
[8] Generate TTS Audio (optional)
       ↓
[9] Return Response:
    {
      "cluster_status": "FALSE",
      "short_reply": "...",
      "audio_url": "/media/replies/123.mp3"
    }
```

---

## 🎯 Missing Features for Your Vision

### 1. **Claim Decomposition Agent**
```python
# TODO: Add to app/services/decomposition.py
def decompose_claim(text: str) -> Dict[str, Any]:
    """
    Break claim into structured components.

    Returns:
        {
            "entities": ["WhatsApp", "PM Modi"],
            "assertions": [
                "WhatsApp will shut down 11:30pm-6am",
                "Declared by central government"
            ],
            "authority_cited": "Narendra Modi (PM)",
            "urgency_level": "high",
            "call_to_action": "forward to contacts"
        }
    """
```

### 2. **Enhanced Rebuttal Generator**
```python
# TODO: Add to app/services/rebuttal.py
def generate_deadly_rebuttal(
    claim: str,
    verdict: str,
    evidence: List[str],
    authority: Optional[str] = None
) -> str:
    """
    Generate punchy, shareable WhatsApp rebuttal.

    Format:
        ❌ FALSE - This is a hoax!

        [Claim summary]

        FACT: [Counter-evidence from official source]

        ⚠️ DO NOT FORWARD

        Verified by: [PIB/WHO/Official source]
    """
```

### 3. **Smart Topic Extraction**
```python
# TODO: Use LLM for topic extraction
def extract_topics_with_llm(claim: str) -> List[str]:
    """Use LLM to extract nuanced topics."""
    prompt = f"What topics does this claim relate to? {claim}"
    # Returns: ["misinformation", "WhatsApp", "government", "technology"]
```

### 4. **Keyword-Based Evidence Search**
```python
# TODO: Extract keywords before search
def extract_search_keywords(claim: str) -> List[str]:
    """Extract key terms for evidence search."""
    # "WhatsApp shutdown PM Modi" → ["WhatsApp shutdown", "PM Modi", "government WhatsApp"]
    # Then search DuckDuckGo with these specific terms
```

### 5. **Enhanced Memory Graph Queries**
```python
# TODO: Add methods to memory_graph.py
def get_trending_myths(days: int = 7) -> List[Dict]:
    """Return myths with spike in last N days."""

def get_related_claims(cluster_id: int) -> List[Dict]:
    """Find related debunked claims to include in rebuttal."""
```

---

## 🚀 Recommendations

### Immediate Improvements (High Impact)

1. **Better Rebuttals**:
   - Add emoji support (❌ ✅ ⚠️)
   - Format with bold/italic (WhatsApp markdown)
   - Add "DO NOT FORWARD" warnings
   - Cite official sources prominently

2. **Keyword Extraction**:
   - Use spaCy for entity extraction
   - Extract key claims before LLM
   - More targeted evidence search

3. **Topic Enhancement**:
   - Use flan-t5 for topic extraction
   - Multi-label classification
   - Track trending topics

### Medium-Term (Agentic Features)

4. **Claim Decomposition**:
   - Break claims into testable assertions
   - Extract entities, authorities, dates
   - Verify each assertion separately

5. **Memory Graph Enhancements**:
   - Trending myths dashboard
   - Related claims in rebuttal
   - Seasonal pattern detection

### Nice-to-Have

6. **Multi-language Support**:
   - Detect Hindi, Tamil, Telugu forwards
   - Generate rebuttals in same language

7. **Image/Video Analysis**:
   - Extract text from forwarded images (OCR)
   - Detect manipulated media

---

## Current Test Results

### WhatsApp Shutdown Hoax
```
Input: "WhatsApp will be off from 11:30 pm to 6:00 am daily. Declared by central govt. Message from Narendra Modi (PM)..."

Output:
✓ Detected as claim
✓ Status: FALSE
✓ Confidence: 0.8
✓ Short reply: "WhatsApp has never announced shutdowns or account deletion for not forwarding messages"

❌ But missing:
- Emoji/formatting
- Authoritative tone
- "DO NOT FORWARD" warning
- PIB citation
```

---

## Next Steps

1. Test the full API with the WhatsApp forward (restart server first)
2. Implement enhanced rebuttal formatting
3. Add keyword extraction
4. Improve topic detection with LLM
5. Add claim decomposition agent

Would you like me to implement any of these improvements?
