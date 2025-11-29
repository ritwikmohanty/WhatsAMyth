"""Quick test script to verify LLM setup"""
import sys
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("Testing LLM Configuration")
print("=" * 60)

# Test 1: Check if transformers is installed
print("\n1. Checking transformers installation...")
try:
    import transformers
    import torch
    print(f"   [OK] transformers version: {transformers.__version__}")
    print(f"   [OK] torch version: {torch.__version__}")
    print(f"   [OK] CUDA available: {torch.cuda.is_available()}")
except ImportError as e:
    print(f"   [FAIL] Missing dependency: {e}")
    sys.exit(1)

# Test 2: Check config
print("\n2. Loading configuration...")
try:
    from app.config import get_settings
    settings = get_settings()
    print(f"   [OK] LLM Backend: {settings.llm_backend}")
    print(f"   [OK] Model: {settings.transformers_model}")
except Exception as e:
    print(f"   [FAIL] Config error: {e}")
    sys.exit(1)

# Test 3: Try to load the LLM client
print("\n3. Testing LLM client...")
try:
    from app.services.llm_client import get_llm_client
    client = get_llm_client()
    print(f"   [OK] Client type: {type(client).__name__}")

    if hasattr(client, 'model_name'):
        print(f"   [OK] Model name: {client.model_name}")

    if client.is_available():
        print(f"   [OK] Client is available")
    else:
        print(f"   [FAIL] Client is NOT available")

except Exception as e:
    print(f"   [FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Try a simple generation
print("\n4. Testing text generation...")
try:
    test_prompt = "Answer this question: Is 2+2 equal to 4? Answer with YES or NO."
    result = client.generate(test_prompt, max_tokens=50)
    print(f"   Prompt: {test_prompt}")
    print(f"   Result: {result[:200] if result else '[EMPTY]'}")

    if result:
        print(f"   [OK] Generation successful")
    else:
        print(f"   [FAIL] Generation returned empty")

except Exception as e:
    print(f"   [FAIL] Generation error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test the verification prompt
print("\n5. Testing verification format...")
try:
    from app.services.llm_client import summarize

    test_claim = "The sky is blue."
    test_evidence = ["Scientific studies confirm that the sky appears blue due to Rayleigh scattering."]

    result = summarize(test_claim, test_evidence)
    print(f"   Claim: {test_claim}")
    print(f"   Result length: {len(result) if result else 0} chars")
    print(f"   Result preview:\n{result[:300] if result else '[EMPTY]'}")

    # Check if it has the expected format
    has_status = "STATUS:" in result
    has_short_reply = "SHORT_REPLY:" in result

    print(f"\n   Has STATUS: {has_status}")
    print(f"   Has SHORT_REPLY: {has_short_reply}")

    if has_status and has_short_reply:
        print(f"   [OK] Format looks correct")
    else:
        print(f"   [FAIL] Format is incorrect - model may not be following instructions")

except Exception as e:
    print(f"   [FAIL] Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
