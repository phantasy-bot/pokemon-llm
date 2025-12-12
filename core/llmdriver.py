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
from pyAIAgent.llm.zai_mcp_client import create_zai_vision_client
from trackers.memory_storage import MemoryManager
from core.battle_strategy import read_battle_state, choose_battle_action, get_battle_context
from trackers.goal_tracker import GoalTracker, GoalPriority, GoalStatus
from trackers.exploration_tracker import ExplorationTracker
from services.twitch_chat_service import TwitchChatService, create_twitch_service
from services.comfyui_tts_service import ComfyUITTSService, create_tts_service
from services.chat_response_service import ChatResponseService, create_chat_response_service, MessageDecision
from trackers.history_tracker import ScreenshotHistoryTracker
from trackers.coordinate_tracker import CoordinateTracker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('llmdriver')


ACTION_RE = re.compile(r'^[LRUDABSTt](?:;[LRUDABSTt])*;?')  # Match action at start, allow trailing text
COORD_RE = re.compile(r'^([0-9]),([0-8])$')
ANALYSIS_RE = re.compile(r"<game_analysis>([\s\S]*?)</game_analysis>", re.IGNORECASE)
IS_LOCAL = DEFAULT_MODE == "LMSTUDIO" or DEFAULT_MODE == "OLLAMA"



def compress_chat_history(chat_history, new_assistant_content):
    """
    Attempts to compress chat history by merging consecutive identical assistant actions.
    Returns True if compressed (appended to existing last msg), False otherwise.
    """
    if not chat_history:
        return False
        
    last_msg = chat_history[-1]
    if last_msg["role"] != "assistant":
        return False

    # Check against new content
    content = last_msg["content"]
    if not isinstance(content, str):
        return False
    
    # Regex to find ending (xN)
    match = re.search(r' \(x(\d+)\)$', content)
    current_count = 1
    clean_content = content
    
    if match:
        current_count = int(match.group(1))
        clean_content = content[:match.start()]
    
    if clean_content.strip() == new_assistant_content.strip():
        # Identical content!
        # Only compress if it's short (likely navigation)
        if len(clean_content) < 150:
            new_count = current_count + 1
            last_msg["content"] = f"{clean_content} (x{new_count})"
            return True
            
    return False


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


