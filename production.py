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

@app.post("/start")
async def start_daily_session(request: Request):
    """RTVI-compatible /start endpoint for Daily transport."""
    try:
        data = await request.json()
        create_room = data.get("createDailyRoom", True)
        room_properties = data.get("dailyRoomProperties", {})
        body = data.get("body", {})

        api_key = os.getenv("DAILY_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="DAILY_API_KEY not set")

        if create_room:
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
                raise HTTPException(status_code=500, detail=f"Failed to create room: {room_response.text}")

            room_data = room_response.json()
            room_url = room_data["url"]

            # Create token for the room
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
                raise HTTPException(status_code=500, detail=f"Failed to create token: {token_response.text}")

            token = token_response.json()["token"]
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
        asyncio.create_task(spawn_bot_async(DailyRunnerArguments(
            room_url=room_url,
            token=token,
            body=body,
        )))

        # Create clickable room link with token
        clickable_room_link = f"{room_url}?t={token}"

        return {
            "clickable_room_link": clickable_room_link
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def spawn_bot_async(runner_args: RunnerArguments):
    """Spawn a bot instance asynchronously."""
    try:
        # Import the bot function from bot.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("bot_module", "bot.py")
        if spec is None:
            print("Could not find bot.py file")
            return
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)

        # Get the bot function
        bot_func = getattr(bot_module, "bot", None)
        if not bot_func:
            print("No 'bot' function found in bot.py")
            return

        # Call the bot function
        await bot_func(runner_args)

    except Exception as e:
        print(f"Error in bot: {e}")

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
