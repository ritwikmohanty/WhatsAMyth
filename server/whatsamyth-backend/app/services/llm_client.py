"""
LLM Client
Adapter pattern for calling different LLM backends (Ollama or local transformers).
"""

import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class LLMAdapter(ABC):
    """Base class for LLM adapters."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3
    ) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM backend is available."""
        pass


class OllamaAdapter(LLMAdapter):
    """Adapter for Ollama local LLM server."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._available: Optional[bool] = None
    
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            self._available = response.status_code == 200
            if self._available:
                logger.info(f"Ollama server available at {self.base_url}")
            return self._available
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._available = False
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3
    ) -> str:
        """Generate text using Ollama API."""
        if not self.is_available():
            logger.error("Ollama not available")
            return ""
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return ""


class TransformersAdapter(LLMAdapter):
    """Adapter for local HuggingFace transformers models."""

    def __init__(self, model_name: str = "google/flan-t5-base"):
        self.model_name = model_name
        self._pipeline = None
        self._tokenizer = None
        self._available: Optional[bool] = None
        self._is_seq2seq = None  # Track if model is seq2seq (T5) or causal (GPT)
    
    def _load_model(self) -> bool:
        """Load the model and tokenizer."""
        if self._pipeline is not None:
            return True

        try:
            from transformers import pipeline, AutoTokenizer, AutoConfig
            import torch

            logger.info(f"Loading transformers model: {self.model_name}")

            # Determine device
            device = "cuda" if torch.cuda.is_available() else "cpu"

            # Load config to detect model type
            config = AutoConfig.from_pretrained(self.model_name)
            model_type = config.model_type.lower()

            # Detect if model is seq2seq (T5, BART, etc.) or causal (GPT, LLaMA, etc.)
            seq2seq_types = ["t5", "bart", "pegasus", "mbart", "mt5"]
            self._is_seq2seq = model_type in seq2seq_types

            task = "text2text-generation" if self._is_seq2seq else "text-generation"
            logger.info(f"Model type: {model_type}, using task: {task}")

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            # Create pipeline
            self._pipeline = pipeline(
                task,
                model=self.model_name,
                tokenizer=self._tokenizer,
                device_map="auto" if device == "cuda" else None,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )

            logger.info(f"Model loaded on {device}")
            return True

        except Exception as e:
            logger.error(f"Failed to load transformers model: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if model can be loaded."""
        if self._available is not None:
            return self._available
        
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3
    ) -> str:
        """Generate text using local transformers pipeline."""
        if not self._load_model():
            return ""

        try:
            # Format prompt based on model type
            if self._is_seq2seq:
                # T5/BART models: just concatenate system prompt and user prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                else:
                    full_prompt = prompt

                # Generate (use max_new_tokens for T5 to ensure enough output space)
                result = self._pipeline(
                    full_prompt,
                    max_new_tokens=max_tokens,  # Use max_new_tokens instead of max_length
                    temperature=temperature if temperature > 0 else 1.0,
                    do_sample=temperature > 0,
                    num_return_sequences=1,
                    early_stopping=True
                )

                if result and len(result) > 0:
                    generated = result[0].get("generated_text", "")
                    return generated.strip()
            else:
                # Causal LM (GPT-style): use chat formatting
                if system_prompt:
                    full_prompt = f"<|system|>\n{system_prompt}</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
                else:
                    full_prompt = f"<|user|>\n{prompt}</s>\n<|assistant|>\n"

                # Generate
                result = self._pipeline(
                    full_prompt,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self._tokenizer.eos_token_id,
                    return_full_text=False
                )

                if result and len(result) > 0:
                    generated = result[0].get("generated_text", "")
                    # Clean up any trailing special tokens
                    generated = generated.split("</s>")[0].strip()
                    return generated

            return ""

        except Exception as e:
            logger.error(f"Transformers generation failed: {e}")
            return ""