def parse_minimap(minimap_2d: str, world_position: list = None) -> dict:
    """
    Pre-compute minimap analysis to reduce LLM hallucination.
    
    Args:
        minimap_2d: The raw minimap string
        world_position: Player's world coordinates [x, y] - used to convert grid coords to world coords
    
    Returns a dict with player position, grid dimensions, adjacent tiles, blocked directions,
    and world coordinate mappings for exits.
    """
    if not minimap_2d:
        return {}
    
    # Parse rows (split by semicolon, strip whitespace)
    rows = [row.strip() for row in minimap_2d.split(';') if row.strip()]
    if not rows:
        return {}
    
    num_rows = len(rows)
    num_cols = len(rows[0]) if rows else 0
    
    # Find player position (look for 'P' in the grid)
    player_row = -1
    player_col = -1
    for r_idx, row in enumerate(rows):
        p_idx = row.find('P')
        if p_idx >= 0:
            player_row = r_idx
            player_col = p_idx
            break
    
    if player_row < 0 or player_col < 0:
        return {"error": "Player 'P' not found in minimap"}
    
    # World coordinate conversion function
    # Grid is centered on player, so player's grid position maps to world position
    world_x = world_position[0] if world_position and len(world_position) >= 2 else None
    world_y = world_position[1] if world_position and len(world_position) >= 2 else None
    
    def grid_to_world(grid_col, grid_row):
        """Convert grid coordinates to world coordinates"""
        if world_x is None or world_y is None:
            return None
        # Offset from player's grid position
        dx = grid_col - player_col
        dy = grid_row - player_row
        return [world_x + dx, world_y + dy]
    
    # Get adjacent tiles
    def get_tile(row, col):
        if 0 <= row < num_rows and 0 <= col < len(rows[row]):
            return rows[row][col]
        return '?'  # Out of bounds
    
    north_tile = get_tile(player_row - 1, player_col)
    south_tile = get_tile(player_row + 1, player_col)
    east_tile = get_tile(player_row, player_col + 1)
    west_tile = get_tile(player_row, player_col - 1)
    
    # Determine blocked directions (B = blocked, W = walkable, O = exit)
    def is_blocked(tile):
        return tile == 'B'
    
    def is_exit(tile):
        return tile in ('O', 'D', 'E', '>', '<', '^', 'v')
    
    blocked = []
    walkable = []
    exits = []
    
    if is_blocked(north_tile):
        blocked.append("NORTH (U)")
    elif is_exit(north_tile):
        exits.append(f"NORTH at [{player_col},{player_row-1}]")
        walkable.append("NORTH (U)")
    else:
        walkable.append("NORTH (U)")
    
    if is_blocked(south_tile):
        blocked.append("SOUTH (D)")
    elif is_exit(south_tile):
        exits.append(f"SOUTH at [{player_col},{player_row+1}]")
        walkable.append("SOUTH (D)")
    else:
        walkable.append("SOUTH (D)")
    
    if is_blocked(east_tile):
        blocked.append("EAST (R)")
    elif is_exit(east_tile):
        exits.append(f"EAST at [{player_col+1},{player_row}]")
        walkable.append("EAST (R)")
    else:
        walkable.append("EAST (R)")
    
    if is_blocked(west_tile):
        blocked.append("WEST (L)")
    elif is_exit(west_tile):
        exits.append(f"WEST at [{player_col-1},{player_row}]")
        walkable.append("WEST (L)")
    else:
        walkable.append("WEST (L)")
    
    # Find all O tiles in the minimap (with world coordinates and direction hints)
    o_tiles = []
    for r_idx, row in enumerate(rows):
        for c_idx, char in enumerate(row):
            if char in ('O', 'D', 'E'):
                world_coords = grid_to_world(c_idx, r_idx)
                
                # Add direction hint based on position relative to grid
                # If exit is at bottom of grid, likely a building exit (step DOWN)
                # If exit is at top, likely an entrance from outside (step UP)
                dir_hint = ""
                if r_idx >= num_rows - 2:  # Bottom edge
                    dir_hint = " (SOUTH EXIT - step DOWN)"
                elif r_idx <= 1:  # Top edge
                    dir_hint = " (NORTH - step UP to enter)"
                elif c_idx >= num_cols - 2:  # Right edge
                    dir_hint = " (EAST EXIT)"
                elif c_idx <= 1:  # Left edge
                    dir_hint = " (WEST EXIT)"
                
                if world_coords:
                    o_tiles.append(f"Grid[{c_idx},{r_idx}] = World[{world_coords[0]},{world_coords[1]}]{dir_hint}")
                else:
                    o_tiles.append(f"Grid[{c_idx},{r_idx}]{dir_hint}")
    
    # Find all NPC tiles ('N') in the minimap
    npc_tiles = []
    for r_idx, row in enumerate(rows):
        for c_idx, char in enumerate(row):
            if char == 'N':
                world_coords = grid_to_world(c_idx, r_idx)
                if world_coords:
                    npc_tiles.append(f"Grid[{c_idx},{r_idx}] = World[{world_coords[0]},{world_coords[1]}]")
                else:
                    npc_tiles.append(f"Grid[{c_idx},{r_idx}]")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PASSAGE/CHOKEPOINT DETECTION
    # Find walkable paths through blocked areas (bridges, corridors, entrances)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def is_walkable(tile):
        return tile in ('W', 'P', 'O', 'D', 'E', '>', '<', '^', 'v')
    
    passages = []  # List of detected passages/chokepoints
    
    # Scan for horizontal passages (W surrounded by B above and below)
    for r_idx in range(1, num_rows - 1):
        row = rows[r_idx]
        for c_idx in range(len(row)):
            tile = row[c_idx]
            if is_walkable(tile):
                above = get_tile(r_idx - 1, c_idx)
                below = get_tile(r_idx + 1, c_idx)
                
                # Horizontal passage: walkable with blocked above AND below
                if above == 'B' and below == 'B':
                    # Check if this is part of a longer passage
                    passage_width = 1
                    for check_col in range(c_idx + 1, min(c_idx + 10, len(row))):
                        if (is_walkable(get_tile(r_idx, check_col)) and
                            get_tile(r_idx - 1, check_col) == 'B' and
                            get_tile(r_idx + 1, check_col) == 'B'):
                            passage_width += 1
                        else:
                            break
                    
                    if passage_width >= 2:  # At least 2 tiles wide to be notable
                        # Calculate direction from player
                        dy = r_idx - player_row
                        dx = c_idx - player_col
                        direction = []
                        if dy < 0: direction.append("NORTH")
                        elif dy > 0: direction.append("SOUTH")
                        if dx < 0: direction.append("WEST")
                        elif dx > 0: direction.append("EAST")
                        dir_str = "-".join(direction) if direction else "HERE"
                        
                        passages.append({
                            "type": "horizontal_passage",
                            "start": f"[{c_idx},{r_idx}]",
                            "width": passage_width,
                            "direction": dir_str,
                            "distance": abs(dy) + abs(dx)
                        })
                        # Skip tiles we've already counted
                        break
    
    # Scan for vertical passages (W surrounded by B left and right)
    for c_idx in range(1, num_cols - 1):
        for r_idx in range(num_rows):
            if c_idx >= len(rows[r_idx]):
                continue
            tile = rows[r_idx][c_idx]
            if is_walkable(tile):
                left = get_tile(r_idx, c_idx - 1)
                right = get_tile(r_idx, c_idx + 1)
                
                # Vertical passage: walkable with blocked left AND right
                if left == 'B' and right == 'B':
                    # Check if this is part of a longer passage
                    passage_height = 1
                    for check_row in range(r_idx + 1, min(r_idx + 10, num_rows)):
                        if (check_row < num_rows and c_idx < len(rows[check_row]) and
                            is_walkable(get_tile(check_row, c_idx)) and
                            get_tile(check_row, c_idx - 1) == 'B' and
                            get_tile(check_row, c_idx + 1) == 'B'):
                            passage_height += 1
                        else:
                            break
                    
                    if passage_height >= 2:  # At least 2 tiles tall to be notable
                        # Calculate direction from player
                        dy = r_idx - player_row
                        dx = c_idx - player_col
                        direction = []
                        if dy < 0: direction.append("NORTH")
                        elif dy > 0: direction.append("SOUTH")
                        if dx < 0: direction.append("WEST")
                        elif dx > 0: direction.append("EAST")
                        dir_str = "-".join(direction) if direction else "HERE"
                        
                        passages.append({
                            "type": "vertical_passage",
                            "start": f"[{c_idx},{r_idx}]",
                            "height": passage_height,
                            "direction": dir_str,
                            "distance": abs(dy) + abs(dx)
                        })
                        break
    
    # Sort passages by distance from player
    passages.sort(key=lambda p: p.get("distance", 999))
    
    # Format passages for output (top 3 closest)
    passage_strs = []
    for p in passages[:3]:
        if p["type"] == "horizontal_passage":
            passage_strs.append(f"🌉 Horizontal path at {p['start']} ({p['width']} tiles wide) - go {p['direction']}")
        else:
            passage_strs.append(f"🚶 Vertical path at {p['start']} ({p['height']} tiles tall) - go {p['direction']}")
    
    return {
        "grid_size": f"{num_cols}x{num_rows}",
        "player_position": f"[{player_col},{player_row}]",
        "player_row": player_row,
        "player_col": player_col,
        "adjacent_tiles": {
            "north": f"[{player_col},{player_row-1}] = '{north_tile}'",
            "south": f"[{player_col},{player_row+1}] = '{south_tile}'",
            "east": f"[{player_col+1},{player_row}] = '{east_tile}'",
            "west": f"[{player_col-1},{player_row}] = '{west_tile}'"
        },
        "blocked_directions": blocked,
        "walkable_directions": walkable,
        "adjacent_exits": exits,
        "all_exit_tiles": o_tiles,
        "npc_tiles": npc_tiles,  # NEW: NPC positions for LLM context
        "passages": passage_strs  # Detected passages/chokepoints
    }


