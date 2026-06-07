#!/usr/bin/env python3
"""
Test Local Model Integration for CTOAi

Usage:
    python scripts/test_local_model.py
    python scripts/test_local_model.py --health-only
    python scripts/test_local_model.py --invoke "Your prompt here"
"""

import argparse
import os
import sys
from pathlib import Path

# Add repo root to path so we can import runner modules
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runner.llm_providers import get_provider


def test_health():
    """Test provider health check."""
    print("[test] Checking provider health...")
    try:
        provider = get_provider()
        print(f"[test] Provider type: {provider.__class__.__name__}")
        
        if provider.health():
            print("[test] ✓ Provider health check PASSED")
            return True
        else:
            print("[test] ✗ Provider health check FAILED")
            return False
    except Exception as e:
        print(f"[test] ✗ Provider initialization failed: {e}")
        return False


def test_completion(prompt: str):
    """Test model completion."""
    print(f"\n[test] Invoking model with prompt: {prompt[:60]}...")
    try:
        provider = get_provider()
        
        response = provider.complete(
            system_prompt=(
                "You are a helpful coding assistant. "
                "Respond concisely with valid code or markdown."
            ),
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=512,
        )
        
        print(f"\n[test] ✓ Model response received ({len(response)} chars)")
        print(f"\n{'='*60}")
        print(response)
        print(f"{'='*60}\n")
        return True
        
    except Exception as e:
        print(f"[test] ✗ Model completion failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test local model integration for CTOAi"
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Only run health check",
    )
    parser.add_argument(
        "--invoke",
        type=str,
        help="Invoke model with custom prompt",
    )
    args = parser.parse_args()

    print(f"[test] CTOAi Local Model Integration Test")
    print(f"[test] Provider mode: {os.getenv('CTOA_LLM_PROVIDER', 'auto')}")
    print(f"[test] Local model URL: {os.getenv('CTOA_LOCAL_MODEL_URL', 'http://localhost:11434/v1')}")
    print()

    # Health check
    if not test_health():
        print("\n[test] ✗ Health check failed, skipping completion test")
        return 1

    if args.health_only:
        print("\n[test] ✓ Health check only - complete")
        return 0

    # Test completion
    if args.invoke:
        if not test_completion(args.invoke):
            return 1
    else:
        # Default test prompts
        test_prompts = [
            "Write a one-line Python hello world function.",
            "What is Docker Model Runner?",
        ]
        
        for prompt in test_prompts:
            if not test_completion(prompt):
                return 1

    print("[test] ✓ All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
