import os
import json
import sys
import time
import base64
import copy
import asyncio
import datetime
import logging
import socket
import re
import math
import concurrent.futures
import functools

from PIL import Image
from token_counter import count_tokens, calculate_prompt_tokens

from pyAIAgent.game.state import prep_llm
from pyAIAgent.navigation import touch_controls_path_find
from pyAIAgent.json_parser import parse_optional_fenced_json
from prompts import build_system_prompt, get_summary_prompt
from client_setup import setup_llm_client, parse_mode_arg, MODES
from benchmark import Benchmark
from client_setup import DEFAULT_MODE, ONE_IMAGE_PER_PROMPT, REASONING_ENABLED, USES_DEFAULT_TEMPERATURE, REASONING_EFFORT, IMAGE_DETAIL, USES_MAX_COMPLETION_TOKENS, MAX_TOKENS, TEMPERATURE, MINIMAP_ENABLED, MINIMAP_2D, SYSTEM_PROMPT_UNSUPPORTED
from pyAIAgent.llm.zai_mcp_client import create_zai_vision_client
from memory_storage import MemoryManager
from battle_strategy import read_battle_state, choose_battle_action, get_battle_context
from goal_tracker import GoalTracker, GoalPriority, GoalStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('llmdriver')


ACTION_RE = re.compile(r'^[LRUDABSs](?:;[LRUDABSs])*(?:;)?$')
COORD_RE = re.compile(r'^([0-9]),([0-8])$')
ANALYSIS_RE = re.compile(r"<game_analysis>([\s\S]*?)</game_analysis>", re.IGNORECASE)
IS_LOCAL = DEFAULT_MODE == "LMSTUDIO" or DEFAULT_MODE == "OLLAMA"

if(IS_LOCAL):
    # Often slow inference
    STREAM_TIMEOUT = 120
else:
    STREAM_TIMEOUT = 60

CLEANUP_WINDOW = 10 # Sometimes 4 is a good choice for local

SCREENSHOT_PATH = "latest.png"
MINIMAP_PATH = "minimap.png"

SAVED_SCREENSHOT_PATH = SCREENSHOT_PATH
SAVED_MINIMAP_PATH = MINIMAP_PATH

# Set CURRENT_MODE from external selection or prompt
CURRENT_MODE = None  # Will be set by main script

def set_current_mode(mode):
    """Set the current LLM mode from external selection"""
    global CURRENT_MODE
    CURRENT_MODE = mode

    # Setup LLM client with the selected mode
    global client, MODEL, supports_reasoning, zai_vision_client
    client, MODEL, supports_reasoning = setup_llm_client(CURRENT_MODE)

    # Initialize Z.AI vision client if using Z.AI mode
    zai_vision_client = None
    if CURRENT_MODE == "ZAI" and client:
        try:
            # Use MCP=True to get the actual MCP vision server with image_analysis tool
            zai_vision_client = create_zai_vision_client(client, MODEL, use_mcp=True)
            log.info("Z.AI sync vision client initialized")
        except Exception as e:
            log.warning(f"Failed to initialize Z.AI vision client: {e}")

# Note: CURRENT_MODE should be set by set_current_mode() before using any llmdriver functions
# This prevents duplicate mode selection prompts

# Initialize variables (will be set properly in set_current_mode)
client = None
MODEL = None
supports_reasoning = False
zai_vision_client = None

chat_history = []
response_count = 0
action_count = 0
tokens_used_session = 0
start_time = datetime.datetime.now()


# ─── Constants ────────────────────────────────────────────────────────────────
LLM_TOTAL_TIMEOUT = STREAM_TIMEOUT + 30     # e.g. 90 s / 150 s

# ─── Helper ───────────────────────────────────────────────────────────────────
async def call_llm_with_timeout(state_data: dict,
                                llm_timeout: float = STREAM_TIMEOUT,
                                total_timeout: float = LLM_TOTAL_TIMEOUT,
                                benchmark: Benchmark = None):
    """
    Run `llm_stream_action` in a worker thread and abort the whole thing
    (token‑counting, API call, streaming, parsing…) after `total_timeout` s.
    """
    loop = asyncio.get_running_loop()
    fn   = functools.partial(llm_stream_action, state_data, llm_timeout, benchmark)

    try:
        # run blocking LLM code in a thread, wait with an asyncio timeout
        return await asyncio.wait_for(loop.run_in_executor(None, fn),
                                      timeout=total_timeout)
    except asyncio.TimeoutError:
        log.error(f"llm_stream_action exceeded {total_timeout}s – skipping cycle.")
        return None, None, None, None

def summarize_and_reset(benchmark: Benchmark = None):
    """Condenses history, updates system prompt, resets history, accounts for tokens."""
    global chat_history, response_count, tokens_used_session

    log.info(f"Summarizing chat history ({len(chat_history)} messages)...")


    history_for_summary = []

    # we convert from 'assistant' to 'user' since many API's don't like multiple 'assistant'
    # messages and will error out.
    for msg in chat_history:
        if msg['role'] == 'assistant':
            history_for_summary.append({
                'role': 'user',
                'content': msg['content']
            })


    if not history_for_summary:
        log.info("No relevant assistant messages to summarize, skipping summarization call.")

        current_system_prompt = chat_history[0]
        chat_history = [current_system_prompt]
        response_count = 0
        log.info("History reset to system prompt without summarization.")
        return None

    summary_prompt = get_summary_prompt()
    summary_input_messages = [{"role": "system", "content": summary_prompt}] + history_for_summary

    logging.info(f"Messages: {summary_input_messages}")

    summary_input_tokens = calculate_prompt_tokens(summary_input_messages)
    log.info(f"Summarization estimated input tokens: {summary_input_tokens}")

    summary_text = "Error generating summary."
    summary_output_tokens = 0

    kwargs = {
        "model": MODEL,
        "messages": summary_input_messages,
    }

    if USES_MAX_COMPLETION_TOKENS:
        kwargs["max_completion_tokens"] = MAX_TOKENS
    else:
        kwargs["max_tokens"] = MAX_TOKENS

    if USES_DEFAULT_TEMPERATURE:
        kwargs["temperature"] = 1.0
    else:
        kwargs["temperature"] = TEMPERATURE

    try:
        summary_resp = client.chat.completions.create(**kwargs)
        if summary_resp.choices and summary_resp.choices[0].message.content:
            summary_text = summary_resp.choices[0].message.content.strip()
            summary_output_tokens = count_tokens(summary_text)
        else:
            log.warning("LLM Summary: No choices or empty content.")
            summary_text = "Summary generation failed."

        total_summary_tokens = summary_input_tokens + summary_output_tokens
        tokens_used_session += total_summary_tokens
        log.info(f"Summarization call used approx. {total_summary_tokens} tokens. Session total: {tokens_used_session}")

    except Exception as e:
        log.error(f"Error during LLM summarization call: {e}", exc_info=True)

    json_object = parse_optional_fenced_json(summary_text)
    
    log.info(f"LLM Summary generated ({summary_output_tokens} tokens): {str(json_object)}")

    benchInstructions = ""
    if benchmark is not None:
        benchInstructions = benchmark.instructions

    new_system_prompt_content = build_system_prompt(summary_text, benchInstructions)
    chat_history = [{"role": "system", "content": new_system_prompt_content}]
    response_count = 0
    log.info("Chat history summarized and reset.")
    return json_object


