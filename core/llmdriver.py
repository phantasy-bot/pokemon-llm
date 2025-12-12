import os
import json
import sys
import time
import base64
import shutil
import copy
import asyncio
import datetime
import logging
import socket
import re
import math
import concurrent.futures
import functools
import subprocess
import threading

from PIL import Image
from core.token_counter import count_tokens, calculate_prompt_tokens

from pyAIAgent.game.state import prep_llm, get_rom_path
from pyAIAgent.game.state import prep_llm, get_rom_path
from pyAIAgent.navigation import touch_controls_path_find, find_path
from pyAIAgent.json_parser import parse_optional_fenced_json
from pyAIAgent.utils.socket_utils import send_command
from pyAIAgent.game.keyboard_tracker import get_keyboard_tracker
from pyAIAgent.game.name_planner import get_name_planner, RIVAL_NAME_SUGGESTIONS

from core.prompts import build_system_prompt, get_summary_prompt, get_screen_specific_prompt, get_chat_response_prompt
from pyAIAgent.game.hints import get_area_hint
from core.client_setup import setup_llm_client, parse_mode_arg, MODES
from scripts.benchmark import Benchmark
from core.client_setup import DEFAULT_MODE, ONE_IMAGE_PER_PROMPT, REASONING_ENABLED, USES_DEFAULT_TEMPERATURE, REASONING_EFFORT, IMAGE_DETAIL, USES_MAX_COMPLETION_TOKENS, MAX_TOKENS, TEMPERATURE, MINIMAP_ENABLED, MINIMAP_2D, SYSTEM_PROMPT_UNSUPPORTED
# from pyAIAgent.llm.zai_mcp_client import create_zai_vision_client # Removed, handled by VisionManager
from core.vision_manager import VisionManager
from core.memory.manager import MemoryManager
from core.battle_strategy import read_battle_state, choose_battle_action, get_battle_context
from trackers.goal_tracker import GoalTracker, GoalPriority, GoalStatus
from trackers.exploration_tracker import ExplorationTracker
from services.twitch_chat_service import TwitchChatService, create_twitch_service
from services.comfyui_tts_service import ComfyUITTSService, create_tts_service
from services.chat_response_service import ChatResponseService, create_chat_response_service, MessageDecision
from trackers.history_tracker import ScreenshotHistoryTracker
from trackers.coordinate_tracker import CoordinateTracker
from core.background_tasks import run_chat_background_task
from core.game_state_manager import parse_minimap
from core.llm_controller import LLMController

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('llmdriver')


ACTION_RE = re.compile(r'^[LRUDABSTt](?:;[LRUDABSTt])*;?')  # Match action at start, allow trailing text
COORD_RE = re.compile(r'^([0-9]),([0-8])$')
ANALYSIS_RE = re.compile(r"<game_analysis>([\s\S]*?)</game_analysis>", re.IGNORECASE)
IS_LOCAL = DEFAULT_MODE == "LMSTUDIO" or DEFAULT_MODE == "OLLAMA"






def translate_cardinal_to_buttons(action_str: str) -> str:
    """
    Translate cardinal directions (N/S/E/W) to game buttons (U/D/R/L).
    
    CRITICAL: 'S' is ambiguous - it's both 'South' AND 'START' button.
    We only translate S->D when other cardinal letters (N/E/W) are present,
    indicating the LLM meant directions, not the START button.
    """
    if not action_str:
        return action_str
    
    # Split into potential tokens to avoid replacing inside words (e.g. START -> DTART)
    tokens = action_str.replace(';', ' ; ').split()
    translated_tokens = []
    
    for token in tokens:
        upper_token = token.upper()
        # Direct cardinal translations
        if upper_token in ['NORTH', 'N']:
            translated_tokens.append('U')
        elif upper_token in ['EAST', 'E']:
            translated_tokens.append('R')
        elif upper_token in ['WEST', 'W']:
            translated_tokens.append('L')
        elif upper_token == 'SOUTH': # Explicit SOUTH -> DOWN
            translated_tokens.append('D')
        elif upper_token == 'S': 
             # Ambiguous 'S'. If context suggests directions, maybe? 
             # But user said: "if we detect that it tried to do 'SOUTH' then we deterministicaly translate to DOWN... we didn't want it to do 'S' which is Start by accident"
             # So 'S' should remain 'S' (Start/Select) unless it explicitly wrote SOUTH.
             # Ideally the LLM shouldn't write SOUTH. If it does, we map to D.
             # If it writes 'S', we assume it means 'S' button (Start/Select handling elsewhere or handled by mGBA as S=Start?)
             # Actually, checking `input_map`: S usually maps to Start? Or Select?
             # Let's keep S as S.
             translated_tokens.append('S')
        elif upper_token == 'DOWN':
             translated_tokens.append('D')
        elif upper_token == 'UP':
             translated_tokens.append('U')
        elif upper_token == 'LEFT':
             translated_tokens.append('L')
        elif upper_token == 'RIGHT':
             translated_tokens.append('R')
        else:
            translated_tokens.append(token)
            
    # Rejoin
    result = "".join(translated_tokens)
    # Fix spacing if we added too many spaces around semicolons, though `send_command` handles spaces fine usually.
    # But let's be clean.
    result = result.replace(' ; ', ';')
    
    if result != action_str:
        log.info(f"🔄 Translated cardinal directions: {action_str} -> {result}")
    
    return result


if(IS_LOCAL):
    # Reduced for faster cycles
    STREAM_TIMEOUT = 30
else:
    STREAM_TIMEOUT = 30

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
    global client, MODEL, supports_reasoning, vision_manager
    client, MODEL, supports_reasoning = setup_llm_client(CURRENT_MODE)

    # Initialize VisionManager if using ZAI mode
    global vision_manager
    vision_manager = None
    if CURRENT_MODE == "ZAI" and client:
        vision_manager = VisionManager(client, MODEL, enabled=True)

# Note: CURRENT_MODE should be set by set_current_mode() before using any llmdriver functions
# This prevents duplicate mode selection prompts

# Initialize variables (will be set properly in set_current_mode)
client = None
MODEL = None
supports_reasoning = False
vision_manager = None

# chat_history = [] (Moved to controller)
response_count = 0
action_count = 0
tokens_used_session = 0
start_time = datetime.datetime.now()

# Agent-requested ui_diff flag - Only run diff when agent asks for it
# This saves 10-20s per cycle when diff is not needed
agent_requested_diff = False

# Global status callback for real-time processing status updates
# Set by run_auto_loop, called by llm_stream_action during vision processing
_status_callback = None

def set_status_callback(callback):
    """Set the callback for processing status updates."""
    global _status_callback
    _status_callback = callback

def update_processing_status(status: str):
    """Update the processing status via callback if set."""
    if _status_callback:
        try:
            _status_callback(status)
        except Exception as e:
            log.warning(f"Status callback error: {e}")





# ─── Constants ────────────────────────────────────────────────────────────────
LLM_TOTAL_TIMEOUT = 75  # Extended to 75s cycle timeout

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


def save_game_state(sock, slot: int = 0) -> bool:
    """Save game state. slot=0 uses QUICKSAVE (faster), slot>0 uses regular SAVESTATE."""
    try:
        if slot == 0:
            # Use QUICKSAVE for faster saves
            response = send_command(sock, "QUICKSAVE")
            if response and "OK" in response:
                log.info(f"💾 Game state quicksaved")
                return True
            else:
                log.warning(f"Failed to quicksave: {response}")
                return False
        else:
            response = send_command(sock, f"SAVESTATE {slot}")
            if response and "OK" in response:
                log.info(f"💾 Game state saved to slot {slot}")
                return True
            else:
                log.warning(f"Failed to save game state to slot {slot}: {response}")
                return False
    except Exception as e:
        log.error(f"Error saving game state: {e}")
        return False


def backup_save_state():
    """Copy current save state file to backup. Previous save becomes backup."""
    rom_path = get_rom_path()
    rom_dir = os.path.dirname(rom_path)
    rom_name = os.path.splitext(os.path.basename(rom_path))[0]
    
    save_file = os.path.join(rom_dir, f"{rom_name}.ss1")
    backup_file = os.path.join(rom_dir, f"{rom_name}-backup.ss1")
    
    if os.path.exists(save_file):
        try:
            shutil.copy2(save_file, backup_file)
            log.info(f"📦 Backup created: {backup_file}")
            return True
        except Exception as e:
            log.error(f"Failed to create backup: {e}")
            return False
    return False




