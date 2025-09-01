#!/usr/bin/env python3
"""
Minimal Production ASGI app for testing deployment.
"""

import os
from fastapi import FastAPI
from fastapi import Request

# Setup FastAPI app
app = FastAPI(title="Pipecat Bot Production", version="1.0.0")

print("🚀 FastAPI app initialized in production mode")

# Templates setup removed for minimal deployment

@app.get("/")
async def root():
    """Simple root endpoint."""
    print("🏠 Root endpoint accessed")
    return {"message": "Pipecat Bot API", "status": "running"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    print("🏥 Health check requested")
    return {"status": "healthy", "mode": "production", "timestamp": "2025-09-01", "bot_imports": BOT_IMPORTS_SUCCESSFUL}

@app.get("/ping")
async def ping():
    """Simple ping endpoint to test basic connectivity."""
    print("🏓 Ping received")
    return {"pong": True, "timestamp": "2025-09-01"}

@app.post("/api/offer")
async def handle_offer(request: Request):
    """Handle WebRTC offer and start bot conversation."""
    try:
        data = await request.json()
        # Here you would handle the WebRTC signaling
        # For now, return a mock response
        return {
            "type": "answer",
            "sdp": "v=0\r\no=- production 1 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0",
            "pc_id": "production_bot"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/start")
async def start_daily_session(request: Request):
    """Simplified /start endpoint for testing."""
    print("📞 Received /start request - simplified version")
    try:
        data = await request.json()
        print(f"📝 Request data: {data}")

        # For now, just return a mock response
        return {
            "message": "Start endpoint working",
            "received_data": data,
            "mock_room_link": "https://example.daily.co/mock-room"
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}

def main():
    """Main entry point for the application."""
    import uvicorn
    uvicorn.run(
        "production:app",
        host="0.0.0.0",
        port=7860,
        workers=1,
        log_level="info"
    )

if __name__ == "__main__":
    main()
