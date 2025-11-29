# Setup OpenAI for REAL Fact-Checking

## Why OpenAI Instead of Pattern Matching?

❌ **Pattern matching (hoax library)** = Hardcoded responses, only works for known hoaxes
✅ **OpenAI GPT** = REAL AI analysis, works for ANY claim, truly dynamic

---

## Setup Steps:

### 1. Get OpenAI API Key

1. Go to: https://platform.openai.com/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

### 2. Install OpenAI Package

```bash
pip install openai
```

### 3. Add API Key to `.env`

Edit `.env` file and replace:
```
OPENAI_API_KEY=your-api-key-here
```

With your actual key:
```
OPENAI_API_KEY=sk-proj-...your-actual-key...
```

### 4. Choose Model (Optional)

In `.env`, you can choose:

**Option A: GPT-3.5-Turbo** (Default, Recommended)
- Faster
- Cheaper ($0.0015 per 1K tokens)
- Good quality
```
OPENAI_MODEL=gpt-3.5-turbo
```

**Option B: GPT-4**
- Better quality
- More expensive ($0.03 per 1K tokens)
- Slower
```
OPENAI_MODEL=gpt-4
```

For most cases, **gpt-3.5-turbo is perfect**!

### 5. Backend is Already Configured!

The `.env` already has:
```
LLM_BACKEND=openai
```

---

## Test It!

### Quick Test:
```bash
python -c "
from app.services.llm_client import get_llm_client

client = get_llm_client()
print(f'Client type: {type(client).__name__}')
print(f'Is available: {client.is_available()}')

if client.is_available():
    result = client.generate('Say hello!')
    print(f'Test response: {result}')
"
```

Expected output:
```
Client type: OpenAIAdapter
Is available: True
Test response: Hello! How can I assist you today?
```

### Full Fact-Check Test:
```bash
python test_multiple_forwards.py
```

This will test all 5 WhatsApp forwards with **REAL OpenAI fact-checking**!

---

## What Happens Now?

### OLD Way (Pattern Matching):
```
User sends message
    ↓
Match pattern in hoax library?
    ├─→ Yes → Return hardcoded response
    └─→ No → Use weak local model → Bad results
```

### NEW Way (Real AI):
```
User sends message
    ↓
Detect claim
    ↓
Search DuckDuckGo for evidence
    ↓
Send to GPT-3.5/GPT-4:
    - Claim: "..."
    - Evidence: [actual search results]
    ↓
GPT analyzes and generates:
    - Verdict (TRUE/FALSE/etc)
    - Myth/Fact explanation
    - Why it matters
    - Sources cited
    ↓
Return REAL, dynamic rebuttal
```

---

## Cost Estimation

### Per Fact-Check:
- Claim: ~100 tokens
- Evidence: ~300 tokens
- Response: ~400 tokens
- **Total: ~800 tokens ≈ $0.0012 per check**

### Monthly (1000 claims/day):
- 1000 claims/day × 30 days = 30,000 checks
- 30,000 × $0.0012 = **~$36/month**

**Very affordable for real AI fact-checking!**

---

## Fallback Behavior

If OpenAI fails (API down, no credits, etc.):
1. Falls back to `local_transformers` (flan-t5-base)
2. Falls back to `FallbackAdapter` (keyword matching)

Your backend always works, even without OpenAI!

---

## Optional: Enable Hoax Library for Speed

If you want to use hoax library for KNOWN hoaxes (instant, free) and OpenAI for UNKNOWN claims:

In `app/services/verification.py`, line ~387, change:
```python
llm_response = summarize(claim_text, evidence_snippets)
```

To:
```python
llm_response = summarize(claim_text, evidence_snippets, use_hoax_library=True)
```

This gives you:
- **Known hoaxes**: Instant response from library (free)
- **Unknown claims**: Real OpenAI analysis (costs $0.0012)

**Best of both worlds!**

---

## Ready to Test?

1. Add your OpenAI API key to `.env`
2. Run: `python test_multiple_forwards.py`
3. Watch REAL fact-checking in action! 🚀
