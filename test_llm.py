"""LLM connectivity test script"""

import os
import sys

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from minerbot.models.llm import get_model


def test_model(model_name: str, test_message: str = "Say 'Hello' in one word.") -> bool:
    """Test a single model for connectivity.
    
    Args:
        model_name: Model identifier
        test_message: Message to send to the model
        
    Returns:
        True if test passed, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Create model
        print("1. Creating model...")
        model = get_model(model_name)
        print(f"   ✓ Model created: {type(model).__name__}")
        print(f"   ✓ Model: {model.model}")
        if hasattr(model, 'api_base') and model.api_base:
            print(f"   ✓ API Base: {model.api_base}")
        
        # Send test message
        print(f"\n2. Sending test message: '{test_message}'")
        from langchain_core.messages import HumanMessage
        response = model.invoke([HumanMessage(content=test_message)])
        
        # Print response
        print(f"\n3. Response received!")
        print(f"   ✓ Response: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"\n   ✗ Error: {type(e).__name__}: {e}")
        return False


def main():
    """Run connectivity tests for all configured models."""
    print("=" * 60)
    print("LLM Connectivity Test")
    print("=" * 60)
    
    # Check environment variables
    print("\n[Environment Check]")
    api_keys = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "MINIMAX_API_KEY": os.getenv("MINIMAX_API_KEY"),
        "AZURE_API_KEY": os.getenv("AZURE_API_KEY"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    }
    
    for key, value in api_keys.items():
        if value:
            # Show masked value
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"  ✓ {key}: {masked}")
        else:
            print(f"    {key}: not set")
    
    # Test models
    models_to_test = [
        "MiniMax-M2.5",
    ]
    
    results = {}
    for model_name in models_to_test:
        results[model_name] = test_model(model_name)
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for model_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {model_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
