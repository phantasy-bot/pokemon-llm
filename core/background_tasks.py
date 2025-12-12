import asyncio
import logging
import random
from typing import Optional, Any

log = logging.getLogger("background_tasks")

async def run_chat_background_task(stop_event: asyncio.Event, tts_service: Any, twitch_service: Any, cycle_id: int):
    """
    Background task to generate and play chat responses while LLM is thinking.
    Runs until stop_event is set.
    """
    from services.twitch_chat_service import TWITCH_TEST_MODE
    
    if not TWITCH_TEST_MODE or not tts_service:
        return

    log.info("🚀 Starting background chat response task")
    
    while not stop_event.is_set():
        try:
            # 1. Check if we need to queue more messages (keep buffer full)
            # queue_status = tts_service.get_queue_status()
            # if queue_status["pending"] < 3: ...
            
            # Generate a message if we don't have enough pending
            # Note: queue_and_start_synthesis checks MAX_QUEUE_SIZE internally
            
            # Random chance to generate a new message (don't spam too fast)
            if random.random() < 0.3:  # 30% chance per loop iteration
                test_msg = twitch_service.generate_single_test_message()
                if test_msg:
                    username = test_msg['display_name']
                    msg_text = test_msg['message']
                    
                    # Generate response
                    # from services.twitch_chat_service import CHAT_RESPONSE_PROMPT
                    # We can't use the full LLM here as it would block/compete with main analysis
                    # In test mode, we use the simple mock response generator
                    
                    # Simulating the mock response logic from the main loop:
                    mock_responses = [
                        "Omg hi @{user}! I'm so happy you're here with me!",
                        "@{user} that is so funny! I literally can't even right now!",
                        "Wait @{user}, really? I had no idea about that!",
                        "Thanks for the tip @{user}! I'll try to remember that!",
                        "@{user} you are always so supportive, thank you!",
                        "I'm trying my best @{user}, this game is harder than it looks!",
                        "Haha @{user} I saw that! wild!",
                    ]
                    response_text = random.choice(mock_responses).format(user=username)
                    
                    # Queue it!
                    await tts_service.queue_and_start_synthesis(
                        response_text, 
                        priority=tts_service.PRIORITY_CHAT_RESPONSE,
                        cycle_id=cycle_id
                    )
            
            # 2. Check for ready audio to play
            ready_request = tts_service.get_next_ready_audio()
            if ready_request:
                # Play it! This will block this task for the duration of playback
                # which is exactly what we want (linear playback)
                
                # Check stop event before starting playback
                if stop_event.is_set():
                    break
                    
                log.info(f"🎤 [BG] Playing chat response: {ready_request.text[:30]}...")
                
                completed = await tts_service.play_ready_audio(ready_request, wait=True)
                
                if not completed:
                    log.info("🎤 [BG] Playback interrupted or failed")
            
            # Brief sleep to yield to event loop and avoid busy spin
            await asyncio.sleep(0.5)
            
        except asyncio.CancelledError:
            log.info("🛑 Background chat task cancelled")
            break
        except Exception as e:
            log.error(f"Error in background chat task: {e}")
            await asyncio.sleep(1.0)  # Sleep on error to avoid log spam
