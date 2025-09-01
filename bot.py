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
import aiohttp

from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import LLMMessagesUpdateFrame
from typing import List, cast
from openai.types.chat import ChatCompletionMessageParam

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds first run only)\n")

logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

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
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.heygen.video import HeyGenVideoService
from pipecat.services.heygen.api import NewSessionRequest
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.services.daily import DailyParams


# Google TTS import (commented out for lower latency)
# from pipecat.services.google.tts import GoogleHttpTTSService, Language

logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    print("🤖 Starting bot function...")
    logger.info(f"Starting bot")
    print(f"🔍 Runner args: {runner_args}")
    print(f"🔍 Transport type: {type(transport)}")

    # Get API keys with error handling
    print("🔑 Checking API keys...")
    
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    if not deepgram_key:
        print("❌ DEEPGRAM_API_KEY not found!")
        raise ValueError("DEEPGRAM_API_KEY environment variable is required")
    print("✅ DEEPGRAM_API_KEY found")
    
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
    
    heygen_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_key:
        print("❌ HEYGEN_API_KEY not found!")
        raise ValueError("HEYGEN_API_KEY environment variable is required")
    print("✅ HEYGEN_API_KEY found")
    print("🔑 All API keys validated!")

    print("🎙️ Initializing speech services...")
    try:
        stt = DeepgramSTTService(api_key=deepgram_key)
        print("✅ Deepgram STT service created")
    except Exception as e:
        print(f"❌ Failed to create Deepgram STT: {e}")
        raise

    # Use Cartesia for lower latency - Google TTS adds significant delay
    try:
        tts = CartesiaTTSService(
            api_key=cartesia_key,
            voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
        )
        print("✅ Cartesia TTS service created")
    except Exception as e:
        print(f"❌ Failed to create Cartesia TTS: {e}")
        raise
    
    # Google TTS alternative (higher latency):
    # tts = GoogleHttpTTSService(
    #     credentials=os.getenv("GOOGLE_TEST_CREDENTIALS"),
    #     voice_id="en-US-Chirp3-HD-Charon",
    #     params=GoogleHttpTTSService.InputParams(
    #         language=Language.EN_US
    #     )
    # )

    print("🧠 Initializing LLM service...")
    try:
        llm = OpenAILLMService(api_key=openai_key)
        print("✅ OpenAI LLM service created")
    except Exception as e:
        print(f"❌ Failed to create OpenAI LLM: {e}")
        raise

    # Create aiohttp session for HeyGen with optimized timeouts
    print("🎭 Initializing HeyGen video service...")
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            # Configure HeyGen video service with optimizations
            heygen = HeyGenVideoService(
                api_key=heygen_key,
                video_encoding="H264",
                session=session,
                session_request=NewSessionRequest(
                    avatar_id="Katya_Chair_Sitting_public"  # Default public avatar
                ),
            )
            print("✅ HeyGen video service created")
        except Exception as e:
            print(f"❌ Failed to create HeyGen service: {e}")
            raise   

        print("🗨️ Setting up conversation context...")
        messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "You are a friendly AI assistant with a visual avatar. Respond naturally and keep your answers conversational.",
            },
        ]

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

        print("🔧 Building pipeline...")
        try:
            pipeline = Pipeline(
                [
                    transport.input(),  # Transport user input
                    rtvi,  # RTVI processor
                    stt,
                    context_aggregator.user(),  # User responses
                    llm,  # LLM
                    tts,  # TTS
                    # heygen,  # HeyGen avatar video generation
                    transport.output(),  # Transport bot output
                    context_aggregator.assistant(),  # Assistant spoken responses
                ]
            )
            print("✅ Pipeline created successfully")
        except Exception as e:
            print(f"❌ Failed to create pipeline: {e}")
            raise

        print("📋 Creating pipeline task...")
        try:
            task = PipelineTask(
                pipeline,
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
                # Kick off the conversation.
                messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
                await task.queue_frames([LLMMessagesUpdateFrame(messages=cast(list, messages), run_llm=True)])
                print("✅ Initial message queued")
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
                await task.cancel()
                print("✅ Task cancelled")
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

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant):
            print(f"👋 Participant left: {participant}")

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

    # Only support Daily transport
    print("🚗 Setting up transport parameters...")
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            # video_out_enabled=True,  # Enable video output for avatar
            # video_out_is_live=True,  # Real-time video streaming
            # video_out_width=1280,  # Reduced for better performance
            # video_out_height=720,
            # audio_out_sample_rate=16000,  # Standard rate for better compatibility
            # camera_out_bitrate=8000,

            vad_analyzer=SileroVADAnalyzer(),
        ),
          "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            video_out_enabled=True,  # Enable video output for avatar
            video_out_is_live=True,  # Real-time video streaming
            video_out_width=1280,  # Reduced for better performance
            video_out_height=720,
        ),
    }

    print("🚗 Creating transport...")
    try:
        transport = await create_transport(runner_args, transport_params)
        print(f"✅ Transport created: {type(transport)}")
    except Exception as e:
        print(f"❌ Failed to create transport: {e}")
        raise

    print("🤖 Starting bot...")
    try:
        await run_bot(transport, runner_args)
        print("✅ Bot completed successfully")
    except Exception as e:
        print(f"❌ Bot failed: {e}")
        raise


# For production with multiple processes:
# Use: gunicorn -w 4 -k uvicorn.workers.UvicornWorker production:app
# Or: uvicorn production:app --host 0.0.0.0 --port 7860 --workers 4

if __name__ == "__main__":
    # For development/single process - force Daily transport
    import sys
    from pipecat.runner.run import main
    
    # If no transport specified, default to Daily
    if "-t" not in sys.argv and "--transport" not in sys.argv:
        sys.argv.extend(["-t", "daily"])
    
    main()