class OpenRouterAdapter(LLMAdapter):
    """Adapter for OpenRouter API using requests (no openai package needed)."""

    def __init__(self, api_key: str, model: str = "deepseek/deepseek-r1-0528-qwen3-8b"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if API key is configured."""
        if self._available is not None:
            return self._available

        if not self.api_key or self.api_key == "your-api-key-here":
            logger.warning("OpenRouter API key not configured")
            self._available = False
            return False

        self._available = True
        return True

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3
    ) -> str:
        """Generate text using OpenRouter API."""
        if not self.is_available():
            return ""

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call OpenRouter API directly
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return ""

        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return ""


class FallbackAdapter(LLMAdapter):
    """
    Fallback adapter that uses rule-based responses when no LLM is available.
    Provides basic fact-checking verdicts based on keyword matching.
    """
    
    # Known false claims patterns
    FALSE_CLAIM_PATTERNS = [
        "microchip", "5g", "bill gates", "population control",
        "magnetic", "dna altering", "tracking", "nanobots",
        "chemtrails", "flat earth", "moon landing fake"
    ]
    
    # Known true/verified patterns (usually from official sources)
    TRUE_CLAIM_PATTERNS = [
        "wash hands", "wear mask", "social distance",
        "vaccines are safe", "vaccines are effective"
    ]
    
    def is_available(self) -> bool:
        """Fallback is always available."""
        return True
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3
    ) -> str:
        """Generate a basic response based on keyword matching."""
        prompt_lower = prompt.lower()
        
        # Check for known false claims
        for pattern in self.FALSE_CLAIM_PATTERNS:
            if pattern in prompt_lower:
                return self._generate_false_response(pattern)
        
        # Check for known true claims
        for pattern in self.TRUE_CLAIM_PATTERNS:
            if pattern in prompt_lower:
                return self._generate_true_response(pattern)
        
        # Default unknown response
        return self._generate_unknown_response()
    
    def _generate_false_response(self, pattern: str) -> str:
        from app.services.rebuttal import get_rebuttal_generator
        from app.models import ClaimStatus

        # Generate deadly rebuttal for common false patterns
        rebuttal_gen = get_rebuttal_generator()

        # Pattern-specific claims and evidence
        if "microchip" in pattern or "tracking" in pattern:
            claim = "Vaccines contain microchips for tracking"
            evidence = ["CDC and WHO confirm vaccines do not contain microchips or tracking devices"]
        elif "5g" in pattern:
            claim = "5G technology causes health issues"
            evidence = ["WHO states 5G networks do not pose health risks when within international guidelines"]
        elif "bill gates" in pattern:
            claim = "Bill Gates conspiracy theory"
            evidence = ["Fact-checkers have debunked Bill Gates conspiracy theories"]
        else:
            claim = f"Claim related to {pattern}"
            evidence = [f"This claim contains common misinformation patterns related to {pattern}"]

        rebuttals = rebuttal_gen.generate_deadly_rebuttal(
            status=ClaimStatus.FALSE,
            claim_text=claim,
            evidence_snippets=evidence,
            llm_explanation=f"This claim contains common misinformation patterns. Official health authorities recommend verifying with trusted sources before sharing.",
            confidence=0.7
        )

        return f"""STATUS: FALSE
CONFIDENCE: 0.7
SHORT_REPLY: {rebuttals['short_reply']}
LONG_REPLY: {rebuttals['long_reply']}
SOURCES: General fact-checking guidance"""

    def _generate_true_response(self, pattern: str) -> str:
        return f"""STATUS: TRUE
CONFIDENCE: 0.8
SHORT_REPLY: ✅ This appears to be accurate public health guidance based on official recommendations.
LONG_REPLY: This claim aligns with official public health recommendations. Always follow guidance from official health authorities in your region.
SOURCES: General public health guidelines"""

    def _generate_unknown_response(self) -> str:
        return """STATUS: UNKNOWN
CONFIDENCE: 0.3
SHORT_REPLY: ❓ *UNVERIFIED* - We could not verify this claim.\n\n⚠️ *Check official sources before sharing.*
LONG_REPLY: This claim requires further verification. We recommend checking multiple authoritative sources before believing or sharing this information.
SOURCES: Unable to automatically verify"""


def get_llm_client() -> LLMAdapter:
    """
    Get the appropriate LLM client based on configuration.

    Falls back gracefully if configured backend is not available.
    """
    backend = settings.llm_backend.lower()

    if backend == "openai":
        adapter = OpenRouterAdapter(
            api_key=settings.openai_api_key,
            model=settings.openai_model
        )
        if adapter.is_available():
            logger.info(f"Using OpenRouter with DeepSeek: {settings.openai_model}")
            return adapter
        logger.warning("OpenRouter not available, falling back to transformers")
        backend = "local_transformers"  # Fall through

    if backend == "ollama":
        adapter = OllamaAdapter(
            base_url=settings.ollama_url,
            model=settings.ollama_model
        )
        if adapter.is_available():
            return adapter
        logger.warning("Ollama not available, falling back to transformers")

    if backend in ("local_transformers", "transformers"):
        adapter = TransformersAdapter(model_name=settings.transformers_model)
        if adapter.is_available():
            return adapter
        logger.warning("Transformers not available, using fallback")

    # Return fallback
    logger.info("Using fallback rule-based adapter")
    return FallbackAdapter()

import re

def _assess_evidence_coverage(claim_text: str, evidence_snippets: List[str]) -> str:
    """
    Very simple heuristic: how much do the evidence snippets overlap with the claim?
    Returns one of: 'NONE', 'LOW', 'MEDIUM', 'HIGH'.

    Used only to *tell the LLM* how reliable the evidence set is, so it can
    choose UNKNOWN/UNVERIFIABLE instead of FALSE when coverage is weak.
    """
    if not evidence_snippets:
        return "NONE"

    claim_tokens = re.findall(r"\b\w+\b", claim_text.lower())
    claim_tokens = [t for t in claim_tokens if len(t) > 3]  # ignore tiny words
    if not claim_tokens:
        return "LOW"

    joined_evidence = " ".join(evidence_snippets).lower()
    hits = {t for t in claim_tokens if t in joined_evidence}
    ratio = len(hits) / max(1, len(claim_tokens))

    if ratio == 0:
        return "NONE"
    elif ratio < 0.2:
        return "LOW"
    elif ratio < 0.5:
        return "MEDIUM"
    else:
        return "HIGH"


def summarize(
    claim_text: str,
    evidence_snippets: List[str],
    system_prompt: Optional[str] = None,
    use_hoax_library: bool = False
) -> str:
    """
    Summarize evidence for a claim using the configured LLM.

    Performs REAL fact-checking by analyzing evidence with AI.

    IMPORTANT LOGIC:
    - FALSE: only if there is clear, credible evidence that the claim is wrong
      or has been debunked.
    - TRUE / PARTIALLY_TRUE: when evidence supports the claim (fully or partially).
    - MISLEADING: when some elements are true but key details are wrong/exaggerated.
    - UNKNOWN / UNVERIFIABLE: when evidence is weak, unrelated, or absent.
      Lack of evidence alone MUST NOT be treated as proof that the claim is false.
    """
    from app.services.rebuttal import get_rebuttal_generator
    from app.models import ClaimStatus

    # Optional: Check hoax library first (faster for known myths)
    if use_hoax_library:
        from app.services.hoax_library import get_hoax_library
        hoax_library = get_hoax_library()
        matched_hoax = hoax_library.match_hoax(claim_text)

        if matched_hoax:
            logger.info(f"Matched common hoax: {matched_hoax['category']}")
            rebuttal = hoax_library.generate_rebuttal(matched_hoax)
            return f"""STATUS: {matched_hoax['status'].value}
CONFIDENCE: 0.95
SHORT_REPLY: {rebuttal['short_reply']}
LONG_REPLY: {rebuttal['long_reply']}
SOURCES: {', '.join(rebuttal['sources'])}"""

    # REAL fact-checking with LLM
    client = get_llm_client()

    # Build evidence text
    if evidence_snippets:
        evidence_text = "\n".join([f"{i+1}. {e}" for i, e in enumerate(evidence_snippets[:5])])
    else:
        evidence_text = "No evidence found from search."

    # Assess coverage: do the snippets actually talk about the same entities/topics?
    coverage = _assess_evidence_coverage(claim_text, evidence_snippets)

    # Check model type
    is_simple_model = False
    if isinstance(client, TransformersAdapter):
        client._load_model()
        is_simple_model = client._is_seq2seq

    # ------------- CAPABLE MODELS (OpenRouter / Ollama) -------------
    if isinstance(client, OpenRouterAdapter) or isinstance(client, OllamaAdapter):
        system_prompt = """You are a professional fact-checker.

Your job:
- Compare the claim with the evidence.
- Use common sense and background knowledge, BUT DO NOT invent specific events or dates that are not supported.
- Be conservative: if evidence is weak or unrelated, prefer UNKNOWN or UNVERIFIABLE over FALSE.

VERY IMPORTANT DECISION RULES:

1. When to use FALSE:
   - ONLY if there is clear, credible evidence that the claim is wrong or has been debunked.
   - Example: official statements or multiple reliable sources explicitly refuting the claim.

2. When to use TRUE:
   - Evidence strongly supports the main point of the claim.

3. When to use PARTIALLY_TRUE:
   - The core idea is supported, but some important details (like exact date, numbers, location) are incorrect or unconfirmed.
   - Example: countries do have a trade agreement in general, but not "signed TODAY" as claimed.

4. When to use MISLEADING:
   - The claim mixes some true facts with exaggerations, omissions, or wrong context that can seriously mislead people.

5. When to use UNKNOWN or UNVERIFIABLE:
   - Evidence is sparse, generic, out of date, or does not specifically address the claim.
   - There is no strong supporting OR refuting evidence.
   - NEVER mark a claim as FALSE just because you cannot find evidence.

You MUST follow these rules strictly."""

        prompt = f"""Fact-check this claim based on the evidence provided.

CLAIM:
{claim_text}

EVIDENCE COVERAGE: {coverage}
(Interpretation: 
- NONE/LOW = most snippets do NOT mention the key entities/claims directly.
- MEDIUM/HIGH = evidence substantially overlaps with the claim.)

EVIDENCE SNIPPETS:
{evidence_text}

Instructions for you:
- If coverage is NONE or LOW and you see no explicit refutation, strongly prefer STATUS: UNKNOWN or STATUS: UNVERIFIABLE.
- If background knowledge supports general relationships (e.g., countries often have trade agreements), but the specific claim (e.g., "signed today") is not confirmed, prefer PARTIALLY_TRUE or MISLEADING over TRUE or FALSE.
- Only assign FALSE if you have strong, direct evidence that the claim is wrong.

Now provide your analysis in this EXACT format:

STATUS: [Choose ONE: TRUE, FALSE, MISLEADING, PARTIALLY_TRUE, UNVERIFIABLE, or UNKNOWN]
CONFIDENCE: [Number from 0.0 to 1.0]
SHORT_REPLY: [Write a WhatsApp-ready response. Use:
  - ✅ *TRUE* when supported
  - ❌ *FALSE - This is a HOAX!* only when clearly debunked
  - ⚠️ *MISLEADING* or *PARTIALLY TRUE* when mixed/partial
  - ❓ *UNVERIFIED* when UNKNOWN/UNVERIFIABLE.
  Summarize the myth vs fact in 2–3 sentences, and if FALSE explain briefly why sharing is harmful.]
LONG_REPLY: [Provide a detailed 3–4 paragraph fact-check explanation including what the evidence shows, any nuance (partial truth), and recommendations.]
SOURCES: [List the key authoritative sources from the evidence, if any. If coverage is NONE/LOW, clearly say that no directly relevant sources were found.]

Your response:"""

        response = client.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3
        )

        if "STATUS:" in response and "SHORT_REPLY:" in response:
            return response
        else:
            logger.warning("LLM response not in expected format, attempting to parse...")
            # fall through to deadly rebuttal path below

    # ------------- SIMPLE SEQ2SEQ MODELS (T5, etc.) -------------
    elif is_simple_model:
        status_prompt = f"""You are a careful fact-checker.

Claim: {claim_text}
Evidence coverage: {coverage}
Evidence snippets:
{evidence_text}

Based on the rules:
- FALSE only if there is strong, direct evidence that the claim is wrong.
- TRUE if evidence strongly supports it.
- PARTIALLY_TRUE if core idea is right but details are off/unconfirmed.
- MISLEADING if partly true but clearly misleads people.
- UNKNOWN or UNVERIFIABLE if evidence is weak, generic, or unrelated.

Answer with exactly ONE word:
TRUE, FALSE, MISLEADING, PARTIALLY_TRUE, UNVERIFIABLE, or UNKNOWN.

Answer:"""

        status_response = client.generate(
            status_prompt,
            max_tokens=10,
            temperature=0.3
        ).strip().upper()

        status_value = "UNKNOWN"
        for valid_status in ["TRUE", "FALSE", "MISLEADING", "PARTIALLY_TRUE", "UNVERIFIABLE", "UNKNOWN"]:
            if valid_status in status_response:
                status_value = valid_status
                break

        # Short explanation
        reply_prompt = f"""Explain in 2–3 sentences why this claim is {status_value.lower()} given the evidence.

Claim: {claim_text}
Evidence coverage: {coverage}
Evidence snippets:
{evidence_text}

Explanation (2–3 sentences):"""

        short_reply = client.generate(
            reply_prompt,
            max_tokens=500,
            temperature=0.5
        ).strip()

        # Longer explanation
        long_prompt = f"""Provide a more detailed fact-check explanation (4–6 sentences) covering:
- What the evidence shows
- Whether any parts of the claim are true
- Any missing information or uncertainty
- What people should keep in mind before sharing

Claim: {claim_text}
Evidence coverage: {coverage}
Evidence snippets:
{evidence_text}

Detailed fact-check:"""

        long_reply = client.generate(
            long_prompt,
            max_tokens=250,
            temperature=0.5
        ).strip()

        status_map = {
            "TRUE": ClaimStatus.TRUE,
            "FALSE": ClaimStatus.FALSE,
            "MISLEADING": ClaimStatus.MISLEADING,
            "PARTIALLY_TRUE": ClaimStatus.PARTIALLY_TRUE,
            "UNVERIFIABLE": ClaimStatus.UNVERIFIABLE,
            "UNKNOWN": ClaimStatus.UNKNOWN
        }
        claim_status = status_map.get(status_value, ClaimStatus.UNKNOWN)
        confidence = 0.8 if status_value in ["TRUE", "FALSE"] else 0.5

        rebuttal_gen = get_rebuttal_generator()
        rebuttals = rebuttal_gen.generate_deadly_rebuttal(
            status=claim_status,
            claim_text=claim_text,
            evidence_snippets=evidence_snippets,
            llm_explanation=f"{short_reply} {long_reply}",
            confidence=confidence
        )

        return f"""STATUS: {status_value}
CONFIDENCE: {confidence}
SHORT_REPLY: {rebuttals['short_reply']}
LONG_REPLY: {rebuttals['long_reply']}
SOURCES: {', '.join(rebuttal_gen._extract_sources(evidence_snippets)) if evidence_snippets else 'No sources available'}"""

    # ------------- VERY SIMPLE / FALLBACK MODELS -------------
    else:
        prompt = f"""You are a cautious fact-checker.

Claim: {claim_text}

Evidence coverage: {coverage}
Evidence snippets:
{evidence_text}

Rules:
- FALSE only if strong, direct evidence shows the claim is wrong.
- TRUE if evidence strongly supports the claim.
- PARTIALLY_TRUE if core idea is right but some important details are off or unconfirmed.
- MISLEADING if it mixes some truth with exaggeration or missing context.
- UNKNOWN or UNVERIFIABLE if the evidence is weak, generic, or unrelated. Never mark FALSE just because you can't confirm it.

Provide a verdict in this format:
STATUS: [TRUE/FALSE/MISLEADING/PARTIALLY_TRUE/UNVERIFIABLE/UNKNOWN]
CONFIDENCE: [0.0-1.0]
SHORT_REPLY: [One-sentence verdict suitable for WhatsApp]
LONG_REPLY: [3–5 sentence explanation]
SOURCES: [Evidence sources or 'No directly relevant sources found']

Verdict:
"""
        return client.generate(
            prompt,
            system_prompt=None,
            max_tokens=384,
            temperature=0.7
        )
