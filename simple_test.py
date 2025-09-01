#!/usr/bin/env python3
"""
Ultra-minimal FastAPI app for testing Sevalla deployment.
"""

import os
from fastapi import FastAPI

# Create the simplest possible FastAPI app
app = FastAPI()

print("🚀 Ultra-simple FastAPI app started")
print(f"🌍 Environment variables:")
print(f"   PORT: {os.getenv('PORT', 'not set')}")
print(f"   HOST: {os.getenv('HOST', 'not set')}")
print(f"   BIND: {os.getenv('BIND', 'not set')}")
print(f"   PYTHONPATH: {os.getenv('PYTHONPATH', 'not set')}")
print(f"   PWD: {os.getenv('PWD', 'not set')}")
print(f"   USER: {os.getenv('USER', 'not set')}")
print(f"   HOME: {os.getenv('HOME', 'not set')}")
print(f"   PATH: {os.getenv('PATH', 'not set')[:100]}...")

@app.get("/")
def read_root():
    print("📍 Root endpoint hit")
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    print("🏥 Health check hit")
    return "OK"

@app.get("/ping")
def ping():
    print("🏓 Ping hit")
    return {"ping": "pong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
