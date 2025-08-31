#!/usr/bin/env python3
"""
Pipecat Development Runner

A unified runner for building voice AI bots with Daily, WebRTC, and telephony transports.
This runner provides infrastructure setup, connection management, and transport abstraction.

Usage:
    python runner.py [OPTIONS]

Options:
  --host TEXT          Server host address (default: localhost)
  --port INTEGER       Server port (default: 7860)
  -t, --transport      Transport type: daily, webrtc, twilio, telnyx, plivo (default: webrtc)
  -x, --proxy TEXT     Public proxy hostname for telephony webhooks (required for telephony)
  --esp32              Enable SDP munging for ESP32 WebRTC compatibility
  -d, --direct         Connect directly to Daily room for testing
  -v, --verbose        Increase logging verbosity
"""

import asyncio
import importlib
import inspect
import os
import sys
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
    from pipecat.transports.network.fastapi_websocket import FastAPIWebSocketTransport
    TELEPHONY_AVAILABLE = True
except ImportError:
    TELEPHONY_AVAILABLE = False
    logger.warning("Telephony transport not available. Install with: pip install pipecat-ai[telephony]")


class PipecatRunner:
    """Main Pipecat development runner class."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7860,
        transport: str = "webrtc",
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
            if self.transport == "webrtc":
                return self.templates.TemplateResponse("webrtc_client.html", {"request": request})
            elif self.transport == "daily":
                return self.templates.TemplateResponse("daily_client.html", {"request": request})
            else:
                return self.templates.TemplateResponse("index.html", {"request": request})

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "transport": self.transport}

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

    def _setup_daily_routes(self):
        """Setup Daily-specific routes."""
        try:
            from daily import RoomService
            from daily.room import RoomProperties
        except ImportError:
            logger.error("Daily SDK not installed. Install with: pip install daily-python")
            return

        @self.app.post("/start")
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

                room_service = RoomService(api_key=api_key)

                if create_room:
                    room_properties_obj = RoomProperties(**room_properties)
                    room = room_service.create_room(properties=room_properties_obj)
                    room_url = room.url
                    token = room_service.get_token(room_url, "Pipecat Bot")
                else:
                    # Use existing room
                    sample_room = os.getenv("DAILY_SAMPLE_ROOM_URL")
                    if not sample_room:
                        raise HTTPException(status_code=400, detail="No room URL provided")
                    room_url = sample_room
                    token = room_service.get_token(room_url, "Pipecat Bot")

                # Spawn bot in background
                task_id = f"daily_{len(self.active_tasks)}"
                task = asyncio.create_task(
                    self._spawn_bot(
                        DailyRunnerArguments(
                            room_url=room_url,
                            token=token,
                            body=body,
                            handle_sigint=False,
                        ),
                        task_id
                    )
                )
                self.active_tasks[task_id] = task

                return {
                    "dailyRoom": room_url,
                    "dailyToken": token,
                }

            except Exception as e:
                logger.error(f"Error starting Daily session: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _setup_telephony_routes(self):
        """Setup telephony-specific routes."""
        @self.app.post(f"/{self.transport}/webhook")
        async def telephony_webhook(request: Request):
            """Handle telephony webhooks."""
            # This would handle incoming calls from telephony providers
            # Implementation depends on specific provider
            data = await request.json()
            logger.info(f"Received {self.transport} webhook: {data}")
            return {"status": "ok"}





    async def _spawn_bot(self, runner_args: RunnerArguments, task_id: str):
        """Spawn a new bot instance."""
        try:
            logger.info(f"Spawning bot instance: {task_id}")

            # Import the bot function from bot.py
            spec = importlib.util.spec_from_file_location("bot_module", "bot.py")
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)

            # Get the bot function
            bot_func = getattr(bot_module, "bot", None)
            if not bot_func:
                logger.error("No 'bot' function found in bot.py")
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
@click.option("--host", default="localhost", help="Server host address")
@click.option("--port", default=7860, type=int, help="Server port")
@click.option("-t", "--transport", default="webrtc",
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
