#!/usr/bin/env python3
"""
Production ASGI app for Pipecat Bot with multiple processes support.
This creates a proper ASGI application for Gunicorn/Uvicorn.
"""

import os
import asyncio
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

# Import our bot functions
from bot import run_bot, bot as bot_function
from pipecat.runner.utils import create_transport
from pipecat.runner.types import RunnerArguments, DailyRunnerArguments

# Setup FastAPI app
app = FastAPI(title="Pipecat Bot Production", version="1.0.0")

print("🚀 FastAPI app initialized in production mode")

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
    print("🏥 Health check requested")
    return {"status": "healthy", "mode": "production", "timestamp": "2025-09-01"}

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
    """RTVI-compatible /start endpoint for Daily transport."""
    try:
        print("📞 Received /start request")
        data = await request.json()
        print(f"📝 Request data: {data}")

        create_room = data.get("createDailyRoom", True)
        room_properties = data.get("dailyRoomProperties", {})
        body = data.get("body", {})

        api_key = os.getenv("DAILY_API_KEY")
        if not api_key:
            print("❌ DAILY_API_KEY not set")
            raise HTTPException(status_code=500, detail="DAILY_API_KEY not set")

        print("✅ API key found, proceeding with room creation")

        if create_room:
            print("🏗️ Creating Daily room...")
            # Create room via Daily REST API
            room_response = requests.post(
                "https://api.daily.co/v1/rooms",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "enable_chat": room_properties.get("enable_chat", True),
                        "enable_screenshare": room_properties.get("enable_screenshare", False)
                    }
                }
            )

            if room_response.status_code != 200:
                print(f"❌ Failed to create room: {room_response.status_code} - {room_response.text}")
                raise HTTPException(status_code=500, detail=f"Failed to create room: {room_response.text}")

            room_data = room_response.json()
            room_url = room_data["url"]
            print(f"✅ Room created: {room_url}")

            # Create token for the room
            print("🎫 Creating meeting token...")
            token_response = requests.post(
                "https://api.daily.co/v1/meeting-tokens",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "room_name": room_data["name"],
                        "user_name": "Pipecat Bot"
                    }
                }
            )

            if token_response.status_code != 200:
                print(f"❌ Failed to create token: {token_response.status_code} - {token_response.text}")
                raise HTTPException(status_code=500, detail=f"Failed to create token: {token_response.text}")

            token = token_response.json()["token"]
            print("✅ Token created successfully")
        else:
            # Use existing room
            sample_room = os.getenv("DAILY_SAMPLE_ROOM_URL")
            if not sample_room:
                raise HTTPException(status_code=400, detail="No room URL provided")
            room_url = sample_room

            # Extract room name from URL
            room_name = room_url.split("/")[-1]

            # Create token for existing room
            token_response = requests.post(
                "https://api.daily.co/v1/meeting-tokens",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "room_name": room_name,
                        "user_name": "Pipecat Bot"
                    }
                }
            )

            if token_response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to create token: {token_response.text}")

            token = token_response.json()["token"]

        # Spawn bot in background (simplified for production)
        print("🤖 Spawning bot in background...")
        asyncio.create_task(spawn_bot_async(DailyRunnerArguments(
            room_url=room_url,
            token=token,
            body=body,
        )))

        # Create clickable room link with token
        clickable_room_link = f"{room_url}?t={token}"
        print(f"🎉 Bot session ready! Room link: {clickable_room_link}")

        return {
            "clickable_room_link": clickable_room_link
        }

    except Exception as e:
        print(f"💥 Error in start_daily_session: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

async def spawn_bot_async(runner_args: RunnerArguments):
    """Spawn a bot instance asynchronously."""
    try:
        print(f"🚀 Starting bot with args: room_url={runner_args.room_url[:50]}...")
        # Use the pre-imported bot function to avoid dynamic imports in production
        await bot_function(runner_args)
        print("✅ Bot completed successfully")
    except Exception as e:
        print(f"❌ Error in bot: {e}")
        import traceback
        print(f"📋 Bot traceback: {traceback.format_exc()}")
        # Don't re-raise the exception to avoid crashing the web server

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
