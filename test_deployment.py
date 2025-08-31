#!/usr/bin/env python3
"""
Test script for Pipecat deployment
Tests both single-process and multi-process configurations
"""

import subprocess
import time
import requests
import sys

def test_single_process():
    """Test single process mode"""
    print("🧪 Testing Single Process Mode...")

    # Start bot in background
    process = subprocess.Popen(
        [sys.executable, "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for startup
    time.sleep(5)

    try:
        # Test health endpoint
        response = requests.get("http://localhost:7860/health", timeout=5)
        if response.status_code == 404:  # bot.py doesn't have health endpoint
            print("✅ Single process: Bot started (no health endpoint)")
        else:
            print(f"✅ Single process: Health check passed ({response.status_code})")

        # Test client endpoint
        response = requests.get("http://localhost:7860/client", timeout=5)
        if response.status_code == 200:
            print("✅ Single process: Client interface accessible")
        else:
            print(f"❌ Single process: Client interface failed ({response.status_code})")

    except requests.exceptions.RequestException as e:
        print(f"❌ Single process: Connection failed - {e}")
    finally:
        process.terminate()
        process.wait()

def test_multi_process():
    """Test multi-process mode"""
    print("\n🧪 Testing Multi-Process Mode...")

    # Start production server
    process = subprocess.Popen(
        ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker",
         "production:app", "--bind", "0.0.0.0:7860", "--log-level", "info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for startup
    time.sleep(8)

    try:
        # Test health endpoint
        response = requests.get("http://localhost:7860/health", timeout=5)
        if response.status_code == 200:
            print("✅ Multi-process: Health check passed")
        else:
            print(f"❌ Multi-process: Health check failed ({response.status_code})")

        # Test client endpoint
        response = requests.get("http://localhost:7860/client", timeout=5)
        if response.status_code == 200:
            print("✅ Multi-process: Client interface accessible")
        else:
            print(f"❌ Multi-process: Client interface failed ({response.status_code})")

        # Test API endpoint
        response = requests.post(
            "http://localhost:7860/api/offer",
            json={"type": "offer", "sdp": "test"},
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Multi-process: WebRTC API working")
        else:
            print(f"❌ Multi-process: WebRTC API failed ({response.status_code})")

    except requests.exceptions.RequestException as e:
        print(f"❌ Multi-process: Connection failed - {e}")
    finally:
        process.terminate()
        process.wait()

def main():
    """Run all tests"""
    print("🚀 Pipecat Deployment Test Suite")
    print("=" * 40)

    # Check if required packages are installed
    try:
        import gunicorn
        import uvicorn
        print("✅ Production dependencies available")
    except ImportError as e:
        print(f"⚠️  Missing production dependencies: {e}")
        print("Install with: uv add gunicorn uvicorn[standard]")
        return

    # Run tests
    test_single_process()
    test_multi_process()

    print("\n" + "=" * 40)
    print("🎯 Test complete! Check results above.")
    print("\n📋 Next steps:")
    print("1. Fix any failed tests")
    print("2. Deploy to Sevalla using sevalla.yml")
    print("3. Set API keys in Sevalla secrets")
    print("4. Monitor performance and scale as needed")

if __name__ == "__main__":
    main()
