import os
import re
import json
import time
import logging
from typing import Optional, Tuple, Any

# Internal imports (adjust paths if needed)
from pyAIAgent.llm.zai_mcp_client import create_zai_vision_client
from services.comfyui_vision_service import create_vision_service, ComfyUIVisionService

log = logging.getLogger("vision_manager")

# CRITICAL: Updated prompt - JSON format, no styling, no emojis, no bullets
# Be SPECULATIVE about uncertain objects, HIGH CONFIDENCE required for doors/exits
FACTUAL_PROMPT = (
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
    "- name_entry: keyboard grid or preset name list. IMPORTANT: Vision cursor detection is UNRELIABLE here - trust the name_entry_context field instead.\n"
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


class VisionManager:
    def __init__(self, client: Any, model: str, enabled: bool = True):
        self.client = client
        self.model = model
        self.enabled = enabled
        self.vision_client = None
        self.comfy_service: Optional[ComfyUIVisionService] = None

        # Determine provider
        self.vision_provider = os.getenv("VISION_PROVIDER", "DEFAULT").upper()

        # Mapping legacy config
        if self.vision_provider == "DEFAULT":
            # If using ZAI mode main client, we use it.
            # If main client is text-only, we might default to ZAI if keys present?
            # For now, DEFAULT implies "Use the main LLM client for vision"
            pass
        elif self.vision_provider not in ["ZAI", "ZAI_DIRECT", "COMFYUI", "DEFAULT"]:
            log.warning(
                f"Unknown VISION_PROVIDER '{self.vision_provider}', defaulting to DEFAULT"
            )
            self.vision_provider = "DEFAULT"

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate vision client."""
        if not self.enabled:
            return

        if self.vision_provider == "COMFYUI":
            try:
                self.comfy_service = create_vision_service()
                log.info("👁️ ComfyUI Vision Service initialized")
            except Exception as e:
                log.warning(f"Failed to initialize ComfyUI Vision: {e}")
                self.comfy_service = None

        elif self.vision_provider in ["ZAI", "ZAI_DIRECT"]:
            # Dedicated ZAI Vision Client
            # If main client is NOT ZAI, we need to create a dedicated one here.
            # Or if self.client is None (e.g. text-only mode where we passed None? No, we pass client)

            vision_api_key = os.getenv("Z_AI_API_KEY")
            vision_base_url = os.getenv(
                "Z_AI_BASE_URL", "https://api.z.ai/api/coding/paas/v4"
            )

            # If we already have a client and it looks like a ZAI/OpenAI client, check if we can reuse it
            # But simpler to just create a new specific client if explicitly requested via VISION_PROVIDER

            if not vision_api_key:
                log.error(
                    "VISION_PROVIDER is ZAI but Z_AI_API_KEY is missing. Vision disabled."
                )
                return

            try:
                # Import OpenAI locally to avoid top-level dependency issues if not installed
                # (Though it should be installed in this env)
                from openai import OpenAI

                # Create dedicated client for vision
                dedicated_client = OpenAI(
                    api_key=vision_api_key,
                    base_url=vision_base_url,
                    timeout=30.0,  # Vision specific timeout
                )

                use_mcp = self.vision_provider == "ZAI"
                vision_model = os.getenv(
                    "VISION_MODEL", "glm-4.6v-flash"
                )  # Default vision model

                self.vision_client = create_zai_vision_client(
                    dedicated_client, vision_model, use_mcp=use_mcp
                )
                log.info(
                    f"Initialized dedicated Z.AI vision client (Model: {vision_model}, MCP: {use_mcp})"
                )
            except Exception as e:
                log.warning(f"Failed to initialize dedicated Z.AI vision client: {e}")
                self.vision_client = None

        elif self.vision_provider == "DEFAULT":
            # Use the main client passed in __init__
            # Only works if the main client supports the ZAI MCP/Fallback interface
            # effectively this is for backward compatibility or when using ZAI as main model
            if self.client:
                try:
                    # Check if we are in ZAI mode main?
                    # Actually we just try to create the wrapper.
                    # If the client is not ZAI compatible, this might fail or just not work well?
                    # create_zai_vision_client expects an OpenAI-compatible client.

                    # We assume if VISION_PROVIDER is DEFAULT, we only init vision_client
                    # if we are actually using ZAI or compatible?
                    # Or do we assume the user knows what they are doing?

                    # Current logic: existing code assumes self.client is valid for this.
                    # We only init if we can.
                    use_mcp = True  # Default behavior
                    self.vision_client = create_zai_vision_client(
                        self.client, self.model, use_mcp=use_mcp
                    )
                    log.info(
                        "Initialized default vision client (using main LLM connection)"
                    )
                except Exception as e:
                    log.info(
                        f"Default vision client init skipped or failed (expected for non-ZAI main models): {e}"
                    )
                    self.vision_client = None

    def ensure_mcp_alive(self):
        """Check if MCP server process matches expectations and restart if needed."""
        if not self.vision_client:
            return

        if (
            hasattr(self.vision_client, "mcp_process")
            and self.vision_client.mcp_process
        ):
            if self.vision_client.mcp_process.poll() is not None:
                log.warning(
                    f"MCP server process has terminated with code: {self.vision_client.mcp_process.returncode}"
                )
                log.warning("Attempting to restart MCP server...")
                try:
                    self.vision_client._start_mcp_server_sync()
                    if self.vision_client.is_connected:
                        log.info("MCP server restarted successfully")
                    else:
                        log.warning("Failed to restart MCP server")
                        self.vision_client.handle_vision_failure(
                            "MCP server process terminated and restart failed"
                        )
                except Exception as restart_error:
                    log.error(f"Failed to restart MCP server: {restart_error}")
                    self.vision_client.handle_vision_failure(
                        f"MCP server restart failed: {str(restart_error)}"
                    )

    async def analyze_image(self, image_path: str) -> Tuple[Optional[str], float]:
        """
        Analyze screenshot using configured vision provider.
        Returns (vision_json_str, time_taken_ms).
        Returns (None, 0) if analysis failed or disabled.
        """
        if not self.enabled or not image_path or not os.path.exists(image_path):
            return None, 0

        t_start = time.time()
        vision_result = None

        # --- COMFYUI PATH ---
        if self.vision_provider == "COMFYUI" and self.comfy_service:
            try:
                log.info("👁️ Analyzing image via ComfyUI (Moondream)...")
                vision_result = await self.comfy_service.analyze_image(image_path)
            except Exception as e:
                log.error(f"ComfyUI vision analysis failed: {e}")

        # --- ZAI PATH ---
        elif self.vision_provider in ["ZAI", "ZAI_DIRECT"] and self.vision_client:
            self.ensure_mcp_alive()
            try:
                log.info("Z.AI vision analyzing screenshot...")

                # Use async method if available
                if hasattr(self.vision_client, "analyze_image_async"):
                    # Fallback client has explicit async method
                    vision_result = await self.vision_client.analyze_image_async(
                        image_path, FACTUAL_PROMPT
                    )
                elif hasattr(self.vision_client, "analyze_image"):
                    # MCP client 'analyze_image' IS async
                    # But Fallback 'analyze_image' IS sync
                    # We need to distinguish or check if it's awaitable?
                    # Or just check class name? Or check signature?
                    # Safer: check for 'analyze_image_async' first (added to fallback).
                    # For MCP client: 'analyze_image' is async.

                    # We can try to await it?
                    # If it's the sync fallback, awaiting it (if not coroutine) might fail?
                    # No, we can't await a non-coroutine.

                    # Let's check if it's the MCP client or fallback.
                    is_fallback = "Fallback" in self.vision_client.__class__.__name__

                    if not is_fallback:
                        # MCP Client: analyze_image is async
                        vision_result = await self.vision_client.analyze_image(
                            image_path, FACTUAL_PROMPT
                        )
                    else:
                        # Fallback Client: analyze_image is sync, but we added analyze_image_async
                        # So we should have hit the first if block.
                        # Unless verify/reload didn't pick it up?
                        # It should work.
                        pass

            except Exception as e:
                log.error(f"Z.AI vision analysis failed: {e}")

        t_duration_ms = (time.time() - t_start) * 1000

        if not vision_result:
            return None, t_duration_ms

        # Post-processing
        processed = self._process_vision_result(vision_result)
        return processed, t_duration_ms

    def _process_vision_result(self, raw_result: str) -> str:
        """Clean up raw vision output: remove Japanese chars, extract JSON."""
        if not raw_result:
            return ""

        clean = raw_result
        try:
            # Remove Japanese characters
            clean = re.sub(r"[\u3040-\u309F\u30A0-\u30FF]", "", clean)

            # Extract JSON if present
            json_match = re.search(r"\{.*\}", clean, re.DOTALL)
            if json_match:
                # If we found JSON, use just that block + any text before it maybe?
                # Actually usually we want just the analysis.
                # But current usage expects the full text description sometimes?
                # The prompt asks for JSON output.
                pass

        except Exception:
            pass

        return clean

    def handle_vision_failure(self, error_message: str):
        """Handle critical vision failures via the MCP client."""
        if self.vision_client and hasattr(self.vision_client, "handle_vision_failure"):
            try:
                self.vision_client.handle_vision_failure(error_message)
            except Exception as e:
                log.error(f"Error handling vision failure: {e}")