def next_with_timeout(iterator, timeout: float):
    """Attempt to pull the first chunk from `iterator` within `timeout` seconds."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: next(iterator))
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"No chunk received in {timeout}s")


def llm_stream_action(state_data: dict, timeout: float = STREAM_TIMEOUT, benchmark: Benchmark = None):
    """
    Determines and executes an action by querying an LLM.

    This function intelligently switches between streaming and non-streaming API calls.
    - For models supporting a 'reasoning_effort', it uses a non-streaming call to
      avoid timeouts while the model "thinks".
    - For other models, it streams the response for lower perceived latency.
    - For Z.AI mode, it optionally uses MCP vision server for image analysis.
    """
    global response_count, tokens_used_session, chat_history, zai_vision_client, CURRENT_MODE

    summary_json = None
    vision_analysis_for_ui = None  # Store raw vision analysis for UI display
    payload = copy.deepcopy(state_data)
    screenshot = payload.pop("screenshot", None)
    minimap = payload.pop("minimap", None)

    # Extract Z.AI specific image paths for MCP processing
    screenshot_path = payload.pop("screenshot_path", None)
    minimap_path = payload.pop("minimap_path", None)

    if not MINIMAP_2D:
        print("Minimap 2D disabled, removing minimap_2d from payload.")
        payload.pop("minimap_2d", None)

    if not isinstance(payload, dict):
        log.error(f"Invalid state_data structure: {type(state_data)}")
        return None, None, False

    # CRITICAL: Handle Z.AI vision processing with robust retry and backoff mechanism
    vision_analysis = ""
    vision_analysis_for_ui = None

    if CURRENT_MODE == "ZAI" and screenshot_path and os.path.exists(screenshot_path) and zai_vision_client:
        # Check if MCP server process is still alive before attempting analysis
        if hasattr(zai_vision_client, 'mcp_process') and zai_vision_client.mcp_process:
            if zai_vision_client.mcp_process.poll() is not None:
                log.warning(f"MCP server process has terminated with code: {zai_vision_client.mcp_process.returncode}")
                log.warning("Attempting to restart MCP server...")
                try:
                    # Try to restart the MCP server
                    zai_vision_client._start_mcp_server_sync()
                    if zai_vision_client.is_connected:
                        log.info("MCP server restarted successfully")
                    else:
                        log.warning("Failed to restart MCP server")
                        zai_vision_client.handle_vision_failure("MCP server process terminated and restart failed")
                except Exception as restart_error:
                    log.error(f"Failed to restart MCP server: {restart_error}")
                    zai_vision_client.handle_vision_failure(f"MCP server restart failed: {str(restart_error)}")

        # CRITICAL: Use enhanced vision client with built-in retry and exponential backoff
        try:
            log.info("Z.AI MCP vision server analyzing screenshot with robust retry mechanism...")

            # Use enhanced sync version with built-in exponential backoff
            if hasattr(zai_vision_client, 'analyze_image_sync'):
                # CRITICAL: Updated prompt - JSON format, no styling, no emojis, no bullets
                factual_prompt = (
                    "Analyze this Pokemon Red game screenshot. Output as JSON with these fields:\n\n"
                    "{\n"
                    '  "screen_type": "title|overworld|battle|menu|dialogue|name_entry",\n'
                    '  "readable_text": "any visible text, semicolon separated. ONLY what is perfectly legible.",\n'
                    '  "player_position": "description using directional terms (north/south/east/west)",\n'
                    '  "nearby_objects": "objects near player, semicolon separated",\n'
                    '  "npcs": "visible NPCs and positions, semicolon separated",\n'
                    '  "obstacles": "walls/trees/barriers, semicolon separated",\n'
                    '  "ui_elements": "menus/cursors/hp bars, semicolon separated",\n'
                    '  "battle_info": "if battle: player_pokemon, player_hp, enemy_pokemon, enemy_hp, moves",\n'
                    '  "menu_cursor": "if menu: which option is highlighted",\n'
                    '  "navigation_notes": "doors/exits/paths visible",\n'
                    '  "black_space": "list any large black cut-off areas (e.g. east side, bottom half)"\n'
                    "}\n\n"
                    "RULES:\n"
                    "- Output ONLY valid JSON, no markdown formatting\n"
                    "- Do NOT use bullet points, use semicolons to separate list items\n"
                    "- Do NOT use emojis\n"
                    "- Do NOT use headers or bold text\n"
                    "- Be factual - only report what is clearly visible\n"
                    "- For positions, use relative terms (north, 2 steps east, directly south)\n"
                    "- Player sprite is ALWAYS the red human character with a hat in center of overworld screens\n"
                    "- If text is unclear say 'unreadable'. DO NOT GUESS TEXT.\n"
                    "- Text must be EXACT pixel-for-pixel match. If partially cut off, do not infer words.\n"
                    "- Empty fields should be empty strings\n\n"
                    "SCREEN TYPES:\n"
                    "- title: Pokemon logo, copyright text, no gameplay\n"
                    "- overworld: player sprite visible, walking around\n"
                    "- battle: HP bars, pokemon sprites, move menu\n"
                    "- menu: START menu, item list, pokemon list\n"
                    "- dialogue: text box at bottom, NPC talking\n"
                    "- name_entry: keyboard grid or preset name list"
                )

              # CRITICAL: NEW MANDATORY VISION SYSTEM - Agent will NOT continue without vision
                try:
                    vision_result = zai_vision_client.analyze_image_sync(SAVED_SCREENSHOT_PATH, factual_prompt)

                    # SUCCESS: Vision analysis completed successfully (this should always happen now)
                    log.info(f"✅ Z.AI MCP vision analysis completed: {len(vision_result)} chars")
                    log.info(f"Vision analysis preview: {vision_result[:200]}...")

                    # TEXT PROCESSING: Filter Japanese characters and truncate
                    processed_vision_result = vision_result

                    # Filter out Japanese characters and non-English text
                    processed_vision_result = re.sub(r'[\u3040-\u309F\u30A0-\u30FF]', '', processed_vision_result)

                    # Remove first 17 and last 14 characters as specified
                    if len(processed_vision_result) > 31:
                        processed_vision_result = processed_vision_result[17:-14]

                    vision_analysis = f"Z.AI GLM-4.6 Vision Analysis: {processed_vision_result}"
                    vision_analysis_for_ui = processed_vision_result  # Store processed vision analysis for UI
                    payload["vision_analysis"] = vision_analysis
                    # Also add a more prominent vision field for better LLM recognition
                    payload["visual_context"] = processed_vision_result

                except RuntimeError as e:
                    # CRITICAL: ALL VISION RETRY ATTEMPTS EXHAUSTED - System cannot continue
                    log.error("🚨 " + "="*80)
                    log.error("🚨 CRITICAL: Vision system completely failed! Agent cannot continue without vision.")
                    log.error(f"🚨 Error: {e}")
                    log.error("🚨 " + "="*80)

                    # This is a catastrophic failure - the agent requires vision to function
                    # We should either:
                    # 1. Stop the agent completely, or
                    # 2. Try to save the game and exit gracefully

                    # For now, we'll set a critical error state and stop the main loop
                    payload["critical_system_failure"] = True
                    payload["vision_analysis"] = "CRITICAL SYSTEM FAILURE: Vision analysis completely failed after exhaustive retry attempts. Agent cannot continue without vision input."
                    payload["system_halt"] = True

                    # Trigger immediate shutdown
                    log.critical("🛑 Halting agent operation due to catastrophic vision system failure")
                    return None  # This will stop the main loop in the calling code

            elif hasattr(zai_vision_client, 'analyze_image'):
                # Handle sync fallback client (ZAIVisionFallback)
                log.warning("Using fallback vision client (ZAIVisionFallback)")
                vision_result = zai_vision_client.analyze_image(SAVED_SCREENSHOT_PATH, factual_prompt)

                if vision_result:
                    # TEXT PROCESSING: Filter Japanese characters and truncate
                    processed_vision_result = vision_result

                    # Filter out Japanese characters and non-English text
                    processed_vision_result = re.sub(r'[\u3040-\u309F\u30A0-\u30FF]', '', processed_vision_result)

                    # Remove first 17 and last 14 characters as specified
                    if len(processed_vision_result) > 31:
                        processed_vision_result = processed_vision_result[17:-14]

                    vision_analysis = f"Z.AI Vision Analysis (Fallback): {processed_vision_result}"
                    vision_analysis_for_ui = processed_vision_result
                    payload["vision_analysis"] = vision_analysis
                    payload["visual_context"] = processed_vision_result
                else:
                    payload["vision_analysis"] = "[Fallback vision analysis failed]"
                    log.warning("Fallback vision analysis failed")
            else:
                log.warning("Z.AI vision client doesn't have analyze_image method")
                payload["vision_analysis"] = "[Vision client method unavailable]"

        except Exception as e:
            # CRITICAL: Handle vision analysis exception without crashing the app
            error_msg = f"Vision analysis exception: {str(e)}"
            log.error(f"CRITICAL VISION ERROR: {error_msg}", exc_info=True)

            # Use the client's built-in failure handling if available
            if hasattr(zai_vision_client, 'handle_vision_failure'):
                zai_vision_client.handle_vision_failure(error_msg)

            payload["vision_analysis"] = f"[Vision analysis failed: {error_msg}]"

            # CRITICAL: DO NOT return None, None, False - continue without vision analysis
            log.error("Vision analysis failed, but game will continue without visual input")

    elif CURRENT_MODE == "ZAI":
        # ZAI mode but no vision client available
        log.warning("ZAI mode detected but no vision client available - continuing without vision analysis")
        payload["vision_analysis"] = "[Vision client not initialized]"

    # Build the user message with text and images
    image_parts_for_api = []

    # Include vision analysis directly in the text content for Z.AI mode
    text_content = json.dumps(payload)
    if CURRENT_MODE == "ZAI" and vision_analysis:
        # Add vision analysis directly to the text for Z.AI mode
        text_content = f"{text_content}\n\nIMPORTANT VISION ANALYSIS:\n{vision_analysis}"

    text_segment = {"type": "text", "text": text_content}
    current_content = [text_segment]

    # Standard image processing for API
    if screenshot and isinstance(screenshot.get("image_url"), dict):
        image_parts_for_api.append({"type": "image_url", "image_url": screenshot["image_url"]})
    if minimap and MINIMAP_ENABLED and isinstance(minimap.get("image_url"), dict):
        image_parts_for_api.append({"type": "image_url", "image_url": minimap["image_url"]})

    current_content.extend(image_parts_for_api)
    
    if(SYSTEM_PROMPT_UNSUPPORTED):
        # TODO: Handle system prompt in messages
        pass

    current_user_message_api = {"role": "user", "content": current_content}
    messages_for_api = chat_history + [current_user_message_api]

    # Token accounting
    call_input_tokens = calculate_prompt_tokens(messages_for_api)
    log.info(f"LLM call estimate: {call_input_tokens} input tokens; history turns: {len(chat_history)}")

    full_output = ""
    action = None
    analysis_text = None

    try:
        # --- API Call Section: Conditional Streaming ---
        kwargs = {
            "model": MODEL,
            "messages": messages_for_api,
            "temperature": TEMPERATURE,
            "timeout": timeout,
        }

        if USES_MAX_COMPLETION_TOKENS:
            kwargs["max_completion_tokens"] = MAX_TOKENS
        else:
            kwargs["max_tokens"] = MAX_TOKENS

        if USES_DEFAULT_TEMPERATURE:
            kwargs["temperature"] = 1.0
        else:
            kwargs["temperature"] = TEMPERATURE

        if supports_reasoning and REASONING_ENABLED:
            # NON-STREAMING path for reasoning models: more robust against long "thinking" times.
            log.info("Model supports reasoning. Making a non-streaming API call.")
            kwargs["stream"] = False

            # For Z.AI, use the correct API parameter format
            if CURRENT_MODE == "ZAI":
                # Create request with Z.AI GLM-4.6 specific parameters
                zai_kwargs = {
                    "model": kwargs.get("model"),
                    "messages": kwargs.get("messages"),
                    "stream": False
                }

                # Add Z.AI specific parameters according to their documentation
                if "max_tokens" in kwargs:
                    zai_kwargs["max_tokens"] = kwargs["max_tokens"]
                if "temperature" in kwargs:
                    zai_kwargs["temperature"] = kwargs["temperature"]

                # Z.AI GLM-4.6 supports thinking parameter with specific format
                if "thinking" not in zai_kwargs:
                    zai_kwargs["thinking"] = {"type": "enabled"}

                # Remove any unsupported parameters that might be in kwargs
                for key in list(zai_kwargs.keys()):
                    if zai_kwargs[key] is None:
                        del zai_kwargs[key]

                # Log detailed request information for debugging
                log.info(f"Z.AI API call - Model: {zai_kwargs['model']}")
                log.info(f"Z.AI API call - Messages count: {len(zai_kwargs['messages']) if zai_kwargs['messages'] else 0}")
                if zai_kwargs['messages']:
                    # Log first message content type and length
                    first_msg = zai_kwargs['messages'][0]
                    log.info(f"Z.AI API call - First message role: {first_msg.get('role', 'unknown')}")
                    if 'content' in first_msg:
                        if isinstance(first_msg['content'], list):
                            content_types = [item.get('type') for item in first_msg['content'] if isinstance(item, dict)]
                            log.info(f"Z.AI API call - Content types: {content_types}")
                        else:
                            log.info(f"Z.AI API call - Content type: {type(first_msg['content']).__name__}")
                            log.info(f"Z.AI API call - Content preview: {str(first_msg['content'])[:200]}...")

                log.info(f"Z.AI API call - Full request structure: {json.dumps({k: v if k != 'messages' else f'array[{len(zai_kwargs[k])}]' for k, v in zai_kwargs.items()}, indent=2)}")
                log.info(f"Z.AI API call - Base URL: {client.base_url}")

                try:
                    # Use raw HTTP request for Z.AI since OpenAI client is not compatible
                    import httpx

                    # Convert to text-only messages for Z.AI coding plan API compatibility
                    text_only_messages = []
                    for msg in zai_kwargs["messages"]:
                        if isinstance(msg.get("content"), list):
                            # Extract only text content from multimodal messages
                            text_content = ""
                            for content_item in msg["content"]:
                                if isinstance(content_item, dict) and content_item.get("type") == "text":
                                    text_content += content_item.get("text", "")
                                elif isinstance(content_item, str):
                                    text_content += content_item
                            if text_content.strip():
                                text_only_messages.append({
                                    "role": msg.get("role", "user"),
                                    "content": text_content.strip()
                                })
                        else:
                            # Handle regular text content
                            text_only_messages.append({
                                "role": msg.get("role", "user"),
                                "content": msg.get("content", "")
                            })

                    api_data = {
                        "model": zai_kwargs["model"],
                        "messages": text_only_messages
                    }

                    # Add optional parameters if available
                    if "max_tokens" in zai_kwargs:
                        api_data["max_tokens"] = zai_kwargs["max_tokens"]
                    if "temperature" in zai_kwargs:
                        api_data["temperature"] = zai_kwargs["temperature"]

                    log.info(f"Z.AI API call - Using text-only messages for coding API: {len(text_only_messages)} messages")

                    log.info(f"Z.AI API call - Making raw HTTP request to: {client.base_url}chat/completions")
                    log.info(f"Z.AI API call - Request data keys: {list(api_data.keys())}")

                    # Create httpx client with headers
                    headers = {
                        "Authorization": f"Bearer {client.api_key}",
                        "Content-Type": "application/json"
                    }

                    with httpx.Client(timeout=30.0) as http_client:
                        response = http_client.post(
                            f"{client.base_url}chat/completions",
                            json=api_data,
                            headers=headers
                        )

                        if response.status_code == 200:
                            response_data = response.json()
                            log.info("Z.AI API call successful via raw HTTP")
                            log.info(f"Z.AI API response - Keys: {list(response_data.keys())}")

                            # Create mock classes outside the class definition
                            class MockMessage:
                                def __init__(self, message_data):
                                    self.content = message_data.get('content', None)

                            class MockChoice:
                                def __init__(self, choice_data):
                                    self.message = MockMessage(choice_data.get('message', {}))
                                    self.finish_reason = choice_data.get('finish_reason', 'unknown')

                            class MockResponse:
                                def __init__(self, data):
                                    self.choices = []
                                    if 'choices' in data and data['choices']:
                                        self.choices = [MockChoice(choice) for choice in data['choices']]

                            response = MockResponse(response_data)
                        else:
                            log.error(f"Z.AI API HTTP request failed: {response.status_code}")
                            log.error(f"Z.AI API response: {response.text}")
                            raise Exception(f"HTTP {response.status_code}: {response.text}")

                except Exception as e:
                    log.error(f"Z.AI API call failed with raw HTTP: {str(e)}")
                    log.error(f"Z.AI API request was: {json.dumps(api_data, default=str, indent=2)}")
                    raise e
            else:
                kwargs["reasoning_effort"] = REASONING_EFFORT
                response = client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content

            if content:
                full_output = content.strip()
                print(f">>> {full_output}", end="", flush=True)
            else:
                log.warning(
                    f"LLM response content was None. Finish reason: '{choice.finish_reason}'. "
                    "This is often due to content filtering."
                )
                full_output = ""

        else:
            # STREAMING path for standard models: provides faster user feedback.
            log.info("Model does not use reasoning effort. Using streaming API call.")
            kwargs["stream"] = True

            response = client.chat.completions.create(**kwargs)

            iterator = iter(response)
            collected_chunks = []
            stream_start = time.time()
            log.info("LLM Stream starting…")
            print(">>> ", end="", flush=True)

            # First-chunk timeout
            try:
                chunk = next_with_timeout(iterator, timeout)
            except StopIteration:
                log.warning("Stream ended immediately with no chunks.")
                chunk = None
            except TimeoutError:
                log.warning(f"TIMEOUT waiting for first chunk after {timeout}s.")
                return None, None, None

            if chunk:
                # Process first chunk
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    collected_chunks.append(delta)
                
                # Continue until finish or total timeout
                if not chunk.choices[0].finish_reason:
                    for chunk in iterator:
                        if time.time() - stream_start > timeout:
                            print("\n[TIMEOUT]", flush=True)
                            log.warning(f"LLM stream timed out after {timeout}s total")
                            raise TimeoutError(f"Stream timed out after {timeout}s")

                        delta = chunk.choices[0].delta.content
                        if delta:
                            print(delta, end="", flush=True)
                            collected_chunks.append(delta)

                        if chunk.choices[0].finish_reason:
                            print(f"\n[END - {chunk.choices[0].finish_reason}]", flush=True)
                            log.info(f"LLM stream finished: {chunk.choices[0].finish_reason}")
                            break
            
            # Assemble final output from chunks
            full_output = "".join(collected_chunks).strip()

        # --- Post-processing Section (common to both paths) ---

        if not full_output:
            log.error("LLM call resulted in empty output.")
            return None, None, None

        log.info(f"LLM raw output length: {len(full_output)} chars")

        # Token accounting for the output
        output_tokens = count_tokens(full_output)
        tokens_used_session += call_input_tokens + output_tokens
        log.info(f"Used ~{output_tokens} output tokens; session total: {tokens_used_session}")

        user_hist_content = [text_segment] # Images are not saved in history
        chat_history.append({"role": "user", "content": user_hist_content})
        chat_history.append({"role": "assistant", "content": full_output})

        # Cleanup history if window is reached
        response_count += 1
        if response_count >= CLEANUP_WINDOW:
            summary_json = summarize_and_reset(benchmark)
            response_count = 0 # Reset counter
            time.sleep(5)

        # Extract analysis section
        match = ANALYSIS_RE.search(full_output)
        if match:
            analysis_text = match.group(1).strip()
        else:
            # Fallback: if no game_analysis tags, try to extract content before action JSON
            lines = full_output.strip().split('\n')
            non_json_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('{') and not line.endswith('}') and not line.startswith('"action"'):
                    non_json_lines.append(line)

            if non_json_lines:
                analysis_text = '\n'.join(non_json_lines)
                log.info(f"🔍 Using fallback analysis extraction: {analysis_text[:100]}...")
            else:
                log.warning(f"⚠️ No analysis text found in LLM output. Full output: {full_output[:200]}...")
                analysis_text = "No analysis available"

        # Extract action JSON - search ANYWHERE in output (may be before closing tags)
        action = None
        parsed = None
        
        # Find all JSON-like blocks and try to parse them for action/touch
        for json_match in re.finditer(r'\{[^{}]*\}', full_output):
            try:
                parsed = json.loads(json_match.group())
                act = parsed.get("action")
                touch = parsed.get("touch")
                vision_from_json = parsed.get("vision_analysis")

                # Use vision analysis from JSON if provided
                if vision_from_json and isinstance(vision_from_json, str):
                    vision_analysis_for_ui = vision_from_json

                if isinstance(act, str) and ACTION_RE.match(act):
                    action = act
                    log.info(f"✅ Found action in JSON: {action}")
                    break
                elif isinstance(touch, str) and COORD_RE.match(touch):
                    # handle JSON-provided touch coords
                    x, y = state_data["position"]
                    coords = [int(i) for i in touch.split(",")]
                    action = touch_controls_path_find(
                        state_data["map_id"],
                        [x, y],
                        coords
                    )
                    log.info(f"✅ Found touch in JSON, converted to action: {action}")
                    break
            except json.JSONDecodeError:
                continue  # Try next JSON block

        # Fallback: last line matching ACTION_RE or COORD_RE
        if action is None:
            lines = [line.strip() for line in full_output.splitlines() if line.strip()]
            if lines:
                last = lines[-1]
                # plain “action” string
                if ACTION_RE.match(last) and not last.startswith('{'):
                    action = last

                # plain touch coords
                elif COORD_RE.match(last):
                    x, y = state_data["position"]
                    coords = [int(i) for i in last.split(",")]
                    action = touch_controls_path_find(
                        state_data["map_id"],
                        [x, y],
                        coords
                    )

    except Exception as e:
        log.error(f"Error during LLM interaction: {e}", exc_info=True)
        return None, None, None, None

    if action is None:
        log.error("No valid action extracted from LLM output.")

    return action, analysis_text, summary_json, vision_analysis_for_ui



def encode_image_base64(image_path: str) -> str | None:
    """Reads an image file and returns its base64 encoded string."""
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log.error(f"Error reading/encoding image '{image_path}': {e}")
        return None


async def run_auto_loop(sock, state: dict, broadcast_func, interval: float = 8.0, max_loops = math.inf, benchmark: Benchmark = None):
    """Main async loop: Get state, call LLM, send action, update/broadcast state."""
    global action_count, tokens_used_session, start_time, chat_history, SCREENSHOT_PATH, MINIMAP_PATH, SAVED_SCREENSHOT_PATH, SAVED_MINIMAP_PATH

    # Initialize memory manager
    memory_manager = MemoryManager()
    log.info("Memory manager initialized for spatial learning")

    # Initialize goal tracker
    goal_tracker = GoalTracker()
    if not goal_tracker.goals:
        goal_tracker.initialize_default_goals()
    log.info("Goal tracker initialized")

    # Position history for stuck detection
    position_history = []
    
    # Track last action for failure replay
    last_action = None
    last_position = None

    b64_mm = None

    benchInstructions = ""
    if benchmark is not None:
        benchInstructions = benchmark.instructions
        logging.info(f"Added bench instructions: {benchInstructions}")
    chat_history = [{"role": "system", "content": build_system_prompt("", benchInstructions)}]

    while action_count < max_loops:
        loop_start_time = time.time()
        current_cycle = action_count + 1
        log.info(f"--- Loop Cycle {current_cycle} ---")

        update_payload = {}
        action_payload = {}

        try:
            log.info("Requesting game state from mGBA...")
            current_mGBA_state = prep_llm(sock)

            if benchmark is not None:
                # check if we complted the bench
                if(benchmark.validation(current_mGBA_state)):
                    break

            #print(str(current_mGBA_state))
            if not current_mGBA_state:
                log.error("Failed to get state from mGBA (prep_llm returned None). Skipping.")
                await asyncio.sleep(max(0, interval - (time.time() - loop_start_time)))
                continue
            log.info("Received game state from mGBA.")
        except socket.timeout:
             log.error("Socket timeout getting state from mGBA. Stopping loop.")
             break
        except socket.error as se:
             log.error(f"Socket error getting state from mGBA: {se}. Stopping loop.")
             break
        except Exception as e:
            log.error(f"Error getting state from mGBA: {e}", exc_info=True)
            await asyncio.sleep(max(0, interval - (time.time() - loop_start_time)))
            continue

        llm_input_state = copy.deepcopy(current_mGBA_state)
        state_update_start = time.time()
        
        # Track position for stuck detection
        current_pos = current_mGBA_state.get('position')
        current_map = current_mGBA_state.get('map_id')
        if current_pos and current_map:
            position_history.append((current_map, tuple(current_pos)))
            # Keep only last 10 positions
            position_history = position_history[-10:]
            
            # Check if stuck and record failure
            stuck_info = memory_manager.detect_stuck(position_history)
            if stuck_info["is_stuck"]:
                log.warning(f"🔄 STUCK DETECTED: {stuck_info['suggestion']}")
                llm_input_state["stuck_warning"] = stuck_info["suggestion"]
                
                # Record failure for replay context
                if last_action and last_position:
                    goal_tracker.record_failure(
                        action=last_action,
                        position=last_position,
                        reason="Position unchanged - movement blocked"
                    )
        
        # Add memory context to LLM input
        map_name = current_mGBA_state.get('map_name', '')
        memory_context = memory_manager.get_context_for_llm(map_name)
        if memory_context:
            llm_input_state["memory_context"] = memory_context
            log.info(f"📝 Memory context: {memory_context[:100]}...")
        
        # Add battle context using game memory (more accurate than vision)
        try:
            battle_context = get_battle_context(sock)
            if battle_context:
                llm_input_state["battle_context"] = battle_context
                log.info(f"⚔️ Battle detected: {battle_context[:80]}...")
        except Exception as e:
            log.debug(f"Battle context error (not in battle): {e}")
        
        # Add goal context
        goal_context = goal_tracker.get_context_for_llm()
        if goal_context:
            llm_input_state["goal_context"] = goal_context
            log.info(f"🎯 Goals: {goal_context[:80]}...")


        new_team = current_mGBA_state.get('party')
        if new_team is not None and json.dumps(new_team) != json.dumps(state.get('currentTeam')):
            state['currentTeam'] = new_team
            update_payload['currentTeam'] = state['currentTeam']
            log.info("State Update: currentTeam")


        badge_data = current_mGBA_state.get('badges')
        current_state_badges = state.get('badges')

        # Compare the new list with the stored list
        if badge_data != current_state_badges:
            log.info(f"State Update: Badges changed from {current_state_badges} to {badge_data}")
            state['badges'] = badge_data
            update_payload['badges'] = badge_data


        pos = current_mGBA_state.get('position')
        map_id = current_mGBA_state.get('map_id', 'N/A')
        map_name = current_mGBA_state.get('map_name', '')
        loc_str = "Unknown"
        if pos:
            loc_str = f"{map_name} (Map {map_id}) ({pos[0]}, {pos[1]})" if map_name else f"Map {map_id} ({pos[0]}, {pos[1]})"
        if loc_str != state.get('minimapLocation'):
            state['minimapLocation'] = loc_str
            update_payload['minimapLocation'] = state['minimapLocation']
            log.info(f"State Update: minimapLocation -> {loc_str}")

        if ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
            try:
                # Load images
                ss_img = Image.open(SAVED_SCREENSHOT_PATH)
                mm_img = Image.open(SAVED_MINIMAP_PATH)

                # Resize minimap to match screenshot height
                mm_ratio = ss_img.height / mm_img.height
                new_mm_width = int(mm_img.width * mm_ratio)
                mm_img = mm_img.resize((new_mm_width, ss_img.height), Image.LANCZOS)

                # Create a new canvas wide enough for both
                combined_width = ss_img.width + mm_img.width
                combined = Image.new('RGB', (combined_width, ss_img.height))

                # Paste screenshot at (0,0), minimap at (ss.width, 0)
                combined.paste(ss_img, (0, 0))
                combined.paste(mm_img, (ss_img.width, 0))

                # Save combined image and override SCREENSHOT_PATH
                combined_path = os.path.splitext(SAVED_SCREENSHOT_PATH)[0] + '_with_minimap.png'
                combined.save(combined_path)
                SCREENSHOT_PATH = combined_path

                log.info(f"Combined screenshot + minimap saved to {combined_path}")
            except Exception as e:
                log.error(f"Failed to combine minimap: {e}")

        # Handle image processing based on provider
        if CURRENT_MODE == "ZAI" and zai_vision_client:
            # For Z.AI, store image paths for MCP processing
            llm_input_state["screenshot_path"] = SCREENSHOT_PATH
            if not ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
                llm_input_state["minimap_path"] = MINIMAP_PATH

            # Also create base64 versions for fallback
            b64_ss = encode_image_base64(SCREENSHOT_PATH)
            if b64_ss:
                llm_input_state["screenshot"] = {"image_url": {"url": f"data:image/png;base64,{b64_ss}", "detail": IMAGE_DETAIL}}
            else:
                llm_input_state["screenshot"] = None

            if not ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
                b64_mm = encode_image_base64(MINIMAP_PATH)
                if b64_mm:
                    llm_input_state["minimap"] = {"image_url": {"url": f"data:image/png;base64,{b64_mm}", "detail": IMAGE_DETAIL}}
        else:
            # Standard base64 image processing for other providers
            b64_ss = encode_image_base64(SCREENSHOT_PATH)
            if b64_ss:
                llm_input_state["screenshot"] = {"image_url": {"url": f"data:image/png;base64,{b64_ss}", "detail": IMAGE_DETAIL}}
            else:
                llm_input_state["screenshot"] = None

            if not ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
                b64_mm = encode_image_base64(MINIMAP_PATH)
                if b64_mm:
                    llm_input_state["minimap"] = {"image_url": {"url": f"data:image/png;base64,{b64_mm}", "detail": IMAGE_DETAIL}}
            else:
                llm_input_state["minimap"] = None

        log.info(f"Pre-LLM state update & image prep took {time.time() - state_update_start:.2f}s. SS:{bool(b64_ss)}, MM:{bool(b64_mm)}")

        log_id_counter = state.get("log_id_counter", 0) + 1
        state["log_id_counter"] = log_id_counter

        action, game_analysis, summary_json, vision_analysis_for_ui = await call_llm_with_timeout(llm_input_state, benchmark=benchmark)

        if summary_json is not None:
            tmp = {"log_entry": {"id": log_id_counter, "text": "🔎 Chat history cleaned up."}}
            await broadcast_func(tmp)

            required = ("primaryGoal", "secondaryGoal", "tertiaryGoal", "otherNotes")

            if isinstance(summary_json, dict):
                # summary_json is dict, safe to check for keys
                missing = [k for k in required if k not in summary_json]
                if not missing:
                    state["goals"] = {
                        "primary":   summary_json["primaryGoal"],
                        "secondary": summary_json["secondaryGoal"],
                        "tertiary":  summary_json["tertiaryGoal"],
                    }
                    state["otherGoals"] = summary_json["otherNotes"]
                    update_payload["goals"] = state["goals"]
                    update_payload["otherGoals"] = state["otherGoals"]
                else:
                    logging.error(f"Missing required goal keys in summary_json: {missing!r}")
            else:
                logging.error(f"Expected summary_json to be dict, but got {type(summary_json).__name__!r}")

        # Add vision analysis to the update payload if available
        if vision_analysis_for_ui:
            update_payload["vision_analysis"] = vision_analysis_for_ui

        action_to_send = None
        log_action_text = "No action taken (LLM failed)."

        if action:
            action_to_send = action
            log_action_text = f"Action: {action}"
            log.info(f"LLM proposed action: {action}")
            try:
                sock.sendall((action_to_send + "\n").encode("utf-8"))
                log.info(f"Action '{action_to_send}' sent to mGBA.")
                # Track for failure replay
                last_action = action_to_send
                last_position = current_pos
            except socket.error as se:
                log.error(f"Socket error sending action '{action_to_send}': {se}. Stopping loop.")
                break
            except Exception as e:
                log.error(f"Unexpected error sending action '{action_to_send}': {e}", exc_info=True)

        else:
            log.error("No valid action from LLM. Cannot send command.")

        action_count = current_cycle
        if state.get('actions') != action_count:
             state['actions'] = action_count
             update_payload['actions'] = action_count

        if state.get('tokensUsed') != tokens_used_session:
            state['tokensUsed'] = tokens_used_session
            update_payload['tokensUsed'] = tokens_used_session

        elapsed = datetime.datetime.now() - start_time
        game_status_str = f"{int(elapsed.total_seconds() // 3600)}h {int((elapsed.total_seconds() % 3600) // 60)}m {int(elapsed.total_seconds() % 60)}s"
        if state.get('gameStatus') != game_status_str:
            state['gameStatus'] = game_status_str
            update_payload['gameStatus'] = game_status_str

        if state.get('modelName') != MODEL:
            state['modelName'] = MODEL
            update_payload['modelName'] = MODEL



        # Create three separate log entries: VISION, RESPONSE, ACTION
        log_entries = []

        # Vision log entry - only create if we have actual vision analysis
        cycle_timestamp = int((time.time() - 2) * 1000)  # Approximate when screenshot was taken
        
        if vision_analysis_for_ui:
            vision_log = {
                "id": log_id_counter,
                "text": vision_analysis_for_ui,
                "is_vision": True,
                "timestamp": cycle_timestamp
            }
            log_entries.append(vision_log)
            log.info(f"📸 Vision log created: {len(vision_analysis_for_ui)} chars")

        # Response log entry (LLM reasoning)
        analysis_text = game_analysis  # Use game_analysis from LLM response
        log.info(f"🧠 LLM Analysis received: {analysis_text[:100] if analysis_text else 'None'}...")

        if analysis_text and analysis_text.strip():
            response_log = { "id": log_id_counter, "text": analysis_text.strip(), "is_response": True }
            log_entries.append(response_log)
            log.info(f"✅ Response log created and added to entries")
        else:
            log.warning(f"⚠️ No analysis_text to send to frontend. game_analysis: {game_analysis}")

                # Force memory recording for important location transitions
            try:
                # MAP TRANSITION LOGIC
                # Track transitions to verification
                current_map = state.get('map_name', 'unknown')
                current_map_id = state.get('map_id', -1)
                current_pos = state.get('position', [])

                # We need to track the PREVIOUS map/pos to record a link
                # use attributes on memory_manager to persist across loops efficiently
                last_map = getattr(memory_manager, 'last_map', None)
                last_map_id = getattr(memory_manager, 'last_map_id', None)
                last_pos = getattr(memory_manager, 'last_pos', None)

                # Check if map changed (and neither is unknown)
                if (current_map != 'unknown' and last_map != 'unknown' and 
                    current_map_id != -1 and last_map_id != -1 and
                    (current_map != last_map or current_map_id != last_map_id)):
                    
                    # We moved between maps! exact position we left FROM is last_pos
                    # exact position we arrived AT is current_pos
                    
                    if last_pos and current_pos:
                        new_links = memory_manager.record_transition(
                            from_map=last_map,
                            from_pos=last_pos,
                            to_map=current_map,
                            to_pos=current_pos
                        )
                        if new_links:
                             log.info(f"🔗 VERIFIED TRANSITION RECORDED: {last_map} -> {current_map}")
                             update_payload["memory_write"] = {"text": f"Mapped connection: {last_map} -> {current_map}"}
                
                # Update history for next loop
                memory_manager.last_map = current_map
                memory_manager.last_map_id = current_map_id
                memory_manager.last_pos = current_pos

                # Extract memories from LLM response and vision analysis
                extracted_memories = memory_manager.extract_memories_from_response(
                    analysis_text=analysis_text,
                    game_state=state,
                    vision_analysis=vision_analysis_for_ui  # Fixed: was 'vision_analysis' which doesn't exist
                )

                if extracted_memories:
                    log.info(f"Extracted {len(extracted_memories)} memories from LLM response")
                    for memory in extracted_memories:
                        log.debug(f"Memory: {memory.type} - {memory.description[:50]}...")

                # Always get latest memory for broadcasting
                latest_memory = memory_manager.get_latest_memory()
                if latest_memory:
                    # Add memory directly to update_payload for frontend compatibility
                    update_payload["memory_write"] = {"text": latest_memory.description}
                    log.info(f"Broadcasting latest memory: {latest_memory.description[:100]}...")

                    # Also add to memory_updates array for potential future use
                    if "memory_updates" not in update_payload:
                        update_payload["memory_updates"] = []
                    memory_payload = {"memory_write": {"text": latest_memory.description}}
                    update_payload["memory_updates"].append(memory_payload)

            except Exception as e:
                log.error(f"Error extracting memories: {e}", exc_info=True)

        # Action log entry
        if action:
            action_log = { "id": log_id_counter, "text": log_action_text, "is_action": True }
            log_entries.append(action_log)

        # Add all log entries to update_payload with different keys to avoid overwriting
        # Add all log entries to update_payload with different keys to avoid overwriting
        # Also persist to state["log_history"] for new connections
        if "log_history" not in state:
            state["log_history"] = []

        for i, log_entry in enumerate(log_entries):
            # Add timestamp if missing
            if "timestamp" not in log_entry:
                log_entry["timestamp"] = int(time.time() * 1000)

            # Add to persistent history (keep last 50)
            state["log_history"].insert(0, log_entry)
            
            if log_entry.get("is_vision"):
                update_payload["vision_log"] = log_entry
                log.info(f"🖼️ Broadcasting vision log: {log_entry.get('text', '')[:50]}... with timestamp: {log_entry.get('timestamp')}")
            elif log_entry.get("is_response"):
                update_payload["response_log"] = log_entry
                log.info(f"💭 Broadcasting response log: {log_entry.get('text', '')[:50]}...")
            elif log_entry.get("is_action"):
                action_payload["log_entry"] = log_entry
                log.info(f"🎮 Broadcasting action log: {log_entry.get('text', '')[:50]}...")

        # Trim history
        state["log_history"] = state["log_history"][:50]
        # Important: Add logs to update_payload so websocket_service sends them if needed? 
        # Actually websocket_service sends full state on connect.
        # But we might want to send 'logs' bulk update if we wanted to sync, but individual updates are fine.

        log.info(f"Log Entry #{log_id_counter}: {log_action_text} (Analysis included in state log)")

        # CRITICAL: Check for system failure before broadcasting
        if update_payload and update_payload.get("system_halt"):
            log.critical("🛑 SYSTEM HALT DETECTED - Terminating agent operation immediately")
            break  # Exit the main loop immediately

        if update_payload:
            log.info(f"Broadcasting {len(update_payload)} state updates: {list(update_payload.keys())}")
            try:
                await broadcast_func(update_payload)
                await broadcast_func(action_payload)
            except Exception as e:
                log.error(f"Error during WebSocket broadcast: {e}", exc_info=True)


        elapsed_loop_time = time.time() - loop_start_time
        wait_time = max(10, interval - elapsed_loop_time) # Ensure at least 10 seconds wait
        log.info(f"Cycle {current_cycle} took {elapsed_loop_time:.2f}s. Waiting {wait_time:.2f}s...")
        await asyncio.sleep(wait_time)


    log.info("Auto loop terminated.")
    if benchmark is not None:
        benchmark.finalize(current_mGBA_state, MODEL)