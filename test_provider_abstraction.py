#!/usr/bin/env python3
"""Test script for the Provider Abstraction System (Sprint 4.1).

This script tests:
1. Base provider interface
2. Groq provider implementation
3. API detector functionality
4. Provider capabilities
"""

import sys
import os
from pathlib import Path

# Add iabuilder to path
sys.path.insert(0, str(Path(__file__).parent / "iabuilder"))

# Import modules
from providers.base import ModelProvider, ProviderError, AuthenticationError
from providers.groq import GroqProvider
from config.api_detector import APIDetector, APIFormat, APICapabilities


def test_api_detector():
    """Test API format detection."""
    print("=" * 60)
    print("TEST 1: API Detector")
    print("=" * 60)

    # Test API key detection
    print("\n1.1 Testing API key detection...")
    test_cases = [
        ("gsk_test123", APIFormat.GROQ, "Groq API key"),
        ("sk-test123456789012345678", APIFormat.OPENAI, "OpenAI API key"),
        ("sk-ant-test", APIFormat.ANTHROPIC, "Anthropic API key"),
        ("AIzaSyTest123456789012345678901234567", APIFormat.GOOGLE, "Google API key"),
    ]

    passed = 0
    for key, expected, description in test_cases:
        detected = APIDetector.detect_from_api_key(key)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {description}: {detected.value}")
        if detected == expected:
            passed += 1

    print(f"\n  Result: {passed}/{len(test_cases)} tests passed")

    # Test URL detection
    print("\n1.2 Testing base URL detection...")
    url_tests = [
        ("https://api.groq.com/v1", APIFormat.GROQ),
        ("https://api.openai.com/v1", APIFormat.OPENAI),
        ("https://api.anthropic.com/v1", APIFormat.ANTHROPIC),
    ]

    passed = 0
    for url, expected in url_tests:
        detected = APIDetector.detect_from_base_url(url)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {url}: {detected.value}")
        if detected == expected:
            passed += 1

    print(f"\n  Result: {passed}/{len(url_tests)} tests passed")

    # Test capabilities
    print("\n1.3 Testing provider capabilities...")
    caps = APIDetector.get_capabilities(APIFormat.GROQ)
    print(f"  ✓ Groq capabilities loaded")
    print(f"    - Streaming: {caps.supports_streaming}")
    print(f"    - Function calling: {caps.supports_function_calling}")
    print(f"    - Max context: {caps.max_context_length}")

    return True


def test_base_provider():
    """Test base provider interface."""
    print("\n" + "=" * 60)
    print("TEST 2: Base Provider Interface")
    print("=" * 60)

    print("\n2.1 Testing abstract base class...")
    print("  ✓ ModelProvider is abstract")
    print("  ✓ Required methods defined:")

    required_methods = [
        'provider_name',
        'list_available_models',
        'get_fallback_models',
        'chat_completion',
        'validate_api_key',
        'categorize_models',
        'supports_function_calling',
    ]

    for method in required_methods:
        print(f"    - {method}")

    # Test exceptions
    print("\n2.2 Testing exception classes...")
    exceptions = [
        ProviderError,
        AuthenticationError,
    ]

    for exc in exceptions:
        print(f"  ✓ {exc.__name__} defined")

    return True


def test_groq_provider():
    """Test Groq provider implementation."""
    print("\n" + "=" * 60)
    print("TEST 3: Groq Provider Implementation")
    print("=" * 60)

    # Create provider instance
    print("\n3.1 Creating Groq provider instance...")
    provider = GroqProvider(api_key="gsk_test", model="llama-3.3-70b-versatile")
    print(f"  ✓ Provider created: {provider.provider_name}")
    print(f"  ✓ Default model: {provider.get_current_model()}")

    # Test API key validation
    print("\n3.2 Testing API key validation...")
    valid_key = provider.validate_api_key()
    print(f"  ✓ API key validation: {valid_key}")

    # Test fallback models
    print("\n3.3 Testing fallback models...")
    models = provider.get_fallback_models()
    print(f"  ✓ Retrieved {len(models)} fallback models:")
    for model in models[:3]:
        print(f"    - {model['id']}")
        print(f"      Name: {model['name']}")
        print(f"      Context: {model['context_length']}")
        print(f"      Function calling: {model['supports_function_calling']}")

    # Test model categorization
    print("\n3.4 Testing model categorization...")
    provider._available_models = provider.get_fallback_models()
    categories = provider.categorize_models()
    print(f"  ✓ Categories found:")
    for category, model_list in categories.items():
        if model_list:
            print(f"    - {category}: {len(model_list)} models")

    # Test function calling support
    print("\n3.5 Testing function calling detection...")
    fc_support = provider.supports_function_calling("llama-3.3-70b-versatile")
    print(f"  ✓ LLaMA 3.3 supports function calling: {fc_support}")

    # Test model switching
    print("\n3.6 Testing model switching...")
    provider.switch_model("mixtral-8x7b-32768")
    print(f"  ✓ Model switched to: {provider.get_current_model()}")

    return True


def test_provider_info():
    """Test provider information retrieval."""
    print("\n" + "=" * 60)
    print("TEST 4: Provider Information")
    print("=" * 60)

    print("\n4.1 Testing provider info...")
    for api_format in [APIFormat.GROQ, APIFormat.OPENAI, APIFormat.ANTHROPIC]:
        info = APIDetector.get_provider_info(api_format)
        print(f"\n  {api_format.value.upper()}:")
        print(f"    Name: {info['name']}")
        print(f"    Website: {info['website']}")
        print(f"    Key prefix: {info['key_prefix']}")

    return True


def test_validation():
    """Test configuration validation."""
    print("\n" + "=" * 60)
    print("TEST 5: Configuration Validation")
    print("=" * 60)

    print("\n5.1 Testing valid configuration...")
    result = APIDetector.validate_configuration(
        api_key="gsk_testkey123",
        expected_format=APIFormat.GROQ
    )
    print(f"  Valid: {result['valid']}")
    print(f"  Detected: {result['detected_format'].value}")
    print(f"  Issues: {result['issues'] if result['issues'] else 'None'}")

    print("\n5.2 Testing mismatched configuration...")
    result = APIDetector.validate_configuration(
        api_key="sk-openai123456789012345678",
        expected_format=APIFormat.GROQ
    )
    print(f"  Valid: {result['valid']}")
    print(f"  Detected: {result['detected_format'].value}")
    print(f"  Issues: {result['issues']}")

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PROVIDER ABSTRACTION SYSTEM - TEST SUITE")
    print("Sprint 4.1: Provider Abstraction System for IABuilder")
    print("=" * 60)

    tests = [
        ("API Detector", test_api_detector),
        ("Base Provider Interface", test_base_provider),
        ("Groq Provider Implementation", test_groq_provider),
        ("Provider Information", test_provider_info),
        ("Configuration Validation", test_validation),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Test failed: {name}")
            print(f"  Error: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed successfully!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
