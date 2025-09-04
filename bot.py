#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat Daily Bot Example.

The example runs a simple voice AI bot using Daily transport that you can 
connect to using Daily rooms. You can also deploy this bot to Pipecat Cloud.

Required AI services:
- Deepgram (Speech-to-Text)
- OpenAI (LLM)
- Cartesia (Text-to-Speech)
- HeyGen (Video Avatar)

Required environment variables:
- DEEPGRAM_API_KEY
- OPENAI_API_KEY  
- CARTESIA_API_KEY
- HEYGEN_API_KEY
- DAILY_API_KEY (for runner)

Run the bot using::

    uv run bot.py
    
Or use the development runner::

    uv run python runner.py
"""

import os
import sys
import psutil
import gc
import requests
from datetime import datetime
from pipecat.transcriptions.language import Language

from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import LLMMessagesUpdateFrame, StartFrame
from typing import List, cast
from openai.types.chat import ChatCompletionMessageParam

# Global exception handler
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    print(f"💥 UNCAUGHT EXCEPTION: {exc_type.__name__}: {exc_value}")
    import traceback
    print(f"💥 Traceback: {''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}")

    # Try to get memory info
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        print(f"💥 Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    except:
        pass

# Install global exception handler
sys.excepthook = global_exception_handler

def log_memory_usage():
    """Log current memory usage"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        print(f"📊 Memory: {memory_info.rss / 1024 / 1024:.2f} MB, "
              f"CPU: {psutil.cpu_percent(interval=1):.1f}%")
    except Exception as e:
        print(f"⚠️ Could not get memory stats: {e}")

# Quiet HeyGen classes will be defined after imports are loaded

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds first run only)\n")

logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams

logger.info("✅ Silero VAD model loaded")
logger.info("Loading pipeline components...")
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.services.daily import DailyParams

from pipecat.processors.user_idle_processor import UserIdleProcessor
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import TextFrame


# Google TTS import (available as alternative)
# from pipecat.services.google.tts import GoogleHttpTTSService, Language

logger.info("✅ All components loaded successfully!")




# Voice-only bot - no HeyGen dependencies

load_dotenv(override=True)

