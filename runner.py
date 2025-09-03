#!/usr/bin/env python3
"""
Pipecat Development Runner

A unified runner for building voice AI bots with Daily as the primary transport.
Also supports WebRTC and telephony transports for advanced use cases.
This runner provides infrastructure setup, connection management, and transport abstraction.

Usage:
    python runner.py [OPTIONS]

Options:
  --host TEXT          Server host address (default: localhost)
  --port INTEGER       Server port (default: 8080)
  -t, --transport      Transport type: daily, webrtc, twilio, telnyx, plivo (default: daily)
  -x, --proxy TEXT     Public proxy hostname for telephony webhooks (required for telephony)
  --esp32              Enable SDP munging for ESP32 WebRTC compatibility
  -d, --direct         Connect directly to Daily room for testing
  -v, --verbose        Increase logging verbosity
"""

import asyncio
import importlib
import importlib.util
import inspect
import os
import sys
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import click

from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Pipecat imports
from pipecat.runner.types import (
    DailyRunnerArguments,
    RunnerArguments,
    SmallWebRTCRunnerArguments,
    WebSocketRunnerArguments,
)

# Transport imports
try:
    from pipecat.transports.services.daily import DailyTransport
    DAILY_AVAILABLE = True
except ImportError:
    DAILY_AVAILABLE = False
    logger.warning("Daily transport not available. Install with: pip install pipecat-ai[daily]")

try:
    from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    logger.warning("WebRTC transport not available. Install with: pip install pipecat-ai[webrtc]")

try:
    from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketTransport
    TELEPHONY_AVAILABLE = True
except ImportError:
    TELEPHONY_AVAILABLE = False
    logger.warning("Telephony transport not available. Install with: pip install pipecat-ai[telephony]")


