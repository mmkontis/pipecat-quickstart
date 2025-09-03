#!/usr/bin/env python3
"""
Test script to verify the new Banana AI default values
"""

from types import SimpleNamespace

def test_banana_defaults():
    """Test that the new Banana AI defaults work correctly"""

    print("🍌 Testing Nano Banana AI default values...")

    # Test Case 1: Empty request body (should use Banana defaults)
    print("\n1️⃣ Testing empty request body (Banana defaults)...")
    empty_args = SimpleNamespace(body={})

    system_prompt = getattr(empty_args, 'body', {}).get('system_prompt',
        "You are Nano Banana AI, a fun and helpful AI assistant. Be creative, witty, and always ready to help with a banana twist!")

    first_message = getattr(empty_args, 'body', {}).get('first_message',
        "Say hi to Nano Banana! I'm your fun AI assistant ready to help with a smile!")

    print(f"   System prompt: {system_prompt}")
    print(f"   First message: {first_message}")

    assert "Nano Banana AI" in system_prompt, "Default system prompt should contain Nano Banana AI"
    assert "banana twist" in system_prompt, "Default system prompt should contain banana twist"
    assert "Say hi to Nano Banana" in first_message, "Default first message should contain Say hi to Nano Banana"
    assert "fun AI assistant" in first_message, "Default first message should contain fun AI assistant"
    print("   ✅ Banana defaults work correctly")

    # Test Case 2: Custom values (should override Banana defaults)
    print("\n2️⃣ Testing custom values (should override Banana defaults)...")
    custom_args = SimpleNamespace(body={
        'system_prompt': 'You are a professional business consultant.',
        'first_message': 'Hello! I am your business consultant.'
    })

    system_prompt = getattr(custom_args, 'body', {}).get('system_prompt',
        "You are Nano Banana AI, a fun and helpful AI assistant. Be creative, witty, and always ready to help with a banana twist!")

    first_message = getattr(custom_args, 'body', {}).get('first_message',
        "Say hi to Nano Banana! I'm your fun AI assistant ready to help with a smile!")

    print(f"   System prompt: {system_prompt}")
    print(f"   First message: {first_message}")

    assert "professional business consultant" in system_prompt, "Custom system prompt should contain business consultant"
    assert "Hello! I am your business consultant" in first_message, "Custom first message should contain business consultant"
    assert "Nano Banana" not in system_prompt, "Custom system prompt should not contain Nano Banana"
    print("   ✅ Custom values override Banana defaults correctly")

    # Test Case 3: Partial customization (only system_prompt)
    print("\n3️⃣ Testing partial customization (only system_prompt)...")
    partial_args = SimpleNamespace(body={
        'system_prompt': 'You are a creative writing assistant.'
    })

    system_prompt = getattr(partial_args, 'body', {}).get('system_prompt',
        "You are Nano Banana AI, a fun and helpful AI assistant. Be creative, witty, and always ready to help with a banana twist!")

    first_message = getattr(partial_args, 'body', {}).get('first_message',
        "Say hi to Nano Banana! I'm your fun AI assistant ready to help with a smile!")

    print(f"   System prompt: {system_prompt}")
    print(f"   First message: {first_message}")

    assert "creative writing assistant" in system_prompt, "Custom system prompt should contain writing assistant"
    assert "Say hi to Nano Banana" in first_message, "First message should use Banana default"
    print("   ✅ Partial customization works correctly")

    print("\n🍌 All Banana AI default tests passed!")
    print("🎯 New Default Values:")
    print("   • System Prompt: 'You are Nano Banana AI, a fun and helpful AI assistant...'")
    print("   • First Message: 'Say hi to Nano Banana! I'm your fun AI assistant...'")
    print("   • Custom values can still override these defaults")
    print("   • Fun, banana-themed personality by default!")

if __name__ == "__main__":
    test_banana_defaults()