# ─── Constants ────────────────────────────────────────────────────────────────
LLM_TOTAL_TIMEOUT = 75  # Extended to 75s cycle timeout

# ─── Helper ───────────────────────────────────────────────────────────────────
async def call_llm_with_timeout(state_data: dict,
                                llm_timeout: float = STREAM_TIMEOUT,
                                total_timeout: float = LLM_TOTAL_TIMEOUT,
                                benchmark: Benchmark = None,
                                cycle_metrics: dict = None):
    """
    Run `llm_stream_action` in a worker thread and abort the whole thing
    (token‑counting, API call, streaming, parsing…) after `total_timeout` s.
    """
    loop = asyncio.get_running_loop()
    fn   = functools.partial(llm_stream_action, state_data, llm_timeout, benchmark, cycle_metrics)

    # Use custom executor to avoid blocking default executor on shutdown
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    try:
        # run blocking LLM code in a thread, wait with an asyncio timeout
        return await asyncio.wait_for(loop.run_in_executor(executor, fn),
                                      timeout=total_timeout)
    except asyncio.TimeoutError:
        log.error(f"llm_stream_action exceeded {total_timeout}s – skipping cycle.")
        executor.shutdown(wait=False)
        return None, None, None, None
    except Exception:
        executor.shutdown(wait=False)
        raise
    finally:
        executor.shutdown(wait=False)

def summarize_and_reset(benchmark: Benchmark = None, state_data: dict = None):
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

    # ═══════════════════════════════════════════════════════════════════════════
    # HANDLE EXPERT PATHFINDING & SELF-ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    extra_context = ""

    # 1. Log Self-Analysis
    self_analysis = json_object.get("self_analysis")
    if self_analysis:
        log.info(f"🛡️ SELF-ANALYSIS: {json.dumps(self_analysis, indent=2)}")
        if isinstance(self_analysis, dict):
            correction = self_analysis.get("correction_plan")
            if correction and correction != "None":
                extra_context += f"\n\n🛡️ SELF-CORRECTION PLAN: {correction}"

    # 2. Handle Plan Target Tile (BFS Pathfinding)
    target_tile_str = json_object.get("plan_target_tile")
    if target_tile_str and state_data:
        try:
            # Parse [x,y] from string like "[12, 15]" or "12,15"
            coords = [int(n) for n in re.findall(r'\d+', str(target_tile_str))]
            if len(coords) == 2:
                target_x, target_y = coords
                current_x, current_y = state_data.get("position", [0, 0])
                map_id = state_data.get("map_id")
                
                if map_id is not None:
                    log.info(f"🧭 Calculating BFS path from [{current_x},{current_y}] to [{target_x},{target_y}]...")
                    rom_path = get_rom_path()
                    # We might need to handle rom_path formatting
                    if not os.path.exists(rom_path):
                         # Try adding roms/ prefix if relative
                         rom_path = os.path.join("roms", rom_path) if not rom_path.startswith("roms") else rom_path

                    bfs_actions = find_path(rom_path, map_id, [current_x, current_y], [target_x, target_y])
                    
                    if bfs_actions:
                        log.info(f"✅ BFS Path Found: {bfs_actions}")
                        extra_context += f"\n\n💡 EXPERT SUGGESTED PATH to [{target_x},{target_y}]: {bfs_actions}\n(Execute this chain using specific chunks if too long)"
                        # Update the plan_target_tile in the summary text to confirm acceptance
                        summary_text += f"\n[System: Integrated path to {target_tile_str}]"
                    else:
                        log.warning(f"❌ BFS Path failed to find route to {target_tile_str}")
                        extra_context += f"\n\n⚠️ PATHFINDING FAILED: Could not calculate route to {target_tile_str}. Destination may be unreachable or in void."
            else:
                 log.warning(f"Invalid target tile format: {target_tile_str}")
        except Exception as e:
            log.error(f"Error executing BFS pathfinding: {e}", exc_info=True)

    benchInstructions = ""
    if benchmark is not None:
        benchInstructions = benchmark.instructions

    new_system_prompt_content = build_system_prompt(summary_text + extra_context, benchInstructions)
    chat_history = [{"role": "system", "content": new_system_prompt_content}]
    response_count = 0
    log.info("Chat history summarized and reset.")
    return json_object


def next_with_timeout(iterator, timeout: float):
    """Attempt to pull the first chunk from `iterator` within `timeout` seconds."""
    # Use manual executor management to avoid blocking on shutdown if thread hangs
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(lambda: next(iterator))
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        # Don't wait for stuck thread
        executor.shutdown(wait=False)
        raise TimeoutError(f"No chunk received in {timeout}s")
    finally:
        # Always shutdown, don't wait if it's somehow still running
        executor.shutdown(wait=False)