class PipecatRunner:
    """Main Pipecat development runner class."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        transport: str = "daily",
        proxy: Optional[str] = None,
        esp32: bool = False,
        direct: bool = False,
        verbose: bool = False,
    ):
        self.host = host
        self.port = port
        self.transport = transport
        self.proxy = proxy
        self.esp32 = esp32
        self.direct = direct
        self.verbose = verbose

        # Setup logging
        if verbose:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG")
        else:
            logger.remove()
            logger.add(sys.stderr, level="INFO")

        # Initialize FastAPI app
        self.app = FastAPI(title="Pipecat Development Runner", version="1.0.0")

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )

        # Setup templates and static files
        self.templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

        # Store active bot tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}

        # Setup routes
        self._setup_routes()

        logger.info(f"🚀 Pipecat Runner initialized with transport: {transport}")

    def _setup_routes(self):
        """Setup FastAPI routes based on transport type."""

        @self.app.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            """Serve the main interface."""
            if self.transport == "daily":
                return self.templates.TemplateResponse("index.html", {"request": request})
            elif self.transport == "webrtc":
                return self.templates.TemplateResponse("webrtc_client.html", {"request": request})
            else:
                return self.templates.TemplateResponse("index.html", {"request": request})

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return JSONResponse(content={"status": "healthy", "transport": self.transport})

        @self.app.get("/capabilities")
        async def capabilities():
            """API capabilities and documentation endpoint."""
            return JSONResponse(content={
                "llm": {
                    "default_model": "gpt-4o-mini",
                    "available_models": [
                        "gpt-5",
                        "gpt-5-mini", 
                        "gpt-5-nano",
                        "gpt-4o-mini",
                        "claude-3-5-haiku-latest",
                        "claude-sonnet-4-20250514"
                    ]
                },
                "tts": {
                    "default_provider": "cartesia",
                    "providers": ["openai", "cartesia", "google", "elevenlabs"]
                },
                "avatar": {
                    "provider": "heygen",
                    "usage": "Include 'heygen_avatar_id' in request body to enable HeyGen avatar",
                    "example": "curl -X POST /start -d '{\"heygen_avatar_id\":\"Katya_Chair_Sitting_public\"}'"
                },
                "customization": {
                    "system_prompt": {
                        "description": "Customize the AI assistant's system prompt",
                        "example": "curl -X POST /start -d '{\"system_prompt\":\"You are a helpful assistant...\"}'"
                    },
                    "bot_name": {
                        "description": "Customize the AI assistant's name",
                        "example": "curl -X POST /start -d '{\"bot_name\":\"Zoe Fragkou\"}'"
                    },
                    "user_name": {
                        "description": "Specify the user's name for personalized conversation",
                        "example": "curl -X POST /start -d '{\"user_name\":\"John\"}'"
                    }
                }
            })

        # WebRTC routes
        if self.transport == "webrtc":
            self._setup_webrtc_routes()

        # Daily routes
        if self.transport == "daily":
            self._setup_daily_routes()

        # Telephony routes
        if self.transport in ["twilio", "telnyx", "plivo"]:
            self._setup_telephony_routes()

    def _setup_webrtc_routes(self):
        """Setup WebRTC-specific routes."""
        @self.app.get("/client", response_class=HTMLResponse)
        async def webrtc_client(request: Request):
            """Serve WebRTC client interface."""
            return self.templates.TemplateResponse("webrtc_client.html", {"request": request})

        @self.app.post("/start")
        async def start_webrtc_session(request: Request):
            """RTVI-compatible /start endpoint for WebRTC transport."""
            try:
                data = await request.json()
                body = data.get("body", {})
                tts = data.get("tts", {})
                
                # Extract heygen_avatar_id from root level if present
                heygen_avatar_id = data.get("heygen_avatar_id") or body.get("heygen_avatar_id")
                print(f"DEBUG: WebRTC heygen_avatar_id = {heygen_avatar_id}, data keys = {list(data.keys())}")

                bot_name = body.get("bot_name") or data.get("bot_name", "Nano Banana AI")
                user_name = body.get("user_name") or data.get("user_name", "friend")
                system_prompt = body.get("system_prompt") or data.get("system_prompt")
                language = body.get("language") or data.get("language")

                # Spawn bot in background for WebRTC
                task_id = f"webrtc_{len(self.active_tasks)}"
                
                # Create a simple class that inherits from RunnerArguments
                class WebRTCArgs(RunnerArguments):
                    def __init__(self):
                        super().__init__()
                        self.body = {
                            "body": body,
                            "tts": tts,
                            "heygen_avatar_id": heygen_avatar_id,
                            "bot_name": bot_name,
                            "user_name": user_name,
                            "system_prompt": system_prompt,
                            "language": language
                        } if heygen_avatar_id else {
                            "body": body,
                            "tts": tts,
                            "bot_name": bot_name,
                            "user_name": user_name,
                            "system_prompt": system_prompt,
                            "language": language
                        }
                        self.handle_sigint = False
                
                webrtc_args = WebRTCArgs()
                
                task = asyncio.create_task(
                    self._spawn_bot(webrtc_args, task_id)
                )
                self.active_tasks[task_id] = task

                # Build simple response for WebRTC
                response = {
                    "status": "started",
                    "transport": "webrtc",
                    "bot_name": bot_name,
                    "user_name": user_name,
                    "avatar_enabled": bool(heygen_avatar_id),
                    "session_id": task_id,
                    "note": "WebRTC bot started - use browser WebRTC client to connect"
                }

                return JSONResponse(content=response)

            except Exception as e:
                logger.error(f"Error starting WebRTC session: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _setup_daily_routes(self):
        """Setup Daily-specific routes."""
        # We'll use HTTP requests to Daily REST API instead of SDK
        import requests

        async def _start_daily_session_logic(request: Request):
            """RTVI-compatible /start endpoint for Daily transport."""
            try:
                data = await request.json()
                create_room = data.get("createDailyRoom", True)
                room_properties = data.get("dailyRoomProperties", {})
                body = data.get("body", {})
                tts = data.get("tts", {})

                # Extract heygen_avatar_id from root level if present
                heygen_avatar_id = data.get("heygen_avatar_id") or body.get("heygen_avatar_id")
                print(f"DEBUG: heygen_avatar_id = {heygen_avatar_id}, data keys = {list(data.keys())}")

                bot_name = body.get("bot_name") or data.get("bot_name", "Nano Banana AI")
                user_name = body.get("user_name") or data.get("user_name", "friend")
                system_prompt = body.get("system_prompt") or data.get("system_prompt")
                language = body.get("language") or data.get("language")
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
                                "enable_screenshare": room_properties.get("enable_screenshare", False),
                                "enable_recording": room_properties.get("enable_recording", os.getenv("DAILY_ENABLE_RECORDING", "cloud"))
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
                                "user_name": user_name,
                                "start_cloud_recording": room_properties.get("start_cloud_recording", os.getenv("DAILY_START_CLOUD_RECORDING", "false").lower() == "true")
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
                                "user_name": user_name,
                                "start_cloud_recording": room_properties.get("start_cloud_recording", os.getenv("DAILY_START_CLOUD_RECORDING", "false").lower() == "true")
                            }
                        }
                    )

                    if token_response.status_code != 200:
                        raise HTTPException(status_code=500, detail=f"Failed to create token: {token_response.text}")

                    token = token_response.json()["token"]

                # Spawn bot in background
                task_id = f"daily_{len(self.active_tasks)}"
                # Create separate token for bot with bot's name
                bot_token_response = requests.post(
                    "https://api.daily.co/v1/meeting-tokens",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "properties": {
                            "room_name": room_data["name"] if create_room else room_name,
                            "user_name": bot_name,
                            "start_cloud_recording": False
                        }
                    }
                )

                if bot_token_response.status_code == 200:
                    bot_token = bot_token_response.json()["token"]
                    bot_room_url = f"{room_url}?t={bot_token}"
                else:
                    # Fallback to URL parameter approach
                    bot_room_url = f"{room_url}?name=Zoe Fragkou"

                task = asyncio.create_task(
                    self._spawn_bot(
                        DailyRunnerArguments(
                            room_url=bot_room_url,
                            token=bot_token if 'bot_token' in locals() else token,
                            body={
                                "body": body,
                                "tts": tts,
                                "heygen_avatar_id": heygen_avatar_id,
                                "bot_name": bot_name,
                                "user_name": user_name,
                                "system_prompt": system_prompt,
                                "language": language
                            } if heygen_avatar_id else {
                                "body": body,
                                "tts": tts,
                                "bot_name": bot_name,
                                "user_name": user_name,
                                "system_prompt": system_prompt,
                                "language": language
                            },
                        ),
                        task_id
                    )
                )
                self.active_tasks[task_id] = task

                # Create clickable room link with token
                clickable_room_link = f"{room_url}?t={token}"

                # Check for heygen avatar configuration
                # HeyGen is only enabled when explicitly requested via heygen_avatar_id
                heygen_enabled = False

                # Build clean response with essential information only
                response = {
                    "status": "started",
                    "room_url": clickable_room_link,
                    "bot_name": bot_name,
                    "user_name": user_name,
                    "avatar_enabled": bool(heygen_avatar_id),
                    "session_id": task_id
                }

                return JSONResponse(content=response)

            except Exception as e:
                logger.error(f"Error starting Daily session: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/start")
        async def start_daily_session(request: Request):
            """RTVI-compatible /start endpoint for Daily transport."""
            return await _start_daily_session_logic(request)

    def _setup_telephony_routes(self):
        """Setup telephony-specific routes."""
        @self.app.post(f"/{self.transport}/webhook")
        async def telephony_webhook(request: Request):
            """Handle telephony webhooks."""
            # This would handle incoming calls from telephony providers
            # Implementation depends on specific provider
            data = await request.json()
            logger.info(f"Received {self.transport} webhook: {data}")
            return JSONResponse(content={"status": "ok"})





    async def _spawn_bot(self, runner_args: RunnerArguments, task_id: str):
        """Spawn a new bot instance."""
        try:
            logger.info(f"Spawning bot instance: {task_id}")

            # Determine which bot file to use based on heygen_avatar_id
            body_data = getattr(runner_args, 'body', {})
            heygen_avatar_id = (
                body_data.get('heygen_avatar_id', '') or
                body_data.get('body', {}).get('heygen_avatar_id', '')
            )
            
            # Check if any heygen-related parameter is provided or if user requests video bot
            use_video_bot = bool(heygen_avatar_id and heygen_avatar_id.strip())
            
            if use_video_bot:
                bot_file = "videobot.py"
                logger.info(f"Using video bot with HeyGen avatar: {heygen_avatar_id}")
            else:
                bot_file = "bot.py"
                logger.info("Using voice-only bot")
            
            # Import the bot function from the appropriate file
            spec = importlib.util.spec_from_file_location("bot_module", bot_file)
            if spec is None:
                logger.error(f"Could not find {bot_file} file")
                return
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)

            # Get the bot function
            bot_func = getattr(bot_module, "bot", None)
            if not bot_func:
                logger.error(f"No 'bot' function found in {bot_file}")
                return

            # Call the bot function
            await bot_func(runner_args)

        except Exception as e:
            logger.error(f"Error in bot {task_id}: {e}")
        finally:
            # Cleanup
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            logger.info(f"Bot instance {task_id} finished")

    def run(self):
        """Run the development runner."""
        # Debug environment variables for Sevalla
        import os
        sevalla_port = os.getenv('PORT')
        if sevalla_port:
            self.port = int(sevalla_port)
            logger.info(f"🔧 Using Sevalla PORT environment variable: {self.port}")
        
        logger.info(f"🔍 Environment debug - PORT: {os.getenv('PORT', 'not set')}")
        logger.info(f"🔍 Environment debug - HOST: {os.getenv('HOST', 'not set')}")
        logger.info(f"🔍 Runner config - host: {self.host}, port: {self.port}")
        logger.info(f"Starting Pipecat Runner on {self.host}:{self.port}")

        # Check transport availability
        if self.transport == "daily" and not DAILY_AVAILABLE:
            logger.error("Daily transport not available")
            return
        if self.transport == "webrtc" and not WEBRTC_AVAILABLE:
            logger.error("WebRTC transport not available")
            return
        if self.transport in ["twilio", "telnyx", "plivo"] and not TELEPHONY_AVAILABLE:
            logger.error("Telephony transport not available")
            return

        # Check required environment variables
        self._check_environment_variables()

        # Run the server
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info" if not self.verbose else "debug",
        )

    def _check_environment_variables(self):
        """Check for required environment variables based on transport."""
        required_vars = []

        if self.transport == "daily":
            required_vars.extend(["DAILY_API_KEY"])

        elif self.transport == "twilio":
            required_vars.extend(["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"])

        elif self.transport == "telnyx":
            required_vars.extend(["TELNYX_API_KEY"])

        elif self.transport == "plivo":
            required_vars.extend(["PLIVO_AUTH_ID", "PLIVO_AUTH_TOKEN"])

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")


@click.command()
@click.option("--host", default="0.0.0.0", help="Server host address")
@click.option("--port", default=8080, type=int, help="Server port")
@click.option("-t", "--transport", default="daily",
              type=click.Choice(["webrtc", "daily", "twilio", "telnyx", "plivo"]),
              help="Transport type")
@click.option("-x", "--proxy", help="Public proxy hostname for telephony webhooks")
@click.option("--esp32", is_flag=True, help="Enable SDP munging for ESP32 WebRTC compatibility")
@click.option("-d", "--direct", is_flag=True, help="Connect directly to Daily room for testing")
@click.option("-v", "--verbose", is_flag=True, help="Increase logging verbosity")
def main(host, port, transport, proxy, esp32, direct, verbose):
    """Main entry point for the Pipecat development runner."""
    runner = PipecatRunner(
        host=host,
        port=port,
        transport=transport,
        proxy=proxy,
        esp32=esp32,
        direct=direct,
        verbose=verbose,
    )
    runner.run()


if __name__ == "__main__":
    main()
