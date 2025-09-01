#!/usr/bin/env python3
"""
Production ASGI app for Pipecat Bot with multiple processes support.
This creates a proper ASGI application for Gunicorn/Uvicorn.
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

# Import our bot functions
from bot import run_bot, bot as bot_function
from pipecat.runner.utils import create_transport
from pipecat.runner.types import RunnerArguments

# Setup FastAPI app
app = FastAPI(title="Pipecat Bot Production", version="1.0.0")

# Setup templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main interface - redirect to client."""
    return RedirectResponse(url="/client")

@app.get("/client", response_class=HTMLResponse)
async def client(request: Request):
    """Serve WebRTC client interface."""
    return templates.TemplateResponse("webrtc_client.html", {"request": request})

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "mode": "production"}

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

def main():
    """Main entry point for the application."""
    import uvicorn
    uvicorn.run(
        "production:app",
        host="0.0.0.0",
        port=7860,
        workers=2,
        log_level="info"
    )

if __name__ == "__main__":
    main()
