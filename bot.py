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
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.services.daily import DailyParams

logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")

    # Get API keys with error handling
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    if not deepgram_key:
        raise ValueError("DEEPGRAM_API_KEY environment variable is required")
    
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY environment variable is required")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    heygen_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_key:
        raise ValueError("HEYGEN_API_KEY environment variable is required")

    stt = DeepgramSTTService(api_key=deepgram_key)

    tts = CartesiaTTSService(
        api_key=cartesia_key,
        voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
    )

    llm = OpenAILLMService(api_key=openai_key)

    # Create aiohttp session for HeyGen
    session = aiohttp.ClientSession()
    
    # Configure HeyGen video service
    heygen = HeyGenVideoService(
        api_key=heygen_key,
        session=session,
        session_request=NewSessionRequest(
            avatar_id="Katya_Chair_Sitting_public"  # Default public avatar
        ),
    )

    messages: List[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": "You are a friendly AI assistant with a visual avatar. Respond naturally and keep your answers conversational.",
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,  # RTVI processor
            stt,
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            heygen,  # HeyGen avatar video generation
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMMessagesUpdateFrame(messages=cast(list, messages), run_llm=True)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await session.close()  # Clean up HeyGen session
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    # Only support Daily transport
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=True,  # Enable video output for avatar
            video_out_is_live=True,  # Real-time video streaming
            video_out_width=360,
            video_out_height=240,
            audio_out_sample_rate=12000,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


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