async def start_daily_recording(room_url: str) -> bool:
    """Start recording via Daily REST API when first participant joins."""
    try:
        api_key = os.getenv("DAILY_API_KEY")
        if not api_key:
            print("⚠️ DAILY_API_KEY not found - skipping recording")
            return False

        # Extract room name from URL
        room_name = room_url.split("/")[-1].split("?")[0]
        print(f"🎥 Starting recording for room: {room_name}")

        # Start recording via Daily REST API
        response = requests.post(
            f"https://api.daily.co/v1/rooms/{room_name}/recordings/start",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "type": "cloud",  # Use cloud recording
                # "layout": {
                #         "preset": "portrait",
                #         "variant": "vertical"
                #     },
                # "width": 1080,
                # "height": 1920,
                # "backgroundColor": "#000000"
                
            }
        )

        if response.status_code == 200:
            recording_data = response.json()
            print(f"✅ Recording started successfully: {recording_data.get('id', 'unknown')}")
            return True
        else:
            print(f"❌ Failed to start recording: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error starting recording: {e}")
        return False


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    print("🤖 Starting bot function...")
    logger.info(f"Starting bot")
    print(f"🔍 Runner args: {runner_args}")
    print(f"🔍 Transport type: {type(transport)}")
    log_memory_usage()



    # Get API keys with error handling
    print("🔑 Checking API keys...")
    
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    if not deepgram_key:
        print("❌ DEEPGRAM_API_KEY not found!")
        raise ValueError("DEEPGRAM_API_KEY environment variable is required")
    print("✅ DEEPGRAM_API_KEY found")
    
    # Check for Cartesia API key
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        print("❌ CARTESIA_API_KEY not found!")
        raise ValueError("CARTESIA_API_KEY environment variable is required")
    print("✅ CARTESIA_API_KEY found")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY not found!")
        raise ValueError("OPENAI_API_KEY environment variable is required")
    print("✅ OPENAI_API_KEY found")
    
    print("🔑 All API keys validated!")
    print("🎵 Voice-only bot - no video avatar support")

    print("🎙️ Initializing speech services...")
    try:
        stt = DeepgramSTTService(api_key=deepgram_key, live_options=LiveOptions(
        model="nova-3-general",
        language=Language.EN,
        smart_format=True
    ) )

        
        print("✅ Deepgram STT service created")
    except Exception as e:
        print(f"❌ Failed to create Deepgram STT: {e}")
        raise

    # Use Cartesia TTS as default for lower latency
    try:
        body_data = getattr(runner_args, 'body', {})
        # Access TTS config from correct nested structure
        tts_config = body_data.get('tts', {}) or body_data.get('body', {}).get('tts', {})
        voice_id = tts_config.get('voice_id', '71a7ad14-091c-4e8e-a314-022ece01c121')
        tts = CartesiaTTSService(
            api_key=cartesia_key,
            voice_id=voice_id,  # Configurable voice ID (default: British Reading Lady)
        )
        print("✅ Cartesia TTS service created")
    except Exception as e:
        print(f"❌ Failed to create Cartesia TTS: {e}")
        raise

    # Google TTS alternative (higher quality but more latency):
    # # Check for Google credentials file
    # credentials_file = os.path.join(os.path.dirname(__file__), "GOOGLE_TEST_CREDENTIALS.json")
    # if os.path.exists(credentials_file):
    #     try:
    #         with open(credentials_file, 'r') as f:
    #             google_credentials = f.read()
    #         tts = GoogleHttpTTSService(
    #             credentials=google_credentials,
    #             voice_id="en-US-Chirp3-HD-Charon",
    #             params=GoogleHttpTTSService.InputParams(
    #                 language=Language.EN_US
    #             )
    #         )
    #         print("✅ Google TTS service created")
    #     except Exception as e:
    #         print(f"⚠️ Google TTS failed, falling back to Cartesia: {e}")
    #         tts = CartesiaTTSService(
    #             api_key=cartesia_key,
    #             voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",
    #         )

    print("🧠 Initializing LLM service...")
    try:
        # Get customizable model from runner args (default to gpt-4o-mini)
        # Access model config from correct nested structure
        inner_body = body_data.get('body', {}) or body_data  # Fallback to direct access
        model = inner_body.get('model', 'gpt-4o-mini')
        llm = OpenAILLMService(api_key=openai_key, model=model)
        print(f"✅ OpenAI LLM service created ({model})")
    except Exception as e:
        print(f"❌ Failed to create OpenAI LLM: {e}")
        raise

    print("🗨️ Setting up conversation context...")

    # Get customizable parameters from runner args
    # Access config from correct nested structure
    body_data = getattr(runner_args, 'body', {})
    config_data = body_data.get('body', {}) or body_data  # Fallback to direct access
    bot_name = config_data.get('bot_name', 'Nano Banana AI')
    user_name = config_data.get('user_name', 'friend')

    # Get customizable system prompt from runner args
    system_prompt = config_data.get('system_prompt',
        f"You are {bot_name}, a fun and helpful AI assistant. Be creative, witty, and always ready to help {user_name}!")

    messages: List[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    print(f"📝 Using system prompt: {system_prompt[:50]}...")

    try:
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)
        print("✅ Context aggregator created")
    except Exception as e:
        print(f"❌ Failed to create context aggregator: {e}")
        raise

    try:
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        print("✅ RTVI processor created")
    except Exception as e:
        print(f"❌ Failed to create RTVI processor: {e}")
        raise

    print("🔧 Building pipelines...")

    # Create a class to track consecutive idle events
    class IdleTracker:
        def __init__(self):
            self.consecutive_idle_count = 0
            self.conversation_ended = False
            self.continuous_idle_time_seconds = 0  # Changed to continuous tracking

        def reset_idle_timer(self):
            """Reset the continuous idle timer when user speaks"""
            if self.continuous_idle_time_seconds > 0:
                print(f"🎤 User spoke - resetting continuous idle timer (was {self.continuous_idle_time_seconds}s)")
            self.continuous_idle_time_seconds = 0

        async def handle_idle(self, processor):
            # Add 10 seconds to continuous idle time
            self.continuous_idle_time_seconds += 10

            # Log continuous idle time every 5 seconds
            if self.continuous_idle_time_seconds % 5 == 0:
                print(f"⏱️ Continuous idle time: {self.continuous_idle_time_seconds}s")

            # Check if continuous idle time exceeds 10 seconds
            if self.continuous_idle_time_seconds > 200:
                print("⏰ Continuous idle time exceeded 500 seconds - cancelling task")
                try:
                    cancelled = task.cancel()
                    print(f"✅ Task cancellation requested: {cancelled}")
                    return
                except Exception as e:
                    print(f"⚠️ Error cancelling task: {e}")

            # If conversation has ended, don't do normal idle processing
            if self.conversation_ended:
                print("🚫 Conversation ended - skipping normal idle processing")
                return

            self.consecutive_idle_count += 1
            print(f"🕐 Idle event #{self.consecutive_idle_count} detected (continuous idle: {self.continuous_idle_time_seconds}s)")

            if self.consecutive_idle_count <= 2:
                # First and second idle: ask if still there
                tone_variations = [
                    "with a friendly, concerned tone",
                    "with a casual, checking-in tone"
                ]
                tone = tone_variations[self.consecutive_idle_count - 1]
                messages.append({
                    "role": "system",
                    "content": f"Ask the user directly: Are you still there? Use {tone}. Keep it short and natural."
                })
                await task.queue_frames([LLMMessagesUpdateFrame(messages=cast(list, messages), run_llm=True)])
            else:
                # Third idle: say goodbye and end conversation
                print("👋 Third consecutive idle - ending conversation permanently")
                messages.append({
                    "role": "system",
                    "content": "Say a friendly goodbye to the user. Something like 'Ok, I think you might have stepped away. Talk to you later!' Keep it warm and natural."
                })
                await task.queue_frames([LLMMessagesUpdateFrame(messages=cast(list, messages), run_llm=True)])

                # Mark conversation as ended - no more idle checking
                self.conversation_ended = True

    idle_tracker = IdleTracker()

    # Create processor to detect user activity and reset idle timer
    class UserActivityDetector(FrameProcessor):
        def __init__(self, idle_tracker):
            super().__init__()
            self.idle_tracker = idle_tracker
            self.started = False

        async def process_frame(self, frame, direction):
            # Always call parent process_frame first to handle base class logic
            await super().process_frame(frame, direction)

            # Handle StartFrame to mark processor as started
            if isinstance(frame, StartFrame):
                self.started = True

            # Reset idle timer when user sends any frame (speech, text, etc.)
            if direction.name == "user":
                self.idle_tracker.reset_idle_timer()

            # Pass frame through unchanged
            await self.push_frame(frame, direction)

    activity_detector = UserActivityDetector(idle_tracker)

    # Create the processor with 10-second timeout
    user_idle = UserIdleProcessor(
        callback=idle_tracker.handle_idle,
        timeout=15.0  # 10 seconds of silence
    )
    # Create voice-only pipeline
    print("🎵 Creating voice-only pipeline...")
    main_pipeline = Pipeline([
        transport.input(),  # Transport user input
        activity_detector,  # Detect user activity and reset idle timer
        rtvi,  # RTVI processor
        stt,  # Speech-to-Text
        user_idle,                   # Add idle detection here
        context_aggregator.user(),  # User responses
        llm,  # Language Model
        tts,  # Text-to-Speech
        transport.output(),  # Transport bot output
        context_aggregator.assistant(),  # Assistant responses
    ])
    print("✅ Voice-only pipeline created")

    print("📋 Creating pipeline task...")
    try:
        task = PipelineTask(
            main_pipeline,
            params=PipelineParams(
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
            observers=[RTVIObserver(rtvi)],
        )
        print("✅ Pipeline task created")
    except Exception as e:
        print(f"❌ Failed to create pipeline task: {e}")
        raise

    print("🔗 Setting up event handlers...")
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        print(f"👋 Client connected: {client}")
        logger.info(f"Client connected")
        try:
            # Get customizable first message from runner args
            # Access config from correct nested structure
            config_data = getattr(runner_args, 'body', {})
            inner_config = config_data.get('body', {}) or config_data  # Fallback to direct access
            first_message = inner_config.get('first_message',
                f"Say hi to {user_name}! I'm {bot_name}, your fun AI assistant ready to help with a smile!")

            # Kick off the conversation.
            messages.append({"role": "system", "content": first_message})
            await task.queue_frames([LLMMessagesUpdateFrame(messages=cast(list, messages), run_llm=True)])
            print(f"✅ Initial message queued: {first_message[:50]}...")
        except Exception as e:
            print(f"❌ Error in client connected handler: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            raise

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        print(f"👋 Client disconnected: {client}")
        logger.info(f"Client disconnected")
        try:
            # Send full conversation context/transcript to webhook
            webhook_url = "https://tryhumanlike.com/api/webhook/note"
            webhook_data = {
                "client_id": str(client),
                "disconnect_time": str(datetime.now()),
                "conversation_context": messages,  # Full transcript/context
                "bot_name": bot_name,
                "user_name": user_name,
                "total_messages": len(messages),
                "idle_tracker": {
                    "consecutive_idle_count": idle_tracker.consecutive_idle_count,
                    "conversation_ended": idle_tracker.conversation_ended,
                    "continuous_idle_time_seconds": idle_tracker.continuous_idle_time_seconds
                }
            }

            try:
                response = requests.post(
                    webhook_url,
                    json=webhook_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5  # 5 second timeout
                )
                if response.status_code == 200:
                    print(f"✅ Webhook sent successfully to {webhook_url}")
                else:
                    print(f"⚠️ Webhook failed with status {response.status_code}: {response.text}")
            except Exception as webhook_error:
                print(f"⚠️ Webhook request failed: {webhook_error}")

            await task.cancel()
            print(f"✅ Task cancellation requested: {await task.cancel()}")
        except Exception as e:
            print(f"❌ Error in client disconnected handler: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            raise

    # Add more detailed transport event handlers
    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        print(f"🎉 First participant joined: {participant}")
        print("🎯 Bot should start responding now")
        log_memory_usage()

        # Auto-start recording when first participant joins
        room_url = getattr(runner_args, 'room_url', None)
        if room_url:
            print("🎥 Auto-starting recording for first participant...")
            await start_daily_recording(room_url)
        else:
            print("⚠️ No room URL available for recording")

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant):
        print(f"👋 Participant left: {participant}")
        try:
            # Send full conversation context/transcript to webhook
            webhook_url = "https://tryhumanlike.com/api/webhook/note"
            webhook_data = {
                "client_id": str(participant),
                "disconnect_time": str(datetime.now()),
                "conversation_context": messages,  # Full transcript/context
                "bot_name": bot_name,
                "user_name": user_name,
                "total_messages": len(messages),
                "idle_tracker": {
                    "consecutive_idle_count": idle_tracker.consecutive_idle_count,
                    "conversation_ended": idle_tracker.conversation_ended,
                    "continuous_idle_time_seconds": idle_tracker.continuous_idle_time_seconds
                }
            }

            try:
                response = requests.post(
                    webhook_url,
                    json=webhook_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5  # 5 second timeout
                )
                if response.status_code == 200:
                    print(f"✅ Webhook sent successfully to {webhook_url}")
                else:
                    print(f"⚠️ Webhook failed with status {response.status_code}: {response.text}")
            except Exception as webhook_error:
                print(f"⚠️ Webhook request failed: {webhook_error}")

            await task.cancel()
            print(f"✅ Task cancellation requested: {await task.cancel()}")
        except Exception as e:
            print(f"❌ Error in participant left handler: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            raise
        
    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        print(f"📞 Call state updated: {state}")

    print("🏃 Starting pipeline runner...")
    try:
        runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
        print("✅ Pipeline runner created")
        
        print("🚀 Running pipeline task...")
        await runner.run(task)
        print("✅ Pipeline task completed")
    except Exception as e:
        print(f"❌ Error running pipeline: {e}")
        import traceback
        print(f"❌ Full pipeline error traceback: {traceback.format_exc()}")
        raise
    finally:
        print("🔚 Pipeline task finished (completed or crashed)")


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""
    print("🎯 Bot entry point called")
    print(f"🔍 Runner args: {runner_args}")

    # Check if this is a direct run or API run
    is_direct_run = not hasattr(runner_args, 'room_url') or not getattr(runner_args, 'room_url', None)

    if is_direct_run:
        print("🔧 Direct run detected - using WebRTC transport for local audio")
        transport_type = "webrtc"

        # Audio device check removed to avoid linter warnings
        # (sounddevice import was causing "could not be resolved" error)
    else:
        print("🔧 API run detected - using Daily transport")
        transport_type = "daily"

    print(f"🚗 Setting up {transport_type} transport parameters...")
    print("🎥 Video output disabled - voice-only bot")
    
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=False,  # Voice-only bot - no video
            video_out_is_live=False,  # Voice-only bot - no video
            vad_analyzer=SileroVADAnalyzer(
                # params=VADParams(
                # start_secs=0,
                # stop_secs=0,
                # confidence=0.5,
                # min_volume=0.5
                # )
            ),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            video_out_enabled=False,  # Voice-only bot - no video
            video_out_is_live=False,  # Voice-only bot - no video
        ),
    }

    print("🚗 Creating transport...")
    try:
        # For direct runs, modify runner_args to use webrtc transport
        if is_direct_run:
            # Create a mock runner args for webrtc transport
            from types import SimpleNamespace
            webrtc_runner_args = SimpleNamespace()
            webrtc_runner_args.transport = "webrtc"
            webrtc_runner_args.room_url = None
            webrtc_runner_args.token = None
            webrtc_runner_args.body = getattr(runner_args, 'body', {})
            print("🔧 Creating WebRTC transport for direct run...")
            transport = await create_transport(webrtc_runner_args, transport_params)
            print(f"✅ WebRTC Transport created for direct run: {type(transport)}")
        else:
            transport = await create_transport(runner_args, transport_params)
            print(f"✅ Transport created: {type(transport)}")
    except Exception as e:
        print(f"❌ Failed to create transport: {e}")
        if is_direct_run:
            print("💡 For direct runs, make sure you have proper audio devices configured")
        raise

    print("🤖 Starting bot...")
    try:
        await run_bot(transport, runner_args)
        print("✅ Bot completed successfully")
    except Exception as e:
        print(f"❌ Bot failed: {e}")
        import traceback
        print(f"❌ Full bot error traceback: {traceback.format_exc()}")
        raise


# For production with multiple processes:
# Use: gunicorn -w 4 -k uvicorn.workers.UvicornWorker production:app
# Or: uvicorn production:app --host 0.0.0.0 --port 8080 --workers 4

if __name__ == "__main__":
    # For development/single process - force Daily transport
    import sys
    from pipecat.runner.run import main
    
    # If no transport specified, default to Daily
    if "-t" not in sys.argv and "--transport" not in sys.argv:
        sys.argv.extend(["-t", "daily"])
    
    main()