async def run_auto_loop(sock, state: dict, broadcast_func, interval: float = 10.0, max_loops = math.inf, benchmark: Benchmark = None, persistence = None, run_state = None, mgba_proc = None):
    """Main async loop: Get state, call LLM, send action, update/broadcast state.
    
    Args:
        mgba_proc: The mGBA subprocess - needed for auto-restart on failures for 24/7 operation.
    """
    global action_count, tokens_used_session, start_time, SCREENSHOT_PATH, MINIMAP_PATH, SAVED_SCREENSHOT_PATH, SAVED_MINIMAP_PATH
    
    cycle_count = 0
    
    # Track if we're resuming a run - don't increment cycle on first iteration
    # because the restored cycle was interrupted and should be completed first
    is_first_cycle_after_continue = False

    # Restore state from persistence if available
    if run_state and run_state.action_count > 0:
        cycle_count = run_state.cycle_count
        action_count = run_state.action_count
        tokens_used_session = run_state.tokens_used
        # Restore elapsed time by adjusting start_time
        start_time = datetime.datetime.now() - datetime.timedelta(seconds=run_state.elapsed_seconds)
        # Restore chat history logic deferred
        restored_history = run_state.chat_history if run_state and run_state.chat_history else []
        if restored_history:
             log.info(f"🔄 Found persistent chat history: {len(restored_history)} messages")
             
        log.info(f"🔄 Restored from persistence: cycle={cycle_count}, actions={action_count}, tokens={tokens_used_session}")
        # Flag to skip cycle increment on first loop iteration
        is_first_cycle_after_continue = True

    # Initialize memory manager - persist memories when continuing a run
    is_continuing_run = run_state and run_state.action_count > 0
    memory_manager = MemoryManager(reset_on_start=not is_continuing_run)
    if is_continuing_run:
        log.info("📝 Memory manager: Loaded existing memories (continuing run)")
    else:
        log.info("📝 Memory manager: Fresh start (new run)")

    # Initialize goal tracker
    goal_tracker = GoalTracker()
    if not goal_tracker.goals:
        goal_tracker.initialize_default_goals()
    log.info("Goal tracker initialized")

    # Initialize exploration tracker - persist when continuing a run
    exploration_tracker = ExplorationTracker(reset_on_start=not is_continuing_run)
    if is_continuing_run:
        log.info(f"🗺️ Exploration tracker: Loaded existing data ({len(exploration_tracker.maps)} maps)")
    else:
        log.info("🗺️ Exploration tracker: Fresh start")

    # Initialize screenshot history tracker for ui_diff_check (keeps N through N-4)
    screenshot_history = ScreenshotHistoryTracker(snapshot_dir="snapshots", max_history=5)
    log.info("📸 Screenshot history tracker initialized (5 cycles for multi-diff)")

    # Initialize coordinate tracker for loop detection and target tracking
    coord_tracker = CoordinateTracker(
        storage_path="data/coordinate_history.json",
        max_history=10,
        reset_on_start=not is_continuing_run
    )
    log.info(f"📍 Coordinate tracker initialized (history: {coord_tracker.get_context_summary()[:100] if coord_tracker.history else 'empty'})")

    # Capture the main event loop for thread-safe callbacks
    # This MUST be done before defining callbacks that will run in executor threads
    loop = asyncio.get_running_loop()
    
    # Define thread-safe status callback for vision updates (called from executor threads)
    # Uses run_coroutine_threadsafe because LLMController.stream_action runs in ThreadPoolExecutor
    def status_callback(status: str):
        state["processingStatus"] = status
        asyncio.run_coroutine_threadsafe(broadcast_func({"processingStatus": status}), loop)
    
    set_status_callback(status_callback)
    log.info("📢 Processing status callback initialized (thread-safe)")

    # Initialize LLM Controller - encapsulates all LLM interaction logic
    llm_config = {
        "mode": CURRENT_MODE,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "is_local": IS_LOCAL,
        "reasoning_enabled": REASONING_ENABLED,
        "reasoning_effort": REASONING_EFFORT,
        "uses_default_temp": USES_DEFAULT_TEMPERATURE,
        "uses_max_completion_tokens": USES_MAX_COMPLETION_TOKENS,
        "minimap_enabled": MINIMAP_ENABLED,
        "minimap_2d": MINIMAP_2D,
        "cleanup_window": CLEANUP_WINDOW,
        "system_prompt_unsupported": SYSTEM_PROMPT_UNSUPPORTED,
        "supports_reasoning": supports_reasoning
    }
    controller = LLMController(client, vision_manager, memory_manager, llm_config)
    controller.set_status_callback(status_callback)
    log.info("🤖 LLM Controller initialized")

    # Initialize Twitch chat service (optional - gracefully disabled if not configured)
    twitch_service = create_twitch_service()
    if twitch_service.is_available:
        try:
            await twitch_service.start()
            log.info("📺 Twitch chat service started")
        except Exception as e:
            log.warning(f"Failed to start Twitch chat service: {e}")
    else:
        log.info("📺 Twitch chat service not configured (set TWITCH_* env vars to enable)")

    # Initialize ComfyUI TTS service (optional - gracefully disabled if not configured)
    # Create callback to notify UI when TTS starts playing (for synchronized typewriter)
    async def on_tts_playback_start(text: str, duration_ms: int):
        """Called when TTS audio is about to start playing. Broadcasts to UI for sync."""
        log.info(f"🔊 Broadcasting TTS playback start: {len(text)} chars, {duration_ms}ms")
        try:
            await broadcast_func({
                "tts_commentary": {
                    "text": text,
                    "duration_ms": duration_ms,
                    "playing": True
                }
            })
        except Exception as e:
            log.warning(f"Failed to broadcast TTS playback start: {e}")
    
    tts_service = create_tts_service(on_playback_start=on_tts_playback_start)
    if tts_service.is_available:
        is_connected = await tts_service.check_connection()
        if is_connected:
            log.info(f"🔊 ComfyUI TTS service connected: {tts_service.base_url}")
        else:
            log.warning(f"🔊 ComfyUI TTS not reachable at {tts_service.base_url} (will retry when needed)")
    else:
        log.info("🔊 ComfyUI TTS service not configured (set COMFYUI_URL in .env to enable)")

    # Initialize Chat Response service (uses Featherless AI / Alkahest for chat responses)
    chat_response_service = create_chat_response_service()
    if chat_response_service.is_available:
        log.info(f"💬 Chat response service configured: {chat_response_service.model}")
    else:
        log.info("💬 Chat response service not configured (set FEATHERLESS_* env vars to enable)")

    # Helper function to generate a chat response via the dedicated chat LLM
    async def generate_chat_response(username: str, message: str, is_past: bool = False) -> str:
        """Generate a response to a Twitch chat message using the chat response service."""
        if chat_response_service.is_available:
            return await chat_response_service.generate_response(username, message, is_past)
        
        # Fallback to main LLM if chat service not available
        try:
            prompt = get_chat_response_prompt(username, message, is_past)
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.9
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return ""
        except Exception as e:
            log.error(f"Error generating chat response: {e}")
            return ""


    # Position history for stuck detection
    position_history = []
    
    # Track last action for failure replay
    last_action = None
    last_position = None

    b64_mm = None

    # Persistence save interval (save every N cycles)
    PERSIST_INTERVAL = 5
    cycles_since_persist = 0
    
    # Track previous cycle time for UI display
    prev_cycle_time_s = 0.0
    cycle_times_history = []  # List of recent cycle times for average calculation
    
    # mGBA timeout - if no response in this time, restart the cycle
    # INCREASED from 5s to 15s - screenshot capture can take 4+ seconds after restart
    # and thread race conditions caused false timeouts when old threads kept running
    MGBA_TIMEOUT = 35  # seconds - must exceed socket timeout (30s) to let prep_llm complete/fail naturally

    benchInstructions = ""
    if benchmark is not None:
        benchInstructions = benchmark.instructions
        logging.info(f"Added bench instructions: {benchInstructions}")
    
    # Always use fresh system prompt (in case prompts.py was updated)
    fresh_system_prompt = build_system_prompt("", benchInstructions)
    
    if run_state and run_state.chat_history:
        # Get the old system prompt from persisted history
        old_system_prompt = ""
        if run_state.chat_history and run_state.chat_history[0].get("role") == "system":
            old_system_prompt = run_state.chat_history[0].get("content", "")
        
        # Check if prompt format has changed by looking for key structural changes
        # We check for the COMMENTARY section format which changed from section 8/9 to section 7
        old_has_commentary_7 = "7. COMMENTARY" in old_system_prompt and "REQUIRED" in old_system_prompt
        new_has_commentary_7 = "7. COMMENTARY" in fresh_system_prompt and "REQUIRED" in fresh_system_prompt
        prompt_format_changed = old_has_commentary_7 != new_has_commentary_7
        
        if prompt_format_changed:
            # Prompt format changed - start fresh to avoid LLM following old patterns
            log.info("🔄 PROMPT FORMAT CHANGED - Clearing chat history to adopt new format")
            controller.chat_history = [{"role": "system", "content": fresh_system_prompt}]
        else:
            # Restore chat history but replace the system prompt with fresh one
            controller.chat_history = restored_history
            if controller.chat_history and controller.chat_history[0].get("role") == "system":
                controller.chat_history[0] = {"role": "system", "content": fresh_system_prompt}
                log.info("🔄 Updated system prompt to latest version")
    else:
        controller.chat_history = [{"role": "system", "content": fresh_system_prompt}]

    # Track consecutive mGBA failures across cycle retries
    # This persists across loop iterations so we can detect when mGBA is completely dead
    consecutive_mgba_failures = 0
    # Reduced to 3 - mGBA Lua socket callbacks may occasionally timeout
    # but if it fails 3 times in a row, it's likely frozen
    MAX_CONSECUTIVE_FAILURES = 3  # Restart mGBA after 3 consecutive failures
    RECONNECT_THRESHOLD = 3  # Skip socket reconnection - go straight to restart
    
    # Use mutable containers for socket and process so restarts update all references
    sock_ref = {"socket": sock}
    proc_ref = {"proc": mgba_proc}
    
    # Socket lock to prevent race condition where old ThreadPoolExecutor threads
    # continue using the socket after asyncio timeout, corrupting data for new threads.
    # ThreadPoolExecutor doesn't cancel running threads on timeout - they keep running!
    socket_lock = threading.Lock()
    
    def prep_llm_locked(sock):
        """Wrapper that acquires lock before accessing socket.
        
        This prevents race conditions where an old prep_llm thread (that didn't
        get cancelled by asyncio timeout) corrupts socket data for new calls.
        """
        with socket_lock:
            return prep_llm(sock)
    
    # Import config for mGBA paths
    import config
    
    def restart_mgba(port=8888):
        """
        Kill and restart the entire mGBA process for 24/7 autonomous operation.
        This is called when socket reconnection fails - mGBA Lua script is probably frozen.
        """
        nonlocal sock_ref, proc_ref
        log.warning("🔄 RESTARTING MGBA PROCESS (Lua script may be frozen)...")
        
        # 1. Close old socket
        try:
            sock_ref["socket"].close()
            log.info("🔌 Old socket closed")
        except Exception as e:
            log.warning(f"Error closing old socket: {e}")
        
        # 2. Kill old process
        if proc_ref["proc"] and proc_ref["proc"].poll() is None:
            try:
                proc_ref["proc"].terminate()
                proc_ref["proc"].wait(timeout=5)
                log.info("💀 Old mGBA process terminated")
            except subprocess.TimeoutExpired:
                log.warning("mGBA didn't terminate gracefully, killing...")
                proc_ref["proc"].kill()
                proc_ref["proc"].wait()
            except Exception as e:
                log.error(f"Error terminating mGBA: {e}")
        
        # 3. Wait a moment for cleanup
        time.sleep(2)
        
        # 4. Start new mGBA process
        rom_path = get_rom_path()
        # Construct path to slot 1 save state (e.g. roms/red.gb -> roms/red.ss1)
        # Using CLI load avoids the socket LOADSTATE pause/freeze issue
        import os
        ss1_path = os.path.splitext(rom_path)[0] + ".ss1"
        
        cmd = [config.MGBA_EXE, '--script', config.LUA_SCRIPT]
        
        # If save state exists, load it via CLI
        if os.path.exists(ss1_path):
            log.info(f"Using CLI to load save state: {ss1_path}")
            cmd.extend(['-t', ss1_path])
        else:
            log.warning(f"Save state not found at {ss1_path}, starting fresh")
            
        cmd.append(rom_path)
        
        log.info(f"Starting new mGBA: {' '.join(cmd)}")
        try:
            proc_ref["proc"] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        except Exception as e:
            log.error(f"Failed to start mGBA: {e}")
            return False
        
        # 5. Wait for mGBA to initialize
        log.info("⏳ Waiting for mGBA to initialize...")
        time.sleep(4)
        
        # Check if mGBA started successfully
        if proc_ref["proc"].poll() is not None:
            log.error(f"mGBA exited immediately with code {proc_ref['proc'].returncode}")
            return False
        
        # 6. Connect to new socket
        import socket as sock_module
        for attempt in range(5):
            try:
                new_sock = sock_module.create_connection(('localhost', port), timeout=5)
                new_sock.setblocking(True)
                new_sock.settimeout(30.0)
                sock_ref["socket"] = new_sock
                log.info(f"✅ Connected to new mGBA socket (fd={new_sock.fileno()})")
                break
            except Exception as e:
                log.warning(f"Socket connection attempt {attempt+1}/5 failed: {e}")
                time.sleep(1)
        else:
            log.error("Failed to connect to new mGBA socket after 5 attempts")
            return False
        
        # 7. Load save state (SKIPPED - handled via CLI to prevent freeze)
        # try:
        #     response = send_command(sock_ref["socket"], "LOADSTATE 1")
        #     if response and "OK" in response:
        #         log.info("✅ Save state loaded successfully!")
        #     else:
        #         log.warning(f"Save state load response: {response}")
        # except Exception as e:
        #     log.error(f"Failed to load save state: {e}")
        
        # 8. Enable input display
        try:
            send_command(sock_ref["socket"], "INPUT_DISPLAY_ON")
        except:
            pass
        
        log.info("🎮 MGBA RESTART COMPLETE - Resuming game loop!")
        return True
    
    def reconnect_socket(port=8888):
        """Attempt to reconnect to mGBA socket. Updates sock_ref in place."""
        nonlocal sock_ref
        log.warning("🔌 Attempting to reconnect to mGBA socket...")
        import socket as sock_module
        try:
            # Close old socket cleanly
            try:
                sock_ref["socket"].close()
            except:
                pass
            
            # Try to create a new connection
            time.sleep(1)  # Give mGBA time to clean up
            new_sock = sock_module.create_connection(('localhost', port), timeout=5)
            new_sock.setblocking(True)
            new_sock.settimeout(30.0)  # Set default timeout to prevent indefinite blocking
            sock_ref["socket"] = new_sock  # Update the shared reference
            log.info(f"✅ Successfully reconnected to mGBA socket! (new fd={new_sock.fileno()})")
            return True
        except Exception as e:
            log.error(f"❌ Failed to reconnect to mGBA: {e}")
            return False
    
    def check_socket_health():
        """Quick check if socket is still valid before operations."""
        try:
            fd = sock_ref["socket"].fileno()
            if fd < 0:
                log.warning(f"🔌 Socket fd is invalid ({fd})")
                return False
            return True
        except Exception as e:
            log.warning(f"🔌 Socket health check failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # STARTUP INTRO CYCLE
    # Play an intro/reconnection message before the first real game cycle
    # This gives mGBA time to fully load and sets the stream mood
    # ═══════════════════════════════════════════════════════════════════════════
    if tts_service and tts_service.is_available:
        try:
            # Determine intro message based on whether we're continuing or starting fresh
            if is_first_cycle_after_continue:
                intro_text = "Hey everyone! Lass is back! Had some connection issues but I'm ready to continue my Pokemon adventure!"
            else:
                intro_text = "Hey chat! It's Lass! Welcome to my Pokemon Red stream! Let's catch some Pokemon and become the very best!"
            
            log.info(f"🎬 Playing startup intro: {intro_text[:50]}...")
            
            # Broadcast a status update so UI shows something
            await broadcast_func({
                "processingStatus": "STARTING STREAM...",
                "response_log": {"id": 0, "text": intro_text, "is_response": True, "timestamp": int(time.time() * 1000)}
            })
            
            # Play the intro TTS and wait for it to complete
            await tts_service.synthesize_and_play(
                intro_text,
                priority=tts_service.PRIORITY_COMMENTARY,
                wait=True
            )
            log.info("✅ Startup intro complete, beginning first cycle")
            
            # Clear processing status
            await broadcast_func({"processingStatus": ""})
            
        except Exception as e:
            log.warning(f"Startup intro failed: {e}")
    
    # Broadcast session start time - this is when cycles actually begin
    # UI will use this to start the session timer and enable cycle tracking
    session_start_ms = int(time.time() * 1000)
    await broadcast_func({
        "sessionStartTime": session_start_ms,
        "cyclesEnabled": True  # UI can now start tracking cycles
    })
    log.info(f"📊 Session started at {session_start_ms}")
    
    # Small delay to let mGBA fully settle
    await asyncio.sleep(1)

    while action_count < max_loops:
        loop_start_time = time.time()
        
        # Skip cycle increment on first iteration when continuing a run
        # The restored cycle was interrupted and should be completed first
        if is_first_cycle_after_continue:
            is_first_cycle_after_continue = False
            log.info(f"🔄 Resuming interrupted cycle {cycle_count}")
        else:
            cycle_count += 1
        current_cycle = cycle_count
        log.info(f"--- Loop Cycle {current_cycle} ---")
        
        # CRITICAL: Always sync cycle/action count to run_state for graceful shutdown
        # This ensures Ctrl+C saves the correct state even between PERSIST_INTERVAL saves
        if run_state:
            run_state.cycle_count = cycle_count
            run_state.action_count = action_count
        
        # Broadcast cycle count immediately
        update_payload = {"cycle": current_cycle}
        await broadcast_func({"cycle": current_cycle})  # Actually broadcast immediately
        action_payload = {}
        
        # Performance metrics container
        cycle_metrics = {"mGBA": 0.0, "vision": 0.0, "diff": 0.0, "llm": 0.0, "cycle": 0.0}
        
        # Track true cycle start time (persists across restarts within same cycle)
        true_cycle_start = time.time()
        
        # Initialize result to prevent NameError if loop breaks early
        result = None

        try:
            log.info("Requesting game state from mGBA...")
            t_mgba_start = time.time()
            
            # Check socket health before attempting prep_llm
            if not check_socket_health():
                log.warning("🔌 Socket unhealthy before prep_llm, attempting reconnection...")
                if reconnect_socket():
                    log.info("✅ Socket reconnected before prep_llm")
                else:
                    consecutive_mgba_failures += 1
                    if consecutive_mgba_failures >= MAX_CONSECUTIVE_FAILURES:
                        log.warning(f"🔄 mGBA unresponsive after {MAX_CONSECUTIVE_FAILURES} failures - attempting full restart...")
                        if restart_mgba():
                            consecutive_mgba_failures = 0  # Reset counter after successful restart
                            log.info("✅ mGBA restarted! Continuing 24/7 operation.")
                        else:
                            log.error("❌ mGBA restart failed! Waiting 30s before retry...")
                            await asyncio.sleep(30)
                    cycle_count -= 1
                    await asyncio.sleep(2)
                    continue
            
            # Wrap prep_llm in async timeout to prevent indefinite blocking
            # Use sock_ref["socket"] to ensure we use the current socket (may be reconnected)
            # Use prep_llm_locked to prevent race condition with old threads
            loop = asyncio.get_event_loop()
            current_socket = sock_ref["socket"]  # Capture current socket for executor
            try:
                current_mGBA_state = await asyncio.wait_for(
                    loop.run_in_executor(None, prep_llm_locked, current_socket),
                    timeout=MGBA_TIMEOUT
                )
            except asyncio.TimeoutError:
                mgba_duration = time.time() - t_mgba_start
                consecutive_mgba_failures += 1
                log.error(f"⏱️ mGBA TIMEOUT after {mgba_duration:.1f}s (limit: {MGBA_TIMEOUT}s) - Retrying same cycle ({consecutive_mgba_failures}/{MAX_CONSECUTIVE_FAILURES})")
                cycle_metrics["mGBA"] = mgba_duration * 1000  # Store in ms for consistency
                
                # Try to reconnect socket after RECONNECT_THRESHOLD failures
                if consecutive_mgba_failures == RECONNECT_THRESHOLD:
                    log.warning(f"🔌 Socket may be dead after {RECONNECT_THRESHOLD} failures. Attempting reconnection...")
                    if reconnect_socket():
                        log.info("✅ Socket reconnected! Continuing cycle retries...")
                    else:
                        log.error("❌ Socket reconnection failed. Will keep trying...")
                
                # Check if mGBA is completely dead - trigger restart
                if consecutive_mgba_failures >= MAX_CONSECUTIVE_FAILURES:
                    log.warning(f"🔄 mGBA unresponsive after {MAX_CONSECUTIVE_FAILURES} failures - attempting full restart...")
                    if restart_mgba():
                        consecutive_mgba_failures = 0  # Reset counter after successful restart
                        log.info("✅ mGBA restarted! Continuing 24/7 operation.")
                    else:
                        log.error("❌ mGBA restart failed! Waiting 30s before retry...")
                        await asyncio.sleep(30)
                
                # Decrement cycle_count to retry the same cycle number (it was incremented at loop start)
                cycle_count -= 1
                await asyncio.sleep(2)  # Brief pause before retry
                continue
            
            mgba_duration = time.time() - t_mgba_start
            cycle_metrics["mGBA"] = mgba_duration * 1000  # Store in ms
            log.info(f"⏱️ mGBA Response: {mgba_duration:.2f}s")
            
            # Reset failure counter on success
            consecutive_mgba_failures = 0

            if benchmark is not None:
                # check if we complted the bench
                if(benchmark.validation(current_mGBA_state)):
                    break

            #print(str(current_mGBA_state))
            if not current_mGBA_state:
                consecutive_mgba_failures += 1
                log.error(f"Failed to get state from mGBA (prep_llm returned None). Retrying same cycle ({consecutive_mgba_failures}/{MAX_CONSECUTIVE_FAILURES}).")
                
                if consecutive_mgba_failures >= MAX_CONSECUTIVE_FAILURES:
                    log.warning(f"🔄 mGBA unresponsive - attempting full restart...")
                    if restart_mgba():
                        consecutive_mgba_failures = 0
                        log.info("✅ mGBA restarted! Continuing 24/7 operation.")
                    else:
                        await asyncio.sleep(30)
                
                cycle_count -= 1  # Retry same cycle number
                await asyncio.sleep(max(0, interval - (time.time() - loop_start_time)))
                continue
            log.info("Received game state from mGBA.")
            
            # --- ATOMIC SNAPSHOT LOGIC ---
            # Create a unique snapshot for this cycle to prevent race conditions (Vision vs UI sync)
            os.makedirs("snapshots", exist_ok=True)
            snapshot_path = f"snapshots/cycle_{current_cycle}.png"
            # Ensure we are copying the fresh capture
            try:
                shutil.copyfile(SAVED_SCREENSHOT_PATH, snapshot_path)
                SCREENSHOT_PATH = snapshot_path
                log.info(f"🔒 Atomic snapshot locked: {snapshot_path}")
                
                # Register with history tracker - this keeps N and N-1, auto-cleans N-2+
                screenshot_history.add_screenshot(current_cycle, snapshot_path)
            except Exception as e:
                log.error(f"Failed to create atomic snapshot: {e}. Falling back to global path.")
                SCREENSHOT_PATH = SAVED_SCREENSHOT_PATH
        except socket.timeout:
             consecutive_mgba_failures += 1
             log.error(f"Socket timeout getting state from mGBA ({consecutive_mgba_failures}/{MAX_CONSECUTIVE_FAILURES}). Retrying...")
             
             if consecutive_mgba_failures >= MAX_CONSECUTIVE_FAILURES:
                 log.warning(f"🔄 mGBA unresponsive - attempting full restart...")
                 if restart_mgba():
                     consecutive_mgba_failures = 0
                 else:
                     await asyncio.sleep(30)
             
             cycle_count -= 1  # Retry same cycle
             await asyncio.sleep(2)  # Brief pause before retry
             continue
        except socket.error as se:
             consecutive_mgba_failures += 1
             log.error(f"Socket error getting state from mGBA: {se} ({consecutive_mgba_failures}/{MAX_CONSECUTIVE_FAILURES}). Retrying...")
             
             if consecutive_mgba_failures >= MAX_CONSECUTIVE_FAILURES:
                 log.warning(f"🔄 mGBA unresponsive - attempting full restart...")
                 if restart_mgba():
                     consecutive_mgba_failures = 0
                 else:
                     await asyncio.sleep(30)
             
             cycle_count -= 1  # Retry same cycle
             await asyncio.sleep(2)  # Brief pause before retry
             continue
        except Exception as e:
            consecutive_mgba_failures += 1
            log.error(f"Error getting state from mGBA: {e} - Retrying same cycle ({consecutive_mgba_failures}/{MAX_CONSECUTIVE_FAILURES})", exc_info=True)
            
            if consecutive_mgba_failures >= MAX_CONSECUTIVE_FAILURES:
                log.warning(f"🔄 mGBA unresponsive - attempting full restart...")
                if restart_mgba():
                    consecutive_mgba_failures = 0
                else:
                    await asyncio.sleep(30)
            
            cycle_count -= 1  # Retry same cycle number
            await asyncio.sleep(max(0, interval - (time.time() - loop_start_time)))
            continue

        llm_input_state = copy.deepcopy(current_mGBA_state)
        
        # REMOVE raw minimap_2d - LLM should use pre-computed minimap_analysis instead
        # This prevents LLM from doing its own buggy parsing
        if "minimap_2d" in llm_input_state:
            del llm_input_state["minimap_2d"]
        
        state_update_start = time.time()
        
        # Track position for stuck detection
        current_pos = current_mGBA_state.get('position')
        current_map = current_mGBA_state.get('map_id')
        stuck_info = {"is_stuck": False, "suggestion": ""}  # Default if no position data
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
                
                # Use the stuck_position from detection (more accurate than current_pos for patterns)
                map_name_for_decay = current_mGBA_state.get('map_name', '')
                stuck_pos = stuck_info.get("stuck_position")
                if stuck_pos and map_name_for_decay:
                    # stuck_pos is a tuple like (map_id, (x, y)), extract coordinates
                    if isinstance(stuck_pos, tuple) and len(stuck_pos) >= 2:
                        coords_to_decay = list(stuck_pos[1]) if isinstance(stuck_pos[1], tuple) else list(stuck_pos)
                    else:
                        coords_to_decay = list(current_pos) if current_pos else None
                    
                    if coords_to_decay:
                        # NEW: record_failed_exit_attempt now returns dict with status
                        failure_result = memory_manager.record_failed_exit_attempt(
                            map_name_for_decay, 
                            coords_to_decay
                        )
                        
                        # Append the suggestion to stuck_warning
                        if failure_result.get("suggestion"):
                            llm_input_state["stuck_warning"] += f" {failure_result['suggestion']}"
                        
                        # If there are untried directions, emphasize them
                        untried = failure_result.get("untried_directions", [])
                        if untried and failure_result.get("status") == "try_different_direction":
                            llm_input_state["stuck_warning"] += f" 🧭 TRY APPROACHING FROM: {untried[0]}"
        
        # Add memory context to LLM input
        map_name = current_mGBA_state.get('map_name', '')
        memory_context = memory_manager.get_context_for_llm(map_name)
        if memory_context:
            llm_input_state["memory_context"] = memory_context
            log.info(f"📝 Memory context: {memory_context[:100]}...")
        
        # Add NPC avoidance context (only if map_name is available)
        if map_name:
            npc_context = memory_manager.get_npc_interaction_context(map_name)
            if npc_context:
                llm_input_state["npc_warning"] = npc_context
                log.info(f"🚫 NPC context: {npc_context}")
        
        # Add learned strategies context
        # Build situation string from current state for relevance matching
        situation_keywords = []
        party = current_mGBA_state.get('party', [])
        if party:
            total_hp = sum(p.get('hp', 0) for p in party if isinstance(p, dict))
            max_hp = sum(p.get('max_hp', 1) for p in party if isinstance(p, dict))
            if max_hp > 0 and total_hp / max_hp < 0.3:
                situation_keywords.append("low HP")
            if all(p.get('hp', 0) == 0 for p in party if isinstance(p, dict)):
                situation_keywords.append("fainted")
        if stuck_info.get("is_stuck"):
            situation_keywords.append("stuck")
            situation_keywords.append("lost")
        situation_str = " ".join(situation_keywords) if situation_keywords else map_name
        
        strategy_context = memory_manager.get_strategy_context_for_llm(situation_str)
        if strategy_context:
            llm_input_state["strategy_hints"] = strategy_context
            log.info(f"💡 Strategy context: {strategy_context[:80]}...")
        
        # Track exploration and add context
        map_id = current_mGBA_state.get('map_id', 0)
        pos = current_mGBA_state.get('position', [0, 0])
        minimap_2d = current_mGBA_state.get('minimap_2d', '')
        
        if pos and len(pos) >= 2:
            # Record this tile as visited
            # NEW: Calculate total walkable tiles in the local minimap/window to allow % calculation
            total_walkable = 0
            if minimap_2d:
                 # Count walkable chars found in typical minimap string
                 # is_walkable(tile) usually includes: W, P, O, D, E, >, <, ^, v
                 # We simply count chars that are in this set
                 for char in minimap_2d:
                     if char in ['W', 'P', 'O', 'D', 'E', '>', '<', '^', 'v']:
                         total_walkable += 1
                         
            exploration_tracker.record_visit(map_id, map_name, pos[0], pos[1], total_walkable=total_walkable)
            
            # Add exploration context to LLM input
            exploration_context = exploration_tracker.get_context_for_llm(
                map_id, map_name, pos[0], pos[1], minimap_2d
            )
            if exploration_context:
                llm_input_state["exploration_context"] = exploration_context
                log.info(f"🗺️ Exploration: {exploration_context.split(chr(10))[0]}")
            
            # Track coordinates for loop detection and navigation progress
            coord_tracker.add_position(current_cycle, pos[0], pos[1], map_name)
            
            # Check for loops and add warning to LLM
            loop_warning = coord_tracker.detect_loop()
            if loop_warning:
                llm_input_state["loop_warning"] = loop_warning
                log.warning(f"⚠️ {loop_warning}")
            
            # Add target progress context
            target_progress = coord_tracker.get_progress_toward_target()
            if target_progress.get("has_target"):
                llm_input_state["navigation_target"] = target_progress
                log.info(f"🎯 Target: {target_progress.get('progress', 'unknown')} - {target_progress.get('recommendation', '')[:60]}")
            
            # Check if target reached
            if coord_tracker.check_target_reached():
                log.info("✅ Navigation target reached!")
            
            # Add full coordinate history context to help LLM understand movement patterns
            coord_context = coord_tracker.get_context_summary()
            if coord_context:
                llm_input_state["coordinate_history"] = coord_context
                log.info(f"📍 Coord context: {len(coord_tracker.history)} positions tracked")
        
        # Add pre-computed minimap analysis to reduce LLM hallucination
        if minimap_2d:
            # Pass world position for coordinate conversion
            world_pos = current_mGBA_state.get('position', [])
            minimap_analysis = parse_minimap(minimap_2d, world_position=world_pos)
            if minimap_analysis and "error" not in minimap_analysis:
                # Format as VERY CLEAR human-readable string for LLM
                # Make blocked directions VERY obvious
                blocked = minimap_analysis['blocked_directions']
                walkable = minimap_analysis['walkable_directions']
                exits = minimap_analysis['all_exit_tiles']
                adj = minimap_analysis['adjacent_tiles']
                passages = minimap_analysis.get('passages', [])
                npcs = minimap_analysis.get('npc_tiles', [])

                # Retrieve current exploration percentage for frontend display
                exp_map = exploration_tracker.maps.get(map_id)
                if exp_map:
                    # Set in state for persistence
                    state["explorationPct"] = exp_map.exploration_pct
                    # Add to update payload for frontend
                    update_payload["explorationPct"] = exp_map.exploration_pct
                    log.info(f"🌍 Exploration: {exp_map.exploration_pct:.1f}% ({len(exp_map.visited_tiles)}/{exp_map.total_walkable})")

                analysis_str = (
                    f"⚠️ MINIMAP DATA (USE THIS - DO NOT PARSE RAW MINIMAP!) ⚠️\n"
                    f"Grid: {minimap_analysis['grid_size']} | Player: {minimap_analysis['player_position']}\n"
                    f"═══════════════════════════════════════\n"
                    f"NORTH: {adj['north']} {'❌ BLOCKED!' if 'NORTH (U)' in blocked else '✓ walkable'}\n"
                    f"SOUTH: {adj['south']} {'❌ BLOCKED!' if 'SOUTH (D)' in blocked else '✓ walkable'}\n"
                    f"EAST:  {adj['east']} {'❌ BLOCKED!' if 'EAST (R)' in blocked else '✓ walkable'}\n"
                    f"WEST:  {adj['west']} {'❌ BLOCKED!' if 'WEST (L)' in blocked else '✓ walkable'}\n"
                    f"═══════════════════════════════════════\n"
                    f"🚫 BLOCKED MOVES: {blocked if blocked else 'NONE - all directions open'}\n"
                    f"✅ ALLOWED MOVES: {walkable}\n"
                    f"🚪 EXIT TILES: {exits if exits else 'None visible in current view'}\n"
                    f"🚶 NPCs: {npcs if npcs else 'None visible'}\n"
                    f"🌉 PASSAGES (paths through walls - might lead somewhere!): {chr(10).join(passages) if passages else 'None detected'}"
                )
                llm_input_state["minimap_data"] = analysis_str
                log.info(f"🗺️ Minimap: Player at {minimap_analysis['player_position']}, "
                        f"blocked: {blocked}, npcs: {len(npcs)}, passages: {len(passages)}")
                
                # Store grid dimensions for lassMarkings overlay positioning
                # Parse "21x19" format into separate width/height
                try:
                    grid_dims = minimap_analysis['grid_size'].split('x')
                    state['minimapGridSize'] = {
                        'width': int(grid_dims[0]),
                        'height': int(grid_dims[1])
                    }
                    update_payload['minimapGridSize'] = state['minimapGridSize']
                except (ValueError, IndexError):
                    pass  # Keep existing or default
                
                # === INVISIBLE OBSTACLE DETECTION ===
                # If stuck but minimap shows walkable directions, there might be an invisible NPC/object
                # BUT: Only suggest A-press if NOT at a map boundary (black edge)
                if stuck_info.get("is_stuck") and walkable:
                    # Get the direction(s) we've been trying to move
                    # Check if any walkable direction is actually blocked (invisible obstacle)
                    stuck_warning_lower = llm_input_state.get("stuck_warning", "").lower()
                    
                    # Check if player is facing a map boundary (black area)
                    # If so, don't suggest A-press - it's just the edge of the map
                    facing = current_mGBA_state.get('facing', 'down')
                    is_at_map_boundary = False
                    
                    # Check if the blocked direction matches a map edge
                    # Map boundaries are indicated by 'X' tiles in the minimap
                    if minimap_analysis and 'blocked' in minimap_analysis:
                        blocked_directions = minimap_analysis.get('blocked', [])
                        facing_to_dir = {'up': 'N', 'down': 'S', 'left': 'W', 'right': 'E'}
                        if facing_to_dir.get(facing) in blocked_directions:
                            is_at_map_boundary = True
                            log.info(f"📍 At map boundary facing {facing} - NOT an invisible obstacle")
                    
                    # Suggest A-press to interact with potential NPC/object ONLY if not at map boundary
                    if ("position unchanged" in stuck_warning_lower or "movement blocked" in stuck_warning_lower) and not is_at_map_boundary:
                        log.warning(f"👻 INVISIBLE OBSTACLE: Minimap shows walkable tiles but movement blocked. Try pressing A to interact!")
                        llm_input_state["invisible_obstacle_hint"] = (
                            "👻 INVISIBLE OBSTACLE DETECTED: The minimap shows walkable tiles ahead, "
                            "but you can't move. There may be an NPC or object blocking you that isn't shown. "
                            "TRY PRESSING 'A' to interact with the invisible obstacle. If dialogue appears, "
                            "press B to close it and try moving again."
                        )
                        
                        # Mark this location as potential NPC for Lass overlay
                        # The actual confirmation happens when vision detects dialogue
                        current_pos = current_mGBA_state.get('position', [])
                        if current_pos and len(current_pos) >= 2:
                            # Mark the tile in front based on facing direction
                            dx, dy = 0, 0
                            if facing == 'up': dy = -1
                            elif facing == 'down': dy = 1
                            elif facing == 'left': dx = -1
                            elif facing == 'right': dx = 1
                            
                            potential_npc_coords = [current_pos[0] + dx, current_pos[1] + dy]
                            # Store as potential NPC (will be confirmed if dialogue detected)
                            memory_manager.add_lass_marking(
                                map_name, potential_npc_coords, "N", confidence=0.5
                            )
        
        # Add battle context using game memory (more accurate than vision)
        try:
            inventory = current_mGBA_state.get('inventory', [])
            battle_context = get_battle_context(sock_ref["socket"], inventory=inventory)
            if battle_context:
                llm_input_state["battle_context"] = battle_context
                log.info(f"⚔️ Battle detected: {battle_context[:80]}...")
        except Exception as e:
            log.debug(f"Battle context error (not in battle): {e}")
        
        new_team = current_mGBA_state.get('party')
        prev_team = state.get('currentTeam', []) or []
        prev_team_size = len(prev_team) if prev_team else 0
        new_team_size = len(new_team) if new_team else 0
        
        # 🎉 MILESTONE DETECTION: First Pokemon obtained
        if prev_team_size == 0 and new_team_size > 0:
            log.info("🎉 MILESTONE DETECTED: First Pokemon obtained!")
            
            # Complete the starter goal
            if goal_tracker.complete_goal_by_keyword("first Pokemon"):
                log.info("✅ Goal auto-completed: Get first Pokemon")
            
            # Record in memory as a milestone event
            pokemon_name = new_team[0].get('name', 'Unknown') if new_team else 'Unknown'
            memory_manager.add_gameplay_memory(
                location=current_mGBA_state.get('map_name', 'unknown'),
                description=f"MILESTONE: Received starter Pokemon {pokemon_name} from Professor Oak",
                event_type="milestone",
                outcome="obtained_first_pokemon",
                pokemon_involved=[pokemon_name]
            )
            log.info(f"📝 Memory recorded: Obtained starter {pokemon_name}")
            
            # Record outcome for strategy learning
            memory_manager.record_outcome(
                "goal_complete",
                {"goal": "first_pokemon", "pokemon": pokemon_name},
                {"location": current_mGBA_state.get('map_name', 'unknown')}
            )
        
        # 🩺 HEALTH MONITORING: Detect blackouts and heals for strategy learning
        prev_party_hp = getattr(memory_manager, '_last_party_hp', None)
        if new_team:
            current_hp_total = sum(p.get('hp', 0) for p in new_team if isinstance(p, dict))
            current_hp_max = sum(p.get('max_hp', 1) for p in new_team if isinstance(p, dict))
            all_fainted = all(p.get('hp', 0) == 0 for p in new_team if isinstance(p, dict))
            
            # Detect blackout (all Pokemon fainted, then respawned with full health)
            if prev_party_hp is not None:
                was_all_fainted = prev_party_hp.get('all_fainted', False)
                prev_hp_total = prev_party_hp.get('total', 0)
                
                # Blackout detected: was fainted, now have HP
                if was_all_fainted and current_hp_total > 0:
                    memory_manager.record_outcome(
                        "blacked_out",
                        {"respawn_location": current_mGBA_state.get('map_name', 'unknown'),
                         "hp_restored": current_hp_total},
                        {"was_lost": stuck_info.get("is_stuck", False)}
                    )
                    log.info("💀 Blackout detected - recording as potential strategy")
                
                # Heal detected: significant HP increase without blackout
                elif current_hp_total > prev_hp_total * 1.5 and not was_all_fainted:
                    memory_manager.record_outcome(
                        "healed",
                        {"location": current_mGBA_state.get('map_name', 'unknown'),
                         "hp_before": prev_hp_total, "hp_after": current_hp_total},
                        {}
                    )
            
            # Store for next cycle
            memory_manager._last_party_hp = {
                'total': current_hp_total, 
                'max': current_hp_max,
                'all_fainted': all_fainted
            }
        
        # Build team context for LLM awareness (every cycle)
        team_pokemon_names = []
        if new_team and new_team_size > 0:
            for mon in new_team:
                name = mon.get('name', 'Unknown')
                level = mon.get('level', '?')
                team_pokemon_names.append(name)
            
            # Create detailed team summary for LLM
            team_details = []
            for mon in new_team:
                name = mon.get('name', 'Unknown')
                level = mon.get('level', '?')
                hp = mon.get('current_hp', '?')
                max_hp = mon.get('max_hp', '?')
                team_details.append(f"{name} Lv{level} ({hp}/{max_hp}HP)")
            llm_input_state["pokemon_team"] = f"YOUR TEAM ({new_team_size}/6): " + ", ".join(team_details)
            log.info(f"🎮 Team context added: {new_team_size} Pokemon")
        
        # Update goal context with team awareness
        goal_context = goal_tracker.get_context_for_llm(
            team_size=new_team_size, 
            team_pokemon=team_pokemon_names
        )
        if goal_context:
            llm_input_state["goal_context"] = goal_context
            # Log first line only to avoid spam
            log.info(f"🎯 Goals: {goal_context.split(chr(10))[0]}...")
        
        # Standard team state update
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
        
        # Always update minimap timestamp to trigger UI refresh (minimap image changes each cycle)
        minimap_ts = int(time.time() * 1000)
        state['minimapTimestamp'] = minimap_ts
        update_payload['minimapTimestamp'] = minimap_ts
        
        # Broadcast exploration percentage for current map
        if map_id in exploration_tracker.maps:
            exp_pct = exploration_tracker.maps[map_id].exploration_pct
            state['explorationPct'] = round(exp_pct, 1)
            update_payload['explorationPct'] = state['explorationPct']
        
        # Broadcast Lass markings for current map (N=NPC, O=Opening)
        lass_marks = memory_manager.get_lass_markings_for_map(map_name)
        if lass_marks:
            state['lassMarkings'] = lass_marks
            update_payload['lassMarkings'] = lass_marks

        # --- DYNAMIC AVATAR STATE UPDATES ---
        # Update Battle State (camelCase for frontend)
        battle_state = current_mGBA_state.get('battle_state')
        if battle_state:
            state['inBattle'] = battle_state.get('in_battle', False)
            state['battleType'] = battle_state.get('battle_type', None)
            
            update_payload['inBattle'] = state['inBattle']
            update_payload['battleType'] = state['battleType']
            
            if state['inBattle'] and state['battleType']:
                 # Only log change to avoid spam
                if state.get('_last_battle_type') != state['battleType']:
                    log.info(f"⚔️ Battle State: {state['battleType']}")
                    state['_last_battle_type'] = state['battleType']
        
        # Update Text/Dialog State for Speaking Avatar
        text_state = current_mGBA_state.get('text_state')
        if text_state:
             state['textState'] = text_state
             update_payload['textState'] = state['textState']
             
        # Update Menu State (simple heuristic for now)
        menu_state = current_mGBA_state.get('menu_state')
        if menu_state:
            # If menu item count > 0, we can assume a menu is active? 
            # Or use explicit flag if available. For now using item count > 0 logic as fallback
            # But relying on vision might be safer for "inMenu". 
            # However, memory is faster. Let's send inMenu if item_count > 0 AND text is NOT printing (menus often overlay text)
            # Actually, let's just pass raw menu state if needed, or set inMenu
            is_menu = menu_state.get('menu_item_count', 0) > 0
            state['inMenu'] = is_menu
            update_payload['inMenu'] = is_menu

        # Update Movement State for biking/surfing avatar switching
        movement_state = current_mGBA_state.get('movement_state')
        if movement_state:
            state['movementState'] = movement_state
            update_payload['movementState'] = movement_state
            if movement_state.get('movement_mode') != 'walking':
                log.info(f"🚴 Movement mode: {movement_state.get('movement_mode')}")

        # Update Name Entry State (when on character naming screen)
        name_entry_state = current_mGBA_state.get('name_entry_state')
        
        # CRITICAL: Skip name entry if dialog text is present (menu state can persist from earlier)
        dialog_text = text_state.get('text', '') if text_state else ''
        has_dialog = bool(dialog_text and len(dialog_text.strip()) > 0)
        
        if name_entry_state and not has_dialog:
            state['nameEntryState'] = name_entry_state
            update_payload['nameEntryState'] = name_entry_state
            
            # Activate keyboard tracker when name entry is detected
            kb_tracker = get_keyboard_tracker()
            kb_tracker.activate()
            
            # Get the name planner
            name_planner = get_name_planner()
            
            # Detect what type of name we're entering (use dialog_text only - vision not yet available)
            dialog_text = text_state.get('text', '') if text_state else ''
            name_type = name_planner.detect_name_type(dialog_text, '')
            
            # Get tracked position (more reliable than memory reads)
            tracked_state = kb_tracker.get_state_dict()
            row = tracked_state.get('row', 1)
            col = tracked_state.get('col', 1)
            selected_char = tracked_state.get('selected_char', 'A')
            cursor_idx = tracked_state.get('cursor_index', 0)
            
            # Also log memory-read position for comparison/debugging
            mem_char = name_entry_state.get('selected_char', '?')
            mem_idx = name_entry_state.get('cursor_index', -1)
            log.info(f"📝 Name entry: TRACKED='{selected_char}' (Row {row}, Col {col}) | MEM='{mem_char}' (idx {mem_idx}) | TYPE={name_type}")
            
            # Build context based on name type
            if name_type == "player":
                # Always type "LASS" for player
                target_name = "LASS"
                if not name_planner.current_name:
                    name_planner.start_typing(target_name)
                
                next_step = name_planner.get_current_step()
                progress = name_planner.get_progress_string()
                
                if next_step:
                    name_entry_context = (
                        f"🎮 NAME ENTRY - PLAYER NAME: '{target_name}'\n"
                        f"══════════════════════════════════════\n"
                        f"📍 CURSOR: Row {row}, Col {col} → '{selected_char}'\n"
                        f"📝 PROGRESS: {progress}\n"
                        f"\n"
                        f"🎯 NEXT: Type '{next_step['char']}'\n"
                        f"   ▶️ USE THIS ACTION: {next_step['path']}\n"
                        f"\n"
                        f"⚠️ Just copy the action above exactly!\n"
                        f"\n"
                        f"⌨️ KEYBOARD: Row1=ABCDEFGHI | Row2=JKLMNOPQR | Row3=STUVWXYZ\n"
                        f"🕹️ After typing all letters, press START to confirm\n"
                    )
                else:
                    name_entry_context = (
                        f"🎮 NAME ENTRY - DONE TYPING '{target_name}'!\n"
                        f"══════════════════════════════════════\n"
                        f"✅ All letters typed! Press START to confirm the name.\n"
                        f"\n"
                        f"▶️ ACTION: S;\n"
                    )
            
            elif name_type == "rival":
                # Let LLM choose rival name with cute/silly suggestions
                suggestions = ", ".join(RIVAL_NAME_SUGGESTIONS[:6])
                
                if not name_planner.rival_name:
                    # Need to pick a name first
                    name_entry_context = (
                        f"💕 TIME TO NAME YOUR RIVAL! 💕\n"
                        f"══════════════════════════════════════\n"
                        f"📍 CURSOR: Row {row}, Col {col} → '{selected_char}'\n"
                        f"\n"
                        f"🎀 Pick a silly/cute/playful name for him!\n"
                        f"   Suggestions: {suggestions}\n"
                        f"\n"
                        f"⌨️ KEYBOARD LAYOUT:\n"
                        f"   Row 1: A B C D E F G H I\n"
                        f"   Row 2: J K L M N O P Q R\n"
                        f"   Row 3: S T U V W X Y Z _\n"
                        f"\n"
                        f"🕹️ D/U/L/R=navigate | A=type char | START=confirm\n"
                        f"\n"
                        f"💡 First decide what name you want, then navigate to each letter!\n"
                        f"   Example for 'MEANY': M is at Row2,Col4 → D;R;R;R;A;\n"
                    )
                else:
                    # Continue typing the chosen rival name
                    target_name = name_planner.rival_name
                    if not name_planner.current_name or name_planner.current_name != target_name:
                        name_planner.start_typing(target_name)
                    
                    next_step = name_planner.get_current_step()
                    progress = name_planner.get_progress_string()
                    
                    if next_step:
                        name_entry_context = (
                            f"💕 RIVAL NAME: '{target_name}'\n"
                            f"══════════════════════════════════════\n"
                            f"📍 CURSOR: Row {row}, Col {col} → '{selected_char}'\n"
                            f"📝 PROGRESS: {progress}\n"
                            f"\n"
                            f"🎯 NEXT: Type '{next_step['char']}'\n"
                            f"   ▶️ USE THIS ACTION: {next_step['path']}\n"
                            f"\n"
                            f"⚠️ Just copy the action above exactly!\n"
                        )
                    else:
                        name_entry_context = (
                            f"💕 DONE TYPING RIVAL NAME '{target_name}'!\n"
                            f"══════════════════════════════════════\n"
                            f"✅ All letters typed! Press START to confirm.\n"
                            f"\n"
                            f"▶️ ACTION: S;\n"
                        )
            
            else:
                # Generic name entry (pokemon nickname - optional)
                name_entry_context = (
                    f"🎮 NAME ENTRY KEYBOARD\n"
                    f"══════════════════════════════════════\n"
                    f"📍 CURSOR: Row {row}, Col {col} → '{selected_char}'\n"
                    f"\n"
                    f"🐾 This is for a Pokemon nickname (optional!)\n"
                    f"   If you don't want to nickname, just press START to skip.\n"
                    f"\n"
                    f"⌨️ KEYBOARD: Row1=ABCDEFGHI | Row2=JKLMNOPQR | Row3=STUVWXYZ\n"
                    f"🕹️ D/U/L/R=navigate | A=type char | START=confirm/skip | B=cancel\n"
                )
            
            llm_input_state["name_entry_context"] = name_entry_context
            log.info(f"✅ Added name_entry_context: type={name_type}, cursor at Row {row}, Col {col} = '{selected_char}'")
        else:
            # Deactivate keyboard tracker when not in name entry
            kb_tracker = get_keyboard_tracker()
            if kb_tracker.active:
                kb_tracker.deactivate()
                # Reset name planner for next name entry session
                name_planner = get_name_planner()
                name_planner.reset()
            
            # Debug: Log menu state to trace why name entry wasn't detected
            menu_state = current_mGBA_state.get('menu_state', {})
            if menu_state:
                log.info(f"name_entry_state=None, menu_state: item_count={menu_state.get('menu_item_count')}, "
                         f"cursor=({menu_state.get('cursor_x')},{menu_state.get('cursor_y')}), "
                         f"selected={menu_state.get('selected_item')}")


        # Default: Analysis uses the clean snapshot unless combined
        ANALYSIS_IMAGE_PATH = SCREENSHOT_PATH
        UI_IMAGE_PATH = SCREENSHOT_PATH

        if ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
            try:
                # Load images
                # VALIDATION: Use SCREENSHOT_PATH (the atomic snapshot) instead of global SAVED_SCREENSHOT_PATH
                ss_img = Image.open(SCREENSHOT_PATH)
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
                # VALIDATION: Derive combined path from atomic snapshot path to keep it unique per cycle
                combined_path = os.path.splitext(SCREENSHOT_PATH)[0] + '_with_minimap.png'
                combined.save(combined_path)
                
                # CRITICAL: AI gets the combined image, but UI gets the clean original
                ANALYSIS_IMAGE_PATH = combined_path
                # UI_IMAGE_PATH remains SCREENSHOT_PATH (the clean snapshot)

                log.info(f"Combined screenshot + minimap saved to {combined_path}")
            except Exception as e:
                log.error(f"Failed to combine minimap: {e}")
                # Fallback: Analysis path remains SCREENSHOT_PATH

        # Handle image processing based on provider
        if CURRENT_MODE == "ZAI" and vision_manager:
            # For Z.AI MCP, use the CLEAN screenshot (UI_IMAGE_PATH) per user request
            # The minimap context is no longer sent to vision - user prefers clean image
            llm_input_state["screenshot_path"] = UI_IMAGE_PATH
            # Add all diff pairs for multi-diff analysis (N-1 through N-4)
            llm_input_state["diff_pairs"] = screenshot_history.get_diff_pairs()
            # Keep previous_screenshot_path for backwards compatibility
            llm_input_state["previous_screenshot_path"] = screenshot_history.get_previous_screenshot()
            if not ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
                llm_input_state["minimap_path"] = MINIMAP_PATH

            # Also create base64 versions for fallback
            # CRITICAL: Encode the UI_IMAGE_PATH (clean snapshot) for the frontend
            b64_ss = encode_image_base64(UI_IMAGE_PATH)
            if b64_ss:
                # Note: We send the CLEAN screenshot to the LLM's vision input here as valid base64
                # But the MCP tool will use 'screenshot_path' (ANALYSIS_IMAGE_PATH)
                llm_input_state["screenshot"] = {"image_url": {"url": f"data:image/png;base64,{b64_ss}", "detail": IMAGE_DETAIL}}
            else:
                llm_input_state["screenshot"] = None
            
            # Note: Explicitly attaching the clean screenshot base64 for the UI later
            # This happens in the log creation step using 'b64_ss'

            if not ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
                b64_mm = encode_image_base64(MINIMAP_PATH)
                if b64_mm:
                    llm_input_state["minimap"] = {"image_url": {"url": f"data:image/png;base64,{b64_mm}", "detail": IMAGE_DETAIL}}
        else:
            # Standard base64 image processing for other providers
            # Use ANALYSIS path for standard models if they can't handle separate tools?
            # Actually, standard models viewing the image directly should probably see the combined one if enabled.
            # But the user specifically asked for "render the cycle not the one with the minimap" on the UI.
            # So we must differentiate what we send to LLM vs what we send to UI.
            
            # For standard LLM input (e.g. GPT-4o), we want it to see the Minimap if enabled.
            b64_llm = encode_image_base64(ANALYSIS_IMAGE_PATH)
            
            # But for UI, we want clean.
            b64_ss = encode_image_base64(UI_IMAGE_PATH)

            if b64_llm:
                llm_input_state["screenshot"] = {"image_url": {"url": f"data:image/png;base64,{b64_llm}", "detail": IMAGE_DETAIL}}
            else:
                llm_input_state["screenshot"] = None

            if not ONE_IMAGE_PER_PROMPT and MINIMAP_ENABLED:
                b64_mm = encode_image_base64(MINIMAP_PATH)
                if b64_mm:
                    llm_input_state["minimap"] = {"image_url": {"url": f"data:image/png;base64,{b64_mm}", "detail": IMAGE_DETAIL}}
            else:
                llm_input_state["minimap"] = None

        log.info(f"Pre-LLM state update & image prep took {time.time() - state_update_start:.2f}s. SS:{bool(b64_ss)}, MM:{bool(b64_mm)}")

        # NEW: Get Contextual Area Hint
        area_hint = get_area_hint(llm_input_state)
        if area_hint:
            llm_input_state["area_hint"] = area_hint
            log.info(f"💡 AREA HINT: {area_hint.splitlines()[0] if area_hint else 'None'}")

        log_id_counter = state.get("log_id_counter", 0) + 1
        state["log_id_counter"] = log_id_counter

        # Broadcast "ANALYZING..." status before starting vision+LLM processing
        state["processingStatus"] = "ANALYZING VISION..."
        await broadcast_func({"processingStatus": "ANALYZING VISION..."})

        # LOG ALL KEY STATE FIELDS BEING SENT TO LLM (for debugging)
        key_fields = [
            f"map_name={llm_input_state.get('map_name', 'None')}",
            f"position={llm_input_state.get('position', 'None')}",
            f"dialog_text={llm_input_state.get('dialog_text', 'None')[:30] if llm_input_state.get('dialog_text') else 'None'}...",
            f"in_battle={llm_input_state.get('battle_state', {}).get('in_battle', False)}",
            f"name_entry_context={'YES' if llm_input_state.get('name_entry_context') else 'NO'}",
            f"text_state.is_printing={llm_input_state.get('text_state', {}).get('is_printing', False)}",
            f"menu_state.item_count={llm_input_state.get('menu_state', {}).get('menu_item_count', 0)}",
        ]
        log.info(f"📊 LLM INPUT STATE: {' | '.join(key_fields)}")

        # ═══════════════════════════════════════════════════════════════════════════
        # PARALLEL CHAT + LLM PROCESSING
        # Run chat responses during LLM wait to keep stream active
        # ═══════════════════════════════════════════════════════════════════════════
        # ═══════════════════════════════════════════════════════════════════════════
        # PARALLEL CHAT + LLM PROCESSING
        # Run chat responses during LLM wait to keep stream active
        # ═══════════════════════════════════════════════════════════════════════════
        chat_stop_event = asyncio.Event()
        parallel_chat_task = asyncio.create_task(
            run_chat_background_task(
                chat_stop_event, 
                tts_service, 
                twitch_service, 
                cycle_count
            )
        )
        
        try:
            # Run the main LLM call via Controller
            action, game_analysis, summary_json, vision_analysis_for_ui = await controller.call_with_timeout(
                llm_input_state, 
                STREAM_TIMEOUT, 
                LLM_TOTAL_TIMEOUT, 
                benchmark, 
                cycle_metrics
            )
            tokens_used_session = controller.tokens_used_session
            
        finally:
            # Signal chat task to stop and cancel if still running
            chat_stop_event.set()
            
            # Cancel current chat TTS (so it doesn't talk over game commentary)
            if tts_service and tts_service.is_available:
                tts_service.cancel_pending_chat_responses()
                
            try:
                await parallel_chat_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.error(f"Error awaiting parallel chat task: {e}")

        # Clear processing status after completion
        state["processingStatus"] = ""
        await broadcast_func({"processingStatus": ""})

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

        if vision_analysis_for_ui:
            update_payload["vision_analysis"] = vision_analysis_for_ui

        action_to_send = None
        log_action_text = "No action taken (LLM failed)."

        # ═══════════════════════════════════════════════════════════════════════════
        # EARLY LOG CREATION & BROADCAST (before action execution for sync)
        # This ensures UI shows reasoning/action BEFORE mGBA executes it
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Calculate button counts EARLY (needed for action log)
        buttons_in_action = 0
        action_start = action_count
        action_end = action_count
        if action:
            action_buttons = [c for c in action.replace(';', '').replace(' ', '') if c in 'UDLRABST']
            buttons_in_action = len(action_buttons)
            action_start = action_count + 1
            action_end = action_count + buttons_in_action
            log.info(f"📊 Calculated action counts: #{action_start}-#{action_end} ({buttons_in_action} buttons)")
        
        # Create log entries BEFORE action execution
        log_entries = []
        cycle_timestamp = int(time.time() * 1000)
        
        # Vision log
        if vision_analysis_for_ui:
            vision_log = {
                "id": log_id_counter,
                "text": vision_analysis_for_ui,
                "is_vision": True,
                "timestamp": cycle_timestamp,
                "screenshot_base64": b64_ss
            }
            log_entries.append(vision_log)
            if b64_ss:
                state["latest_screenshot_base64"] = b64_ss
        
        # Response log (LLM reasoning)
        if game_analysis and game_analysis.strip():
            response_log = {"id": log_id_counter, "text": game_analysis.strip(), "is_response": True, "timestamp": cycle_timestamp}
            log_entries.append(response_log)
        
        # Action log (intended action - shows BEFORE execution)
        if action and vision_analysis_for_ui:
            action_log = {
                "id": log_id_counter,
                "text": f"Action: {action}",
                "is_action": True,
                "action_start": action_start,
                "action_end": action_end,
                "button_count": buttons_in_action,
                "timestamp": cycle_timestamp
            }
            log_entries.append(action_log)
        
        # BROADCAST LOGS IMMEDIATELY (before action execution)
        if "log_history" not in state:
            state["log_history"] = []
        
        for log_entry in log_entries:
            state["log_history"].insert(0, log_entry)
            if log_entry.get("is_vision"):
                update_payload["vision_log"] = log_entry
                log.info(f"🖼️ Broadcasting vision log: {log_entry.get('text', '')[:50]}...")
            elif log_entry.get("is_response"):
                update_payload["response_log"] = log_entry
                log.info(f"💭 Broadcasting response log: {log_entry.get('text', '')[:50]}...")
            elif log_entry.get("is_action"):
                update_payload["log_entry"] = log_entry  # For action_payload compatibility
                log.info(f"🎮 Broadcasting action log: {log_entry.get('text', '')[:50]}...")
        
        state["log_history"] = state["log_history"][:50]
        
        # Include state counts in the early broadcast (with PREDICTED action count)
        predicted_action_count = action_count + buttons_in_action
        update_payload["cycle"] = current_cycle
        update_payload["actions"] = predicted_action_count  # Show what it WILL be after execution
        update_payload["tokensUsed"] = tokens_used_session
        state["actions"] = predicted_action_count
        state["tokensUsed"] = tokens_used_session
        
        # BROADCAST NOW - before action execution
        if update_payload:
            await broadcast_func(update_payload)
            log.info(f"📡 Broadcast complete: {list(update_payload.keys())}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # TTS COMMENTARY PLAYBACK (BEFORE action execution for proper sync)
        # Order: UI shows reasoning/action → TTS plays → mGBA executes
        # ═══════════════════════════════════════════════════════════════════════════
        if game_analysis and tts_service and tts_service.is_available:
            # Extract commentary from the LLM response
            commentary_match = re.search(r'<commentary>([\s\S]*?)</commentary>', game_analysis, re.IGNORECASE)
            
            if not commentary_match:
                # Fallback: various numbered formats
                commentary_match = re.search(
                    r'(?:7|8|9|10|11)\.\s*\*{0,2}COMMENTARY\*{0,2}[:\s]*["\'\(]?(.+?)["\'\)]?(?=\n\d+\.|$|\n\n|</game_analysis>)',
                    game_analysis, 
                    re.IGNORECASE | re.DOTALL
                )
            
            if commentary_match:
                commentary_text = commentary_match.group(1).strip()
                commentary_text = re.sub(r'^[-–•]\s*', '', commentary_text)
                commentary_text = re.sub(r'\n.*$', '', commentary_text)  # Take first line only
                commentary_text = commentary_text.strip().strip('"\'')
                
                if commentary_text and len(commentary_text) > 5:
                    log.info(f"🔊 Playing TTS: {commentary_text[:60]}...")
                    
                    # Update chat response service context
                    if chat_response_service.is_available:
                        chat_response_service.update_context(
                            game_context=f"Currently in {current_mGBA_state.get('map_name', 'unknown')}",
                            commentary=commentary_text,
                            location=current_mGBA_state.get('map_name', 'unknown'),
                            memory=memory_manager.get_narrative_context()
                        )
                    
                    # Synthesize and play TTS - WAIT for it to complete
                    try:
                        await tts_service.synthesize_and_play(
                            commentary_text,
                            priority=tts_service.PRIORITY_COMMENTARY,
                            wait=True
                        )
                        log.info(f"✅ TTS playback complete")
                    except Exception as tts_err:
                        log.warning(f"🔊 TTS error: {tts_err}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # ACTION EXECUTION (now happens AFTER TTS completes)
        # ═══════════════════════════════════════════════════════════════════════════

        if action:
            action_to_send = action
            log_action_text = f"Action: {action}"
            log.info(f"LLM proposed action: {action}")
            try:
                # Broadcast action_execute to trigger button animation in UI
                # This is sent right before mGBA executes so animation syncs with game
                await broadcast_func({
                    "action_execute": True,
                    "action_buttons": action_to_send.replace(";", " ").strip().split(),
                    "buttons_in_action": buttons_in_action
                })
                log.info(f"🎮 Broadcasted action_execute for animation trigger")
                
                # Wait 1s before sending action to let game state settle
                time.sleep(1)
                sock.sendall((action_to_send + "\n").encode("utf-8"))
                log.info(f"Action '{action_to_send}' sent to mGBA.")
                
                # Update keyboard tracker with the action (for name entry screens)
                kb_tracker = get_keyboard_tracker()
                if kb_tracker.active:
                    kb_tracker.apply_action(action_to_send)
                    
                    # Advance name planner for each 'A' press (typing a character)
                    name_planner = get_name_planner()
                    a_presses = action_to_send.upper().count('A')
                    for _ in range(a_presses):
                        name_planner.advance()
                
                # Wait 4s AFTER sending action to let screen fully render before next screenshot
                # This prevents cut-off/partial screenshots and ensures dialog text is captured
                time.sleep(4)
                log.info("Post-action delay complete, ready for next cycle screenshot.")
                
                # Track for failure replay
                last_action = action_to_send
                last_position = current_pos
                
                # Track NPC interactions when A button is pressed
                if 'A' in action_to_send.upper() and current_pos and map_name:
                    npc_warning = memory_manager.record_npc_interaction(
                        map_name, 
                        list(current_pos), 
                        npc_name="NPC"
                    )
                    if npc_warning:
                        # Add warning to stuck_warning for next cycle
                        llm_input_state["stuck_warning"] = llm_input_state.get("stuck_warning", "") + f" {npc_warning}"
                        
            except socket.error as se:
                log.error(f"Socket error sending action '{action_to_send}': {se}. Stopping loop.")
                break
            except Exception as e:
                log.error(f"Unexpected error sending action '{action_to_send}': {e}", exc_info=True)

        else:
            log.error("No valid action from LLM. Cannot send command.")
            # User request: Stay on same cycle number if failure occurs
            cycle_count -= 1
            log.info("Decremented cycle count to retry same cycle number on next attempt.")

        # Update the GLOBAL action_count variable after execution
        # (state was already updated in the early broadcast with predicted value)
        if action:
            action_count += buttons_in_action
            log.info(f"📊 Actions #{action_start}-#{action_end} ({buttons_in_action} buttons) - EXECUTED")
        
        # Update elapsed time for status display
        elapsed = datetime.datetime.now() - start_time
        elapsed_seconds = elapsed.total_seconds()
        game_status_str = f"{int(elapsed_seconds // 3600)}h {int((elapsed_seconds % 3600) // 60)}m {int(elapsed_seconds % 60)}s"
        state['gameStatus'] = game_status_str
        state['modelName'] = MODEL

        # Force memory recording for important location transitions
        # IMPORTANT: This runs ALWAYS, not just when analysis_text is empty
        try:
            # MAP TRANSITION LOGIC - use current_mGBA_state which has correct keys
            current_map = current_mGBA_state.get('map_name', 'unknown')
            current_map_id = current_mGBA_state.get('map_id', -1)
            current_pos = current_mGBA_state.get('position', [])

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
                    # Check if we were on an O tile before transition
                    # This helps determine if this was a natural transition or cutscene
                    last_minimap = getattr(memory_manager, 'last_minimap_2d', '')
                    was_on_o_tile = False
                    minimap_had_exit = False
                    
                    if last_minimap:
                        # Check if there was an 'O' tile near player position in last minimap
                        # 'O' tiles indicate exits/entrances
                        rows = last_minimap.split(';')
                        for row in rows:
                            if 'O' in row:
                                minimap_had_exit = True
                                break
                        # Check if player marker 'P' was adjacent to or on an 'O'
                        for row_idx, row in enumerate(rows):
                            p_idx = row.find('P')
                            if p_idx >= 0:
                                # Check adjacent tiles for 'O'
                                if (p_idx > 0 and row[p_idx-1] == 'O') or \
                                   (p_idx < len(row)-1 and row[p_idx+1] == 'O'):
                                    was_on_o_tile = True
                                if row_idx > 0 and len(rows[row_idx-1]) > p_idx and rows[row_idx-1][p_idx] == 'O':
                                    was_on_o_tile = True
                                if row_idx < len(rows)-1 and len(rows[row_idx+1]) > p_idx and rows[row_idx+1][p_idx] == 'O':
                                    was_on_o_tile = True
                                break
                    
                    new_links = memory_manager.record_transition(
                        from_map=last_map,
                        from_pos=list(last_pos) if isinstance(last_pos, tuple) else last_pos,
                        to_map=current_map,
                        to_pos=list(current_pos) if isinstance(current_pos, tuple) else current_pos,
                        was_on_o_tile=was_on_o_tile,
                        minimap_had_exit=minimap_had_exit
                    )
                    if new_links:
                         log.info(f"🔗 TRANSITION RECORDED: {last_map} -> {current_map} (O-tile: {was_on_o_tile})")
                         update_payload["memory_write"] = {"text": f"Mapped connection: {last_map} -> {current_map}"}
                         
                         # Reset failed attempts and boost confidence since this exit WORKED
                         memory_manager.reset_failed_attempts(
                             last_map, 
                             list(last_pos) if isinstance(last_pos, tuple) else last_pos
                         )
                         
                         # Mark this as a Lass-discovered exit for the minimap overlay
                         memory_manager.mark_lass_exit(
                             last_map,
                             list(last_pos) if isinstance(last_pos, tuple) else last_pos,
                             destination=current_map,
                             confidence=0.95 if was_on_o_tile else 0.8
                         )
            
            # Update history for next loop
            memory_manager.last_map = current_map
            memory_manager.last_map_id = current_map_id
            memory_manager.last_pos = current_pos
            memory_manager.last_minimap_2d = current_mGBA_state.get('minimap_2d', '')

            # Extract memories from LLM response and vision analysis
            # CRITICAL FIX: Use current_mGBA_state which has map_name and position keys
            # Also guard against None analysis_text (occurs when vision fails)
            extracted_memories = []
            if game_analysis:
                extracted_memories = memory_manager.extract_memories_from_response(
                    analysis_text=game_analysis,
                    game_state=current_mGBA_state,  # Fixed: was 'state' which has different keys
                    vision_analysis=vision_analysis_for_ui
                )

            if extracted_memories:
                log.info(f"📝 Extracted {len(extracted_memories)} memories from LLM response")
                for memory in extracted_memories:
                    log.debug(f"Memory: {memory.type} - {memory.description[:50]}...")
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # QUEST GOAL CREATION - When we detect quest items, create goals
                    # Quest goals are CRITICAL priority - they override healing
                    # ═══════════════════════════════════════════════════════════════════
                    if hasattr(memory, 'quest_id') and memory.quest_id:
                        # Check if we already have this quest goal
                        if not goal_tracker.has_quest_goal(memory.quest_id):
                            goal_id = goal_tracker.add_quest_goal(
                                quest_id=memory.quest_id,
                                description=memory.description,
                                target_location=getattr(memory, 'target_location', None),
                                target_npc=getattr(memory, 'target_npc', None)
                            )
                            if goal_id:
                                log.info(f"🎯 CREATED QUEST GOAL: {memory.description}")
                                log.info(f"   Quest ID: {memory.quest_id} | Goal ID: {goal_id}")
                                # Broadcast quest detection to UI
                                update_payload["memory_write"] = {
                                    "text": f"🎯 NEW QUEST: {memory.description}"
                                }

            # Verify pending vision claims against minimap data
            minimap_2d = current_mGBA_state.get('minimap_2d', '')
            if minimap_2d and current_pos:
                unverified_claims = memory_manager.get_unverified_claims(limit=3)
                for claim in unverified_claims:
                    was_correct = memory_manager.verify_vision_claim(
                        claim=claim,
                        minimap_2d=minimap_2d,
                        player_pos=list(current_pos) if current_pos else []
                    )
                    if was_correct:
                        log.info(f"✅ Vision claim VERIFIED: {claim.description}")
                    else:
                        log.warning(f"❌ Vision claim WRONG: {claim.description}")
                
                # Log vision accuracy periodically
                vision_stats = memory_manager.get_vision_accuracy()
                if vision_stats.get("verified", 0) > 0 and vision_stats.get("verified", 0) % 5 == 0:
                    log.info(f"👁️ {vision_stats['message']}")

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
            latest_memory = None
        
        # Persist run state periodically (after memory extraction so latest_memory is available)
        cycles_since_persist += 1
        if persistence and run_state and cycles_since_persist >= PERSIST_INTERVAL:
            run_state.cycle_count = cycle_count
            run_state.action_count = action_count
            run_state.tokens_used = tokens_used_session
            run_state.elapsed_seconds = elapsed_seconds
            run_state.goals = state.get('goals', run_state.goals)
            run_state.other_goals = state.get('otherGoals', run_state.other_goals)
            run_state.chat_history = controller.chat_history[-20:]  # Keep last 20 messages
            run_state.recent_actions.append(action if action else 'NONE')
            run_state.recent_actions = run_state.recent_actions[-50:]  # Keep last 50
            if latest_memory:
                run_state.latest_memory = latest_memory.description
            
            persistence.save_run_state(run_state)
            cycles_since_persist = 0
            log.info(f"💾 Persisted run state: cycle={cycle_count}, actions={action_count}, tokens={tokens_used_session}")
        
        # Log action to database
        if persistence and run_state and action:
            try:
                persistence.log_action(
                    run_id=run_state.run_id,
                    action=action,
                    screenshot_b64=b64_ss[:1000] if b64_ss else None,  # Truncate for storage
                    llm_analysis=game_analysis[:2000] if game_analysis else None,
                    vision_analysis=vision_analysis_for_ui[:2000] if vision_analysis_for_ui else None,
                    position=current_pos,
                    map_name=map_name,
                    metrics=cycle_metrics
                )
            except Exception as pe:
                log.warning(f"Failed to log action to database: {pe}")

        # CRITICAL: Check for system failure
        if update_payload and update_payload.get("system_halt"):
            log.critical("🛑 SYSTEM HALT DETECTED - Terminating agent operation immediately")
            break  # Exit the main loop immediately


        # Auto-save game state at end of each cycle
        try:
            # AUTOSAVE enabled: save to slot 1 every cycle for safety
            save_game_state(sock_ref["socket"], slot=1)  # Use slot 1 for regular saves
        except Exception as e:
            log.warning(f"⚠️ Save operation failed: {e} - continuing cycle")

        elapsed_loop_time = time.time() - loop_start_time
        # ORIGINAL llmdriver.py used max(10, ...). 
        # Changed to 10s minimum wait as requested.
        wait_time = max(2, interval - elapsed_loop_time) # Ensure at least 2 seconds wait
        if result and result.get("stats", {}).get("action_count", 0) > 0:
            log.info(f"💾 Cycle {current_cycle} action execution successful")
            
        t_cycle_end = time.time()
        cycle_duration_s = t_cycle_end - loop_start_time  # Processing time (from successful mGBA response)
        true_cycle_duration_s = t_cycle_end - true_cycle_start  # True wall clock time (includes mGBA retries)
        cycle_metrics["cycle"] = true_cycle_duration_s * 1000  # Store TRUE cycle time
        
        log.info(f"⏱️ Total Cycle Time: {true_cycle_duration_s:.2f}s")
        log.info(f"Cycle {current_cycle} took {elapsed_loop_time:.2f}s. Waiting {wait_time:.2f}s...")
        
        # ═══════════════════════════════════════════════════════════════════
        # Broadcast cycle timing to UI
        # ═══════════════════════════════════════════════════════════════════
        cycle_timing_str = f"{elapsed_loop_time:.1f}s | wait {wait_time:.1f}s"
        
        # We need to update the log_action call (it happened inside llm_stream_action or executed via persistence object?)
        # Actually persistence.log_action is called where? It hasn't been called yet for this cycle in this scope?
        # Aah, log_action is usually called inside the execute loop or we need to pass these metrics to where it IS called.
        # But wait, run_persistence.log_action is called in `run_auto_loop`? No, it's not.
        # Looking at previous code, `persistence.log_action` was NOT called in `run_auto_loop` explicitly in the visible code. 
        # It must be called elsewhere or I missed it.
        # Let's check `llm_stream_action` returns `summary_json`? 
        # Ah, `persistence` is global or passed?
        # I need to find where `log_action` is called.
        
        pass # Placeholder to allow finding the callsite in next step if needed, or simply patching likely location.
        
        if broadcast_func:
            try:
                # Track cycle time for average calculation - use TRUE time
                cycle_times_history.append(true_cycle_duration_s)
                # Keep only last 20 cycles for average
                if len(cycle_times_history) > 20:
                    cycle_times_history.pop(0)
                
                # Calculate average
                avg_cycle_time = sum(cycle_times_history) / len(cycle_times_history) if cycle_times_history else 0
                
                # Broadcast enhanced cycle metrics: current cycle, previous cycle, average, and detailed breakdown
                cycle_metrics_payload = {
                    "cycleTiming": cycle_timing_str,
                    "currentCycleTime": round(true_cycle_duration_s, 1),  # TRUE wall clock time
                    "prevCycleTime": round(prev_cycle_time_s, 1),
                    "avgCycleTime": round(avg_cycle_time, 1),
                    "cycleMetrics": {
                        "mGBA": round(cycle_metrics.get("mGBA", 0) / 1000, 1),  # Convert ms to s
                        "vision": round(cycle_metrics.get("vision", 0) / 1000, 1),
                        "diff": round(cycle_metrics.get("diff", 0) / 1000, 1),
                        "llm": round(cycle_metrics.get("llm", 0) / 1000, 1),
                        "total": round(true_cycle_duration_s, 1)
                    }
                }
                await broadcast_func(cycle_metrics_payload)
                
                # Also update the shared state so new clients get the values
                state["currentCycleTime"] = round(true_cycle_duration_s, 1)
                state["prevCycleTime"] = round(prev_cycle_time_s, 1)
                state["avgCycleTime"] = round(avg_cycle_time, 1)
            except Exception as e:
                log.warning(f"Failed to broadcast cycle timing: {e}")
        
        # Store current cycle time as previous for next iteration - use TRUE time
        prev_cycle_time_s = true_cycle_duration_s
        
        # ═══════════════════════════════════════════════════════════════════════════
        # TWITCH CHAT RESPONSE PROCESSING (during wait period)
        # ═══════════════════════════════════════════════════════════════════════════
        # Mark the current time as when game commentary was sent
        if twitch_service.is_available:
            twitch_service.mark_commentary_timestamp()
        
        # Process Twitch chat during wait period
        wait_start = time.time()
        chat_response_count = 0
        max_chat_responses = 3  # Limit responses per cycle to avoid overwhelming
        
        # Flag to detect if new cycle is starting (for interruption)
        cycle_interrupted = False
        
        while time.time() - wait_start < wait_time and not cycle_interrupted:
            remaining_wait = wait_time - (time.time() - wait_start)
            
            # Check if Twitch service is available and we haven't hit response limit
            if not twitch_service.is_available or chat_response_count >= max_chat_responses:
                await asyncio.sleep(min(remaining_wait, 2.0))
                continue
            
            # Check if we're in test mode first (handles its own message generation)
            from services.twitch_chat_service import TWITCH_TEST_MODE, TWITCH_TEST_LLM
            
            if TWITCH_TEST_MODE:
                # Test mode: Generate message immediately, then wait for TTS
                import random
                
                if chat_response_count >= max_chat_responses:
                    await asyncio.sleep(1.0)
                    continue
                
                # Check time remaining - only need 1 second to start a response
                remaining = wait_time - (time.time() - wait_start)
                if remaining < 1:
                    continue
                
                # Generate one random test message FIRST (no pre-delay!)
                test_msg = twitch_service.generate_single_test_message()
                
                if test_msg:
                    # Decide: spam = skip, else = respond
                    is_spam = any(spam in test_msg["message"].lower() for spam in 
                                 ["kekw", "lul", "kappa", "!gamble", "first", "asdf", "zzz", "spam"])
                    
                    if is_spam or random.random() < 0.25:  # 25% skip rate
                        log.info(f"⏭️ [TEST] Skipping spam from @{test_msg['display_name']}: {test_msg['message'][:40]}...")
                        await asyncio.sleep(0.5)  # Brief pause before next message
                    else:
                        # Generate response - use LLM if TWITCH_TEST_LLM=true, otherwise mock
                        llm_start = time.time()
                        if TWITCH_TEST_LLM and chat_response_service.is_available:
                            # Use actual LLM (Featherless) for realistic latency testing
                            try:
                                response_text = await chat_response_service.generate_response(
                                    test_msg['display_name'],
                                    test_msg['message'],
                                    is_past=False
                                )
                                llm_time = time.time() - llm_start
                                log.info(f"💬 [TEST+LLM] @{test_msg['display_name']}: \"{test_msg['message']}\"")
                                log.info(f"🎤 [TEST+LLM] Lass responds (LLM took {llm_time:.2f}s): {response_text}")
                            except Exception as e:
                                log.warning(f"[TEST+LLM] LLM error, falling back to mock: {e}")
                                response_text = f"Hehe thanks @{test_msg['display_name']}! You're awesome!"
                        else:
                            # Use mock responses for speed testing
                            mock_responses = [
                                f"Hehe, thanks for watching @{test_msg['display_name']}! You're making this adventure more fun!",
                                f"Omg hi @{test_msg['display_name']}! I'm so happy you're here with me!",
                                f"@{test_msg['display_name']} Aww you're so sweet! Let's catch 'em all together!",
                                f"Thanks @{test_msg['display_name']}! I may get lost sometimes but at least we're lost together!",
                                f"@{test_msg['display_name']} You're the Pikachu to my Ash! Well... once I actually GET a Pikachu...",
                                f"Haha @{test_msg['display_name']}! True, but hey, every Pokemon master started somewhere!",
                                f"Aww @{test_msg['display_name']} that's so nice! You're giving me all the encouragement I need!",
                                f"@{test_msg['display_name']} Good question! I'm working on it, I promise! Maybe...",
                            ]
                            response_text = random.choice(mock_responses)
                            log.info(f"💬 [TEST] @{test_msg['display_name']}: \"{test_msg['message']}\"")
                            log.info(f"🎤 [TEST] Lass responds: {response_text}")
                        
                        chat_response_count += 1
                        
                        # Queue TTS (non-blocking) - if queue full, response will just show in UI
                        tts_queued = False
                        if tts_service.is_available:
                            try:
                                request = await tts_service.queue_and_start_synthesis(
                                    response_text,
                                    priority=tts_service.PRIORITY_CHAT_RESPONSE,
                                    cycle_id=current_cycle
                                )
                                tts_queued = request is not None
                                if tts_queued:
                                    log.info(f"✅ [TEST] TTS queued (non-blocking)")
                                else:
                                    log.info(f"📝 [TEST] TTS queue full, response will only show in UI")
                            except Exception as tts_err:
                                log.warning(f"🔊 [TEST] TTS error: {tts_err}")
                        
                        # Broadcast to UI (always - even if TTS queue full)
                        chat_response_payload = {
                            "chat_response": {
                                "username": test_msg['display_name'],
                                "message": test_msg['message'],
                                "response": response_text,
                                "is_test": True,
                                "tts_queued": tts_queued,  # UI can show indicator
                                "timestamp": int(time.time() * 1000)
                            }
                        }
                        await broadcast_func(chat_response_payload)
                        
                        # Brief delay before next potential message
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                
                continue  # Continue the wait loop
            
            # Real mode below - get actual messages
            messages_for_cycle = twitch_service.get_messages_for_cycle_or_test()
            
            if not messages_for_cycle:
                await asyncio.sleep(min(remaining_wait, 2.0))
                continue
                
            # Real mode: Use chat response service for decisions
            if not chat_response_service.is_available:
                await asyncio.sleep(min(remaining_wait, 2.0))
                continue
                
            # Decide SKIP/RESPOND for all messages at once
            decisions = await chat_response_service.decide_skip_or_respond(messages_for_cycle)
            
            # Process RESPOND messages oldest first
            for decided in decisions:
                if decided.decision == MessageDecision.SKIP:
                    log.info(f"⏭️ Skipping message from @{decided.display_name}")
                    # Mark as responded so we don't process again
                    original_msg = next(
                        (m["_original"] for m in messages_for_cycle 
                         if m["timestamp"] == decided.timestamp), 
                        None
                    )
                    if original_msg:
                        twitch_service.mark_responded(original_msg)
                    continue
                    
                # Check if we should stop for new cycle
                if time.time() - wait_start >= wait_time:
                    log.info("🔄 Cycle time up - interrupting chat responses")
                    tts_service.cancel_current()  # Cancel any playing audio
                    cycle_interrupted = True
                    break
                
                # Generate and send response
                response_text = await chat_response_service.generate_response(
                    decided.display_name,
                    decided.message,
                    is_past=False
                )
                
                if response_text:
                    # Format response with @ mention if not already present
                    if not response_text.startswith("@"):
                        response_text = f"@{decided.display_name} {response_text}"
                    
                    # Mark original message as responded
                    original_msg = next(
                        (m["_original"] for m in messages_for_cycle 
                         if m["timestamp"] == decided.timestamp), 
                        None
                    )
                    if original_msg:
                        twitch_service.mark_responded(original_msg)
                    
                    chat_response_count += 1
                    
                    # Queue TTS for the response (non-blocking) - if full, text still goes to Twitch
                    tts_queued = False
                    if tts_service.is_available:
                        request = await tts_service.queue_and_start_synthesis(
                            response_text,
                            priority=tts_service.PRIORITY_CHAT_RESPONSE,
                            cycle_id=current_cycle
                        )
                        tts_queued = request is not None
                    
                    # Send response to Twitch chat
                    await twitch_service.send_response(
                        decided.display_name,
                        response_text.replace(f"@{decided.display_name} ", "")
                    )
                    
                    # Broadcast chat response to OBS widget
                    chat_response_payload = {
                        "chat_response": {
                            "username": decided.display_name,
                            "response": response_text,
                            "is_past_message": False,
                            "timestamp": int(time.time() * 1000)
                        }
                    }
                    await broadcast_func(chat_response_payload)
                    log.info(f"✅ Chat response sent: {response_text[:50]}...")
            
            # If we processed all messages, sleep briefly
            await asyncio.sleep(min(remaining_wait, 1.0))



    log.info("Auto loop terminated.")
    if benchmark is not None:
        benchmark.finalize(current_mGBA_state, MODEL)