def llm_stream_action(state_data: dict, timeout: float = STREAM_TIMEOUT, benchmark: Benchmark = None, cycle_metrics: dict = None):
    """
    Determines and executes an action by querying an LLM.

    This function intelligently switches between streaming and non-streaming API calls.
    - For models supporting a 'reasoning_effort', it uses a non-streaming call to
      avoid timeouts while the model "thinks".
    - For other models, it streams the response for lower perceived latency.
    - For Z.AI mode, it optionally uses MCP vision server for image analysis.
    """
    if cycle_metrics is None:
        cycle_metrics = {}
    global response_count, tokens_used_session, chat_history, zai_vision_client, CURRENT_MODE, agent_requested_diff

    summary_json = None
    vision_analysis_for_ui = None  # Store raw vision analysis for UI display
    payload = copy.deepcopy(state_data)
    screenshot = payload.pop("screenshot", None)
    minimap = payload.pop("minimap", None)

    # Extract Z.AI specific image paths for MCP processing
    screenshot_path = payload.pop("screenshot_path", None)
    previous_screenshot_path = payload.pop("previous_screenshot_path", None)
    diff_pairs = payload.pop("diff_pairs", [])  # List of (prev_cycle, prev_path, curr_path) tuples
    minimap_path = payload.pop("minimap_path", None)

    if not MINIMAP_2D:
        print("Minimap 2D disabled, removing minimap_2d from payload.")
        payload.pop("minimap_2d", None)

    if not isinstance(payload, dict):
        log.error(f"Invalid state_data structure: {type(state_data)}")
        return None, None, None, None

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
                # Be SPECULATIVE about uncertain objects, HIGH CONFIDENCE required for doors/exits
                factual_prompt = (
                    "Analyze this Pokemon Red game screenshot. Output as JSON with these fields:\n\n"
                    "{\n"
                    '  "screen_type": "title|overworld|battle|menu|dialogue|name_entry",\n'
                    '  "readable_text": "any visible text, semicolon separated. ONLY what is perfectly legible.",\n'
                    '  "player_position": "describe player location in the scene",\n'
                    '  "nearby_objects": "objects RELATIVE TO PLAYER - e.g. bookshelf north of player, table to player east",\n'
                    '  "npcs": "NPCs RELATIVE TO PLAYER - e.g. NPC standing south of player; NPC to player left",\n'
                    '  "obstacles": "walls/trees/barriers RELATIVE TO PLAYER, semicolon separated",\n'
                    '  "ui_elements": "menus/cursors/hp bars, semicolon separated",\n'
                    '  "battle_info": "if battle: player_pokemon, player_hp, enemy_pokemon, enemy_hp, moves",\n'
                    '  "menu_cursor": "if menu: which option is highlighted",\n'
                    '  "navigation_notes": "doors/exits/red mats/stairs RELATIVE TO PLAYER - e.g. possible exit south of player",\n'
                    '  "black_space": "MAP BOUNDARIES - black areas are the edge of the map, NOT walkable or interactable"\n'
                    "}\n\n"
                    "CRITICAL RULES:\n"
                    "- Output ONLY valid JSON, no markdown formatting\n"
                    "- Do NOT use bullet points, use semicolons to separate list items\n"
                    "- Do NOT use emojis\n"
                    "- Do NOT use headers or bold text\n\n"
                    "UNCERTAINTY & SPECULATION (for nearby_objects):\n"
                    "- Be SPECULATIVE about object identification - use 'maybe', 'possibly', 'looks like'\n"
                    "- If you can't clearly identify something, say 'unclear sprite' or 'possibly a [guess]'\n"
                    "- Example: 'maybe a toilet or plant; possibly a bookshelf' instead of 'toilet; bookshelf'\n"
                    "- Pixel art is ambiguous - express uncertainty appropriately\n\n"
                    "EXIT DETECTION (navigation_notes) - SECONDARY TO MINIMAP:\n"
                    "- **CRITICAL**: Any RED RECTANGLE on the floor is likely an EXIT MAT (doormat)\n"
                    "- Red floor mats are warping tiles that teleport the player in/out of buildings\n"
                    "- If you see a red rectangular shape on the floor, report: 'possibly exit mat at [direction]'\n"
                    "- Do NOT just say 'red rectangular object' - infer it may be an EXIT MAT\n"
                    "- These mats are typically near the bottom/south edge of indoor areas\n"
                    "- Look for door frames, stairs, or cave openings as secondary exit indicators\n"
                    "- Report exits as possibilities: 'red shape at south - possibly exit mat'\n"
                    "- **BUILDING IDENTIFICATION BY TEXT SIGNS**: Roof colors vary by city - do NOT use roof color!\n"
                    "- Identify buildings by TEXT on facade: 'POKE' = Pokemon Center, 'MART' = Shop, 'GYM' = Gym\n"
                    "- If a building does NOT have 'POKE' text visible, it is likely NOT a Pokemon Center\n"
                    "- Use this as a BACKUP when minimap doesn't show 'O' markers\n"
                    "- The minimap 'O' tiles are the primary navigation source\n\n"
                    "TEXT & LOCATION - ONLY REPORT IF 100% CERTAIN:\n"
                    "- ONLY report text if you are 100% certain it exists - otherwise leave readable_text empty\n"
                    "- If text is unclear or questionable, use empty string - DO NOT GUESS\n"
                    "- Text must be EXACT pixel-for-pixel match. If partially cut off, do not infer.\n"
                    "- **NEVER** report 'POKEMON CENTER' or location names unless you CLEARLY see the text\n"
                    "- Do NOT try to identify what building/location you are in - the game state provides the map name\n"
                    "- Vision frequently hallucinates location names like 'Pokemon Center' - be extremely cautious\n"
                    "- If no visible text box with black borders exists, readable_text MUST be empty\n\n"
                    "POSITION RULES (CRITICAL - BE SPECIFIC):\n"
                    "- The PLAYER is ALWAYS at SCREEN CENTER. All positions are RELATIVE to the player.\n"
                    "- Use PRECISE DISTANCE + DIRECTION format:\n"
                    "  * 'directly 1 tile NORTH' = immediately above player (adjacent)\n"
                    "  * 'directly 1 tile EAST' = immediately right of player (adjacent)\n"
                    "  * 'directly 1 tile SOUTH' = immediately below player (adjacent)\n"
                    "  * 'directly 1 tile WEST' = immediately left of player (adjacent)\n"
                    "- For DIAGONAL positions, use COMPOUND directions:\n"
                    "  * 'NORTHEAST' = above and to the right\n"
                    "  * 'SOUTHWEST' = below and to the left\n"
                    "  * 'NORTHWEST' = above and to the left\n"
                    "  * 'SOUTHEAST' = below and to the right\n"
                    "- For DISTANCE, be specific:\n"
                    "  * 'directly 1 tile X' = immediately adjacent (touchingplayer)\n"
                    "  * '2-3 tiles X' = close but not adjacent\n"
                    "  * '4-6 tiles X' = moderate distance\n"
                    "  * 'far X' or 'distant X' = across the screen (7+ tiles)\n"
                    "- EXAMPLE FORMAT: 'NPC directly 1 tile SOUTH of player'\n"
                    "- EXAMPLE: 'bookshelf 3 tiles NORTHEAST of player'\n"
                    "- EXAMPLE: 'exit mat far SOUTH of player (at screen edge)'\n"
                    "- **PLAYER IDENTIFICATION (CRITICAL)**:\n"
                    "  * The RED-CLOTHED sprite at SCREEN CENTER is ALWAYS the PLAYER CHARACTER\n"
                    "  * The player's name is 'RED' and they wear red clothing with a hat\n"
                    "  * NEVER report 'NPC in red clothing' if they are at screen center - that IS the player\n"
                    "  * In the 'npcs' field, do NOT list the player - only list OTHER characters\n"
                    "- Empty fields should be empty strings\n\n"
                    "SCREEN TYPES (CRITICAL - read carefully before classifying):\n"
                    "- title: Pokemon logo, copyright text, no gameplay\n"
                    "- overworld: Player sprite visible walking around in the world. NPCs may be present.\n"
                    "- menu: START menu, item list, pokemon list\n"
                    "- dialogue: REQUIRE visible text box at bottom with black borders. If no box, it is NOT dialogue.\n"
                    "- name_entry: keyboard grid or preset name list. Press B to delete incorrect characters.\n"
                    "- **battle**: VERY STRICT REQUIREMENTS - ALL of these must be present:\n"
                    "  1. The screen is mostly WHITE/light colored (not the colorful overworld)\n"
                    "  2. Pokemon sprites are shown LARGE - not small 16x16 overworld sprites\n"
                    "  3. HP bars are visible showing HP values (e.g. 'HP: 25/25')\n"
                    "  4. Pokemon NAMES are displayed as text (e.g. 'CHARMANDER', 'PIDGEY')\n"
                    "  5. A battle menu (FIGHT/PKMN/ITEM/RUN) appears in the bottom-right\n"
                    "  OR dialogue text boxes with battle narration ('Wild PIDGEY appeared!')\n\n"
                    "**BATTLE vs OVERWORLD - DO NOT CONFUSE THESE:**\n"
                    "- If you see a COLORFUL TILED FLOOR (grass, buildings, paths) → it is OVERWORLD, not battle\n"
                    "- If you see small 16x16 pixel character sprites walking around → it is OVERWORLD\n"
                    "- NPCs in the overworld are NOT 'enemy sprites' - they are just NPCs\n"
                    "- Lab interiors, houses, caves with walkable floors are OVERWORLD\n"
                    "- Battle screens have a PLAIN WHITE/LIGHT background, not detailed tile graphics\n"
                    "- If there is no HP bar visible, it is NOT a battle\n"
                    "- If there is no Pokemon name text visible, it is NOT a battle\n\n"
                    "TALL GRASS RECOGNITION (CRITICAL for early game):\n"
                    "- Tall grass appears as DENSE DARK GREEN patterned/textured tiles\n"
                    "- In Pallet Town/Route 1, it looks like 'spiky' patches that stand out from flat ground\n"
                    "- It is distinct from the smooth light-colored path tiles\n"
                    "- If the player is standing IN tall grass, report: 'player in tall grass'\n"
                    "- Tall grass is where WILD POKEMON appear - you usually MUST enter it to find Pokemon\n"
                    "- If you see dense green textured tiles near the player, note: 'tall grass nearby [direction]'\n\n"
                    "BATTLE MENU CURSOR DETECTION (CRITICAL - reduces hallucination):\n"
                    "- The battle menu is a 2x2 grid in the bottom-right corner:\n"
                    "  TOP ROW:    FIGHT  |  PKMN\n"
                    "  BOTTOM ROW: ITEM   |  RUN\n"
                    "- The CURSOR is a right-pointing triangle (▶) that appears TO THE LEFT of the selected option\n"
                    "- Look CAREFULLY for the triangle position:\n"
                    "  * If ▶ is left of FIGHT → menu_cursor = 'FIGHT'\n"
                    "  * If ▶ is left of PKMN → menu_cursor = 'PKMN'\n"
                    "  * If ▶ is left of ITEM → menu_cursor = 'ITEM'\n"
                    "  * If ▶ is left of RUN → menu_cursor = 'RUN'\n"
                    "- DO NOT assume FIGHT is selected - LOOK FOR THE TRIANGLE\n"
                    "- The triangle is small but visible - check each row carefully\n"
                    "- If cursor is in the LEFT column = FIGHT or ITEM\n"
                    "- If cursor is in the RIGHT column = PKMN or RUN\n\n"
                    "NAME ENTRY KEYBOARD LAYOUT (if needed):\n"
                    "Row 1: A B C D E F G H I\n"
                    "Row 2: J K L M N O P Q R\n"
                    "Row 3: S T U V W X Y Z (space)\n"
                    "Row 4: x ( ) : ; [ ] PK MN\n"
                    "Row 5: - ? ! (boy) (girl) / . , ED\n"
                    "Row 6: (case toggle)\n"
                    "PREFER selecting preset names like RED or BLUE over typing custom names."
                )

              # CRITICAL: NEW MANDATORY VISION SYSTEM - Agent will NOT continue without vision
                try:
                    # Use the snapshot path if available, otherwise fallback (though snapshot should always be there now)
                    target_image_path = screenshot_path if screenshot_path else SAVED_SCREENSHOT_PATH
                    
                    # Update status for OBS widget
                    update_processing_status("ANALYZING VISION...")
                    t_vision_start = time.time()
                    vision_result = zai_vision_client.analyze_image_sync(target_image_path, factual_prompt)
                    t_vision_end = time.time()
                    cycle_metrics["vision"] = (t_vision_end - t_vision_start) * 1000
                    log.info(f"⏱️ Vision Analysis: {t_vision_end - t_vision_start:.2f}s")
                    
                    update_processing_status("THINKING...")

                    if vision_result:
                        # SUCCESS: Vision analysis completed successfully
                        log.info(f"✅ Z.AI MCP vision analysis completed: {len(vision_result)} chars")
                        log.info(f"Vision analysis preview: {vision_result[:200]}...")
                    else:
                        log.error("❌ Z.AI MCP vision analysis failed (returned None). Continuing without vision.")
                        vision_result = ""

                    # TEXT PROCESSING: Filter Japanese characters and truncate
                    processed_vision_result = vision_result

                    # Filter out Japanese characters and non-English text
                    processed_vision_result = re.sub(r'[\u3040-\u309F\u30A0-\u30FF]', '', processed_vision_result)

                    global agent_requested_diff
                    # Robust JSON extraction instead of brittle slicing
                    json_start = processed_vision_result.find('{')
                    json_end = processed_vision_result.rfind('}')
                    
                    if json_start != -1 and json_end != -1:
                        # Extract just the JSON part
                        processed_vision_result = processed_vision_result[json_start:json_end+1]
                    else:
                        # Fallback: legacy slicing if braces not found (unlikely but safe)
                        if len(processed_vision_result) > 31:
                            processed_vision_result = processed_vision_result[17:-14]

                    vision_analysis = f"Z.AI GLM-4.6 Vision Analysis: {processed_vision_result}"
                    vision_analysis_for_ui = processed_vision_result  # Store processed vision analysis for UI
                    payload["vision_analysis"] = vision_analysis
                    # Also add a more prominent vision field for better LLM recognition
                    payload["visual_context"] = processed_vision_result
                    
                    # Parse screen_type from vision JSON for dynamic prompting
                    try:
                        # Try to parse the vision result as JSON to extract screen_type
                        vision_json = json.loads(processed_vision_result)
                        detected_screen_type = vision_json.get("screen_type", "")
                        if detected_screen_type:
                            log.info(f"🖥️ Detected screen type: {detected_screen_type}")
                            payload["detected_screen_type"] = detected_screen_type
                    except json.JSONDecodeError:
                        # Vision result is not valid JSON, try regex extraction
                        screen_type_match = re.search(r'"screen_type"\s*:\s*"([^"]+)"', processed_vision_result)
                        if screen_type_match:
                            detected_screen_type = screen_type_match.group(1)
                            log.info(f"🖥️ Detected screen type (regex): {detected_screen_type}")
                            payload["detected_screen_type"] = detected_screen_type
                    
                    # ═══════════════════════════════════════════════════════════════
                    # SINGLE DIFF CHECK - Only run when agent requested it
                    # Sequential execution to prevent MCP response ID conflicts
                    # ═══════════════════════════════════════════════════════════════
                    global agent_requested_diff
                    if agent_requested_diff and diff_pairs:
                        log.info("🔄 Agent requested diff - running ui_diff_check")
                        try:
                            # Only use the most recent diff pair (N-1)
                            single_pair = diff_pairs[0] if diff_pairs else None
                            
                            if single_pair:
                                prev_cycle, prev_path, curr_path = single_pair
                                log.info(f"🔄 Running single ui_diff_check (cycle {prev_cycle} vs current)")
                                update_processing_status(f"COMPARING TO PREVIOUS CYCLE...")
                                
                                t_diff_start = time.time()
                                
                                try:
                                    result = zai_vision_client.ui_diff_check_sync(
                                        prev_path, curr_path, max_attempts=1, timeout=15
                                    )
                                    if result:
                                        # Clean up result
                                        cleaned = re.sub(r'[\u3040-\u309F\u30A0-\u30FF]', '', result)
                                        if len(cleaned) > 31:
                                            cleaned = cleaned[17:-14]
                                        log.info(f"UI Diff result: {cleaned}")
                                        
                                        # Add to payload
                                        payload["ui_changes_from_previous_cycle"] = cleaned
                                        payload["temporal_diffs"] = f"TEMPORAL CHANGES (vs cycle {prev_cycle}):\n{cleaned[:300]}"
                                        log.info(f"🔄 Diff completed for cycle {prev_cycle}")
                                    else:
                                        log.info("🔄 Diff returned no result")
                                except Exception as e:
                                    log.warning(f"Diff for cycle {prev_cycle} failed: {e}")
                                
                                t_diff_end = time.time()
                                cycle_metrics["diff"] = (t_diff_end - t_diff_start) * 1000
                                log.info(f"⏱️ UI Diff Check: {t_diff_end - t_diff_start:.2f}s")
                                
                        except Exception as diff_error:
                            log.warning(f"Multi-diff failed (non-critical): {diff_error}")
                        
                        # Reset flag after running
                        agent_requested_diff = False
                    elif diff_pairs:
                        log.debug("⏭️ Skipping ui_diff (agent did not request it) - saves ~15s")
                    else:
                        log.debug("No diff pairs available (first few cycles?)")

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
    
    # DYNAMIC PROMPT UPDATE: Rebuild system prompt with current context (Screen Type + Area Hint)
    detected_screen_type = payload.get("detected_screen_type", "")
    area_hint = state_data.get("area_hint", "")
    
    if chat_history and len(chat_history) > 0 and chat_history[0].get("role") == "system":
        # extract benchmark instruction if any (passed in global or arg? arg: benchmark)
        bench_instr = benchmark.instructions if benchmark else ""
        
        # Rebuild clean system prompt
        fresh_prompt = build_system_prompt(
            benchmarkInstruction=bench_instr,
            screen_type=detected_screen_type,
            area_hint=area_hint
        )
        
        chat_history[0] = {"role": "system", "content": fresh_prompt}
        log.info(f"📝 Updated System Prompt: Screen='{detected_screen_type}', Hint='{area_hint[:20] if area_hint else 'None'}...'")
    
    messages_for_api = chat_history + [current_user_message_api]

    # Token accounting
    call_input_tokens = calculate_prompt_tokens(messages_for_api)
    log.info(f"LLM call estimate: {call_input_tokens} input tokens; history turns: {len(chat_history)}")

    full_output = ""
    action = None
    analysis_text = None

    try:
        # Update status for OBS widget - now thinking
        update_processing_status("THINKING...")
        
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

                    # LLM API retry logic - retry up to 2 times on timeout
                    LLM_API_TIMEOUT = 40.0  # 40s timeout as requested
                    LLM_MAX_RETRIES = 2
                    response = None
                    last_error = None
                    
                    for llm_attempt in range(LLM_MAX_RETRIES + 1):
                        try:
                            t_llm_start = time.time()
                            with httpx.Client(timeout=LLM_API_TIMEOUT) as http_client:
                                response = http_client.post(
                                    f"{client.base_url}chat/completions",
                                    json=api_data,
                                    headers=headers
                                )
                            t_llm_end = time.time()
                            cycle_metrics["llm"] = (t_llm_end - t_llm_start) * 1000
                            log.info(f"⏱️ LLM Analysis: {t_llm_end - t_llm_start:.2f}s")
                            break  # Success - exit retry loop
                            
                        except httpx.ReadTimeout as e:
                            last_error = e
                            if llm_attempt < LLM_MAX_RETRIES:
                                log.warning(f"🔄 LLM API timeout (attempt {llm_attempt + 1}/{LLM_MAX_RETRIES + 1}). Retrying...")
                                time.sleep(1)  # Brief pause before retry
                            else:
                                log.error(f"❌ LLM API timeout after {LLM_MAX_RETRIES + 1} attempts")
                                raise e
                    
                    if response is None:
                        raise last_error or Exception("LLM API call failed with no response")

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
                t_llm_start = time.time()
                response = client.chat.completions.create(**kwargs)
                t_llm_end = time.time()
                cycle_metrics["llm"] = (t_llm_end - t_llm_start) * 1000
                log.info(f"⏱️ LLM Generation: {t_llm_end - t_llm_start:.2f}s")
                update_processing_status("EXECUTING...")
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
                return None, None, None, None

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
            return None, None, None, None

        log.info(f"LLM raw output length: {len(full_output)} chars")

        # Token accounting for the output
        output_tokens = count_tokens(full_output)
        tokens_used_session += call_input_tokens + output_tokens
        log.info(f"Used ~{output_tokens} output tokens; session total: {tokens_used_session}")

        user_hist_content = [text_segment] # Images are not saved in history
        
        # Compress history if repetitive action
        compressed = compress_chat_history(chat_history, full_output)
        
        if compressed:
             log.info(f"♻️ Compressed chat history (repetitive action): {full_output[:50]}...")
             # Do NOT append user message or new assistant message
        else:
             chat_history.append({"role": "user", "content": user_hist_content})
             chat_history.append({"role": "assistant", "content": full_output})

        # Cleanup history if window is reached
        response_count += 1
        if response_count >= CLEANUP_WINDOW:
            t_summarize_start = time.time()
            summary_json = summarize_and_reset(benchmark, state_data)
            t_summarize_end = time.time()
            if cycle_metrics is not None:
                cycle_metrics["summarization"] = (t_summarize_end - t_summarize_start) * 1000
            log.info(f"⏱️ Summarization: {t_summarize_end - t_summarize_start:.2f}s")
            response_count = 0 # Reset counter
            time.sleep(5)

        # Extract analysis section
        match = ANALYSIS_RE.search(full_output)
        if match:
            # Include the full tags so frontend can parse the JSON structure
            analysis_text = f"<game_analysis>{match.group(1).strip()}</game_analysis>"
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
                
                # Check if agent requested a diff for next cycle
                # Output format: {"action":"U;U;U;", "request_diff": true}
                request_diff_flag = parsed.get("request_diff", False)
                if request_diff_flag:
                    agent_requested_diff = True
                    log.info("🔍 Agent requested ui_diff for next cycle")

                # Use vision analysis from JSON if provided
                if vision_from_json and isinstance(vision_from_json, str):
                    vision_analysis_for_ui = vision_from_json

                if isinstance(act, str):
                    # Translate cardinal directions (N/S/E/W) to buttons (U/D/L/R)
                    act = translate_cardinal_to_buttons(act)
                    if ACTION_RE.match(act):
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

        # Fallback: Find ACTION line or last line matching ACTION_RE
        if action is None:
            lines = [line.strip() for line in full_output.splitlines() if line.strip()]
            if lines:
                # First try to find explicit ACTION line (e.g., "8. **ACTION**: A;" or "**ACTION**: R;R;A;")
                for line in lines:
                    # Look for ACTION: pattern (with or without ** markdown)
                    if 'ACTION' in line.upper() and ':' in line:
                        # Extract content after the colon
                        colon_idx = line.find(':')
                        if colon_idx != -1:
                            action_part = line[colon_idx + 1:].strip()
                            # Translate and match
                            translated = translate_cardinal_to_buttons(action_part)
                            match = ACTION_RE.match(translated)
                            if match:
                                action = match.group().rstrip(';') + ';'
                                log.info(f"✅ Found action in ACTION line: {action}")
                                break
                
                # Fall back to last line if no ACTION line found
                if action is None:
                    last = lines[-1]
                    translated_last = translate_cardinal_to_buttons(last)
                    match = ACTION_RE.match(translated_last)
                    if match and not translated_last.startswith('{'):
                        action = match.group().rstrip(';') + ';'

                # plain touch coords
                if action is None:
                    last = lines[-1]
                    if COORD_RE.match(last):
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
    global action_count, tokens_used_session, start_time, chat_history, SCREENSHOT_PATH, MINIMAP_PATH, SAVED_SCREENSHOT_PATH, SAVED_MINIMAP_PATH
    
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
        # Restore chat history if available
        if run_state.chat_history:
            chat_history = run_state.chat_history
            log.info(f"🔄 Restored chat history: {len(chat_history)} messages")
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

    # Set up status callback for real-time processing status updates
    # This allows llm_stream_action to broadcast status changes during vision processing
    def status_callback(status: str):
        state["processingStatus"] = status
        # Use asyncio to schedule the broadcast (we're in an async context)
        asyncio.create_task(broadcast_func({"processingStatus": status}))
    
    set_status_callback(status_callback)
    log.info("📢 Processing status callback initialized")

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

    # Helper function for parallel chat processing during LLM wait
    async def parallel_chat_processing(stop_event: asyncio.Event) -> int:
        """
        Process Twitch chat responses in parallel with the main LLM call.
        This keeps the stream active during the 10-40s LLM thinking phase.
        
        Returns the number of chat responses generated.
        """
        responses_generated = 0
        max_responses = 2  # Limit during parallel processing
        
        if not twitch_service.is_available or not chat_response_service.is_available:
            return 0
        
        try:
            while not stop_event.is_set() and responses_generated < max_responses:
                # Check for pending mentions
                pending = twitch_service.get_pending_mentions()
                if not pending:
                    # No messages - wait a bit before checking again
                    await asyncio.sleep(2.0)
                    continue
                
                # Process the oldest pending message
                chat_msg = pending[0]
                username = chat_msg.get("display_name", chat_msg.get("username", "viewer"))
                message = chat_msg.get("message", "")
                
                if not message:
                    twitch_service.mark_responded(chat_msg)
                    continue
                
                log.info(f"💬 [PARALLEL] Responding to @{username}: {message[:50]}...")
                
                try:
                    # Generate response using chat LLM (fast, not main LLM)
                    response = await chat_response_service.generate_response(username, message)
                    
                    if response:
                        # Send response to Twitch
                        await twitch_service.send_response(response)
                        log.info(f"💬 [PARALLEL] Sent: {response[:80]}...")
                        
                        # Play TTS for chat response if available
                        if tts_service.is_available:
                            await tts_service.synthesize(response)
                        
                        responses_generated += 1
                    
                    twitch_service.mark_responded(chat_msg)
                    
                except Exception as e:
                    log.warning(f"Parallel chat response error: {e}")
                    twitch_service.mark_responded(chat_msg)
                
                # Brief pause between responses
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            log.info("🛑 Parallel chat processing cancelled (LLM complete)")
        except Exception as e:
            log.error(f"Error in parallel chat processing: {e}")
        
        return responses_generated


    # Position history for stuck detection
    position_history = []
    
    # Track last action for failure replay
    last_action = None
    last_position = None

    b64_mm = None
    
    # Capture the main event loop for thread-safe callbacks
    loop = asyncio.get_running_loop()
    
    # Define thread-safe status callback for vision updates (called from executor threads)
    def status_callback(status: str):
        state["processingStatus"] = status
        # Use run_coroutine_threadsafe to schedule the async broadcast on the main loop
        # This is required because this callback is invoked from llm_stream_action running in a ThreadPoolExecutor
        asyncio.run_coroutine_threadsafe(broadcast_func({"processingStatus": status}), loop)

    # Set the global callback
    set_status_callback(status_callback)

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
            chat_history = [{"role": "system", "content": fresh_system_prompt}]
        else:
            # Restore chat history but replace the system prompt with fresh one
            chat_history = run_state.chat_history
            if chat_history and chat_history[0].get("role") == "system":
                chat_history[0] = {"role": "system", "content": fresh_system_prompt}
                log.info("🔄 Updated system prompt to latest version")
    else:
        chat_history = [{"role": "system", "content": fresh_system_prompt}]

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
        if CURRENT_MODE == "ZAI" and zai_vision_client:
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
        chat_stop_event = asyncio.Event()
        parallel_chat_task = asyncio.create_task(parallel_chat_processing(chat_stop_event))
        
        try:
            # Run the main LLM call
            action, game_analysis, summary_json, vision_analysis_for_ui = await call_llm_with_timeout(
                llm_input_state, 
                benchmark=benchmark,
                cycle_metrics=cycle_metrics
            )
        finally:
            # Signal chat task to stop and cancel if still running
            chat_stop_event.set()
            parallel_chat_task.cancel()
            try:
                parallel_responses = await parallel_chat_task
                if parallel_responses > 0:
                    log.info(f"💬 Sent {parallel_responses} chat responses during LLM processing")
            except asyncio.CancelledError:
                pass

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
            run_state.chat_history = chat_history[-20:]  # Keep last 20 messages
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
            from services.twitch_chat_service import TWITCH_TEST_MODE
            
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
                        # Generate a witty mock response in Lass's personality
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
                        
                        # Actually send to TTS!
                        if tts_service.is_available:
                            try:
                                await tts_service.synthesize_and_play(
                                    response_text,
                                    priority=tts_service.PRIORITY_CHAT_RESPONSE,
                                    wait=True
                                )
                                log.info(f"✅ [TEST] TTS response complete")
                            except Exception as tts_err:
                                log.warning(f"🔊 [TEST] TTS error: {tts_err}")
                        
                        # Broadcast to UI
                        chat_response_payload = {
                            "chat_response": {
                                "username": test_msg['display_name'],
                                "message": test_msg['message'],
                                "response": response_text,
                                "is_test": True,
                                "timestamp": int(time.time() * 1000)
                            }
                        }
                        await broadcast_func(chat_response_payload)
                        
                        # Short delay before next potential message (1-3 seconds)
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                
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
                    
                    # Queue TTS for the response (lower priority than game commentary)
                    if tts_service.is_available:
                        await tts_service.synthesize_and_play(
                            response_text,
                            priority=tts_service.PRIORITY_CHAT_RESPONSE,
                            wait=True
                        )
                    
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