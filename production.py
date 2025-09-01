#!/usr/bin/env python3
"""
Minimal Production ASGI app for testing deployment.
"""

import os
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Setup FastAPI app
app = FastAPI(title="Pipecat Bot Production", version="1.0.0")

print("🚀 FastAPI app initialized in production mode")

# Add middleware to log all requests
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"🌐 {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
        response = await call_next(request)
        print(f"📤 Response: {response.status_code}")
        return response

app.add_middleware(RequestLoggingMiddleware)

# Add startup event
@app.on_event("startup")
async def startup_event():
    print("🔥 Application startup event triggered")

# Add shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Application shutdown event triggered")

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
    return "OK"

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

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def catch_all(path: str, request: Request):
    """Catch-all route to handle any unmatched requests."""
    print(f"🎯 Catch-all: {request.method} /{path}")
    return {"message": f"Endpoint /{path} not found", "method": request.method, "status": "ok"}

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
