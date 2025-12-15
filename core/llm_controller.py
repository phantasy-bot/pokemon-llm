import os
import json
import time
import base64
import copy
import asyncio
import datetime
import logging
import re
import concurrent.futures
import functools
import httpx
from typing import Dict, Any, Optional, List, Tuple

from core.token_counter import count_tokens, calculate_prompt_tokens
from core.prompts import build_system_prompt, get_summary_prompt
from core.vision_manager import VisionManager
from core.memory.manager import MemoryManager
# from core.benchmark import Benchmark # Avoid circular import if Benchmark is not strictly typed here
from pyAIAgent.navigation import touch_controls_path_find

log = logging.getLogger('llm_controller')

# Regex constants
ACTION_RE = re.compile(r'^[LRUDABSTt](?:;[LRUDABSTt])*;?')
COORD_RE = re.compile(r'^([0-9]),([0-8])$')
ANALYSIS_RE = re.compile(r"<game_analysis>([\s\S]*?)</game_analysis>", re.IGNORECASE)

class LLMController:
    def __init__(self, 
                 client: Any, 
                 vision_manager: VisionManager, 
                 memory_manager: MemoryManager,
                 config: Dict[str, Any]):
        """
        Initialize LLM Controller with dependencies and configuration.
        config expected keys:
            mode: str (e.g. "ZAI", "OPENAI")
            model: str
            temperature: float
            max_tokens: int
            is_local: bool
            reasoning_enabled: bool
            reasoning_effort: str
            uses_default_temp: bool
            uses_max_completion_tokens: bool
            minimap_enabled: bool
            minimap_2d: bool
            cleanup_window: int
            system_prompt_unsupported: bool
        """
        self.client = client
        self.vision_manager = vision_manager
        self.memory_manager = memory_manager
        self.config = config
        
        # State
        self.chat_history: List[Dict] = []
        self.agent_requested_diff = False
        self.response_count = 0
        self.tokens_used_session = 0
        self._status_callback = None
        self._vision_callback = None

    def set_status_callback(self, callback):
        self._status_callback = callback

    def set_vision_callback(self, callback):
        """Set callback to be called when vision analysis completes.
        
        Callback signature: (vision_text: str, screenshot_b64: str, new_status: str) -> None
        The new_status is bundled with vision_log for atomic UI update.
        """
        self._vision_callback = callback

    def update_processing_status(self, status: str):
        if self._status_callback:
            self._status_callback(status)

    def broadcast_vision_result(self, vision_text: str, screenshot_b64: str = None, new_status: str = ""):
        """Broadcast vision analysis result immediately when available.
        
        Args:
            vision_text: The vision analysis text
            screenshot_b64: Base64 encoded screenshot
            new_status: New processing status to bundle with the broadcast (e.g., 'THINKING...')
        """
        if self._vision_callback:
            self._vision_callback(vision_text, screenshot_b64, new_status)

    async def call_with_timeout(self, state_data: dict, 
                              llm_timeout: float = 30.0, 
                              total_timeout: float = 75.0, 
                              benchmark: Any = None, 
                              cycle_metrics: dict = None) -> Tuple:
        """Run stream_action in a thread with timeout."""
        loop = asyncio.get_running_loop()
        fn = functools.partial(self.stream_action, state_data, llm_timeout, benchmark, cycle_metrics)
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            return await asyncio.wait_for(loop.run_in_executor(executor, fn), timeout=total_timeout)
        except asyncio.TimeoutError:
            log.error(f"llm_stream_action exceeded {total_timeout}s - skipping cycle.")
            executor.shutdown(wait=False)
            return None, None, None, None
        except Exception:
            executor.shutdown(wait=False)
            raise
        finally:
            executor.shutdown(wait=False)

    def compress_chat_history(self, new_assistant_content: str) -> bool:
        """
        Attempts to compress chat history by merging consecutive identical assistant actions.
        Returns True if compressed.
        """
        if not self.chat_history:
            return False
            
        last_msg = self.chat_history[-1]
        if last_msg["role"] != "assistant":
            return False

        content = last_msg["content"]
        if not isinstance(content, str):
            return False
        
        match = re.search(r' \(x(\d+)\)$', content)
        current_count = 1
        clean_content = content
        
        if match:
            current_count = int(match.group(1))
            clean_content = content[:match.start()]
        
        if clean_content.strip() == new_assistant_content.strip():
            if len(clean_content) < 150:
                new_count = current_count + 1
                last_msg["content"] = f"{clean_content} (x{new_count})"
                return True
                
        return False

    def summarize_and_reset(self, benchmark: Any = None, state_data: dict = None) -> Optional[str]:
        """Condenses history, updates system prompt, resets history."""
        if not self.chat_history:
            return None

        # Build summary prompt
        summary_prompt = get_summary_prompt()
        
        # We need a temporary history for summarization
        temp_history = copy.deepcopy(self.chat_history)
        # Append summary request
        temp_history.append({"role": "user", "content": summary_prompt})
        
        # Calculate tokens
        input_tokens = calculate_prompt_tokens(temp_history)
        
        log.info(f"Summary Context: {len(temp_history)} messages ({input_tokens} tokens)")
        
        summary_text = None
        try:
            # Non-streaming call for summary
            kwargs = {
                "model": self.config["model"],
                "messages": temp_history,
                "temperature": 0.3, # Low temp for factual summary
                "max_tokens": 1000
            }
            
            if self.config.get("uses_max_completion_tokens"):
                 kwargs.pop("max_tokens")
                 kwargs["max_completion_tokens"] = 1000

            # Handling ZAI/Legacy API diffs could be here, but usually summary uses standard client
            response = self.client.chat.completions.create(**kwargs)
            summary_text = response.choices[0].message.content.strip()
            
            # Update token usage
            output_tokens = count_tokens(summary_text)
            self.tokens_used_session += input_tokens + output_tokens
            
            log.info(f"📝 Summary generated: {summary_text[:100]}...")
            
        except Exception as e:
            log.error(f"Summarization failed: {e}")
            summary_text = f"Failed to generate summary. Last known state: {state_data.get('map_id', 'unknown') if state_data else 'unknown'}"

        # Reset history
        self.chat_history.clear()
        
        # Rebuild system prompt
        bench_instr = benchmark.instructions if benchmark else ""
        screen_type = state_data.get("detected_screen_type", "") if state_data else ""
        area_hint = state_data.get("area_hint", "") if state_data else ""
        
        fresh_prompt = build_system_prompt(
            benchmarkInstruction=bench_instr,
            screen_type=screen_type,
            area_hint=area_hint
        )
        
        # Insert System Prompt
        self.chat_history.append({"role": "system", "content": fresh_prompt})
        
        # Insert Summary if available
        if summary_text:
             self.chat_history.append({"role": "system", "content": f"PREVIOUS SESSION SUMMARY:\n{summary_text}"})
        
        # Parse summary_text as JSON and return the dict directly
        # so primaryGoal, secondaryGoal, etc. are accessible
        if summary_text:
            try:
                parsed = json.loads(summary_text)
                log.info(f"📋 Parsed summary JSON with keys: {list(parsed.keys())}")
                return parsed
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse summary JSON: {e}")
                return {"summary": summary_text}  # Fallback
        return None

    def stream_action(self, state_data: dict, timeout: float, benchmark: Any, cycle_metrics: dict):
        """
        Determines and executes an action by querying an LLM.
        """
        if cycle_metrics is None:
            cycle_metrics = {}
        
        summary_json = None
        vision_analysis_for_ui = None
        payload = copy.deepcopy(state_data)
        
        # Pop large items
        screenshot = payload.pop("screenshot", None)
        minimap = payload.pop("minimap", None)
        screenshot_path = payload.pop("screenshot_path", None)
        payload.pop("previous_screenshot_path", None)
        diff_pairs = payload.pop("diff_pairs", [])
        payload.pop("minimap_path", None)
        
        if not self.config.get("minimap_2d", True):
            payload.pop("minimap_2d", None)
            
        if not isinstance(payload, dict):
            log.error(f"Invalid state_data structure: {type(state_data)}")
            return None, None, None, None

        # Vision Analysis
        vision_analysis = ""
        
        if self.vision_manager and screenshot_path and os.path.exists(screenshot_path):
            try:
                self.update_processing_status("ANALYZING VISION...")
                
                # Vision analysis call
                processed_vision_result, duration_ms = self.vision_manager.analyze_image(screenshot_path)
                
                cycle_metrics["vision"] = duration_ms
                log.info(f"⏱️ Vision Analysis: {duration_ms/1000:.2f}s")
                
                if processed_vision_result:
                     log.info(f"✅ Vision Analysis Completed: {len(processed_vision_result)} chars")
                else:
                     processed_vision_result = ""
                
                vision_analysis = f"Vision Analysis: {processed_vision_result}"
                vision_analysis_for_ui = processed_vision_result
                payload["vision_analysis"] = vision_analysis
                payload["visual_context"] = processed_vision_result
                
                # Broadcast vision result immediately (before LLM processing)
                # Bundle processingStatus: "THINKING..." with vision_log for atomic UI update
                # This ensures the screenshot is revealed exactly when vision completes
                screenshot_b64 = state_data.get("screenshot_base64")
                self.broadcast_vision_result(vision_analysis_for_ui, screenshot_b64, "THINKING...")
                
                # Dynamic prompt updates from vision result
                try:
                    vision_json = json.loads(processed_vision_result)
                    detected_screen_type = vision_json.get("screen_type", "")
                    if detected_screen_type:
                        payload["detected_screen_type"] = detected_screen_type
                except json.JSONDecodeError:
                    match = re.search(r'"screen_type"\s*:\s*"([^"]+)"', processed_vision_result)
                    if match:
                         payload["detected_screen_type"] = match.group(1)
                
                # Diff Check
                if self.agent_requested_diff and diff_pairs:
                     log.info("🔄 Agent requested diff - running ui_diff_check")
                     try:
                         single_pair = diff_pairs[0] if diff_pairs else None
                         if single_pair:
                             prev_cycle, prev_path, curr_path = single_pair
                             self.update_processing_status(f"COMPARING TO PREVIOUS CYCLE...")
                             t_diff_start = time.time()
                             
                             result = self.vision_manager.ui_diff_check(prev_path, curr_path, max_attempts=1, timeout=15)
                             
                             t_diff_end = time.time()
                             cycle_metrics["diff"] = (t_diff_end - t_diff_start) * 1000
                             
                             if result:
                                 # Basic cleanup
                                 cleaned = re.sub(r'[\u3040-\u309F\u30A0-\u30FF]', '', result)
                                 if len(cleaned) > 200: cleaned = cleaned[:200]
                                 log.info(f"UI Diff result: {cleaned}")
                                 payload["ui_changes_from_previous_cycle"] = cleaned
                                 
                     except Exception as e:
                         log.warning(f"Diff failed: {e}")
                     self.agent_requested_diff = False
                elif diff_pairs:
                     pass # save time
                
            except Exception as e:
                log.error(f"Vision analysis failed: {e}")
                payload["vision_analysis"] = "[Vision analysis failed]"
                # Handle critical failure if needed
                self.vision_manager.handle_vision_failure(str(e))

        elif self.config["mode"] == "ZAI":
             # ZAI mode but no vision client
             log.warning("ZAI mode detected but no vision available")
             payload["vision_analysis"] = "[Vision client not initialized]"
        
        elif self.config["mode"] == "ZAI_DIRECT":
             # ZAI_DIRECT mode: Images are embedded directly in API call
             # No separate vision analysis needed - the model handles both vision and analysis
             log.info("ZAI_DIRECT mode: Image will be embedded directly in API call (combined vision+text)")
             # Update status to show we're doing combined analysis
             self.update_processing_status("ANALYZING (COMBINED)...")
             # Set placeholder vision analysis so action logging works in llmdriver
             vision_analysis_for_ui = "[Combined vision+text analysis - image embedded in LLM call]"

        # Build Message
        image_parts = []
        text_content = json.dumps(payload)
        
        # Include vision analysis directly in text for ZAI
        if self.config["mode"] == "ZAI" and vision_analysis:
             text_content = f"{text_content}\n\nIMPORTANT VISION ANALYSIS:\n{vision_analysis}"
        
        current_content = [{"type": "text", "text": text_content}]
        
        if screenshot and isinstance(screenshot.get("image_url"), dict):
            current_content.append({"type": "image_url", "image_url": screenshot["image_url"]})
        if minimap and self.config.get("minimap_enabled", False) and isinstance(minimap.get("image_url"), dict):
            current_content.append({"type": "image_url", "image_url": minimap["image_url"]})
            
        current_user_message = {"role": "user", "content": current_content}
        
        # Dynamic System Prompt Update
        detected_screen_type = payload.get("detected_screen_type", "")
        area_hint = state_data.get("area_hint", "")
        if self.chat_history and self.chat_history[0].get("role") == "system":
            bench_instr = benchmark.instructions if benchmark else ""
            fresh_prompt = build_system_prompt(bench_instr, detected_screen_type, area_hint)
            self.chat_history[0] = {"role": "system", "content": fresh_prompt}
            
        messages = self.chat_history + [current_user_message]
        
        # Token Accounting
        input_tokens = calculate_prompt_tokens(messages)
        log.info(f"LLM Input Tokens: {input_tokens}")
        
        # API Call
        full_output = ""
        action = None
        analysis_text = None
        
        try:
            self.update_processing_status("THINKING...")
            
            kwargs = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": self.config["temperature"],
                "timeout": timeout
            }
            
            if self.config.get("uses_max_completion_tokens"):
                 kwargs["max_completion_tokens"] = self.config["max_tokens"]
            else:
                 kwargs["max_tokens"] = self.config["max_tokens"]
                 
            if self.config.get("uses_default_temp"):
                 kwargs["temperature"] = 1.0
                 
            supports_reasoning = self.config.get("reasoning_enabled", False)
            
            if supports_reasoning:
                log.info("Using reasoning model (non-streaming).")
                kwargs["stream"] = False
                
                # ZAI Specific Logic
                if self.config["mode"] == "ZAI":
                     full_output = self._call_zai_api(kwargs, cycle_metrics)
                else:
                     kwargs["reasoning_effort"] = self.config.get("reasoning_effort", "medium")
                     t_start = time.time()
                     response = self.client.chat.completions.create(**kwargs)
                     cycle_metrics["llm"] = (time.time() - t_start) * 1000
                     full_output = response.choices[0].message.content
            
            elif self.config["mode"] == "ZAI_DIRECT":
                # ZAI_DIRECT: Use non-streaming for more reliable multimodal responses
                log.info("Using ZAI_DIRECT mode (non-streaming with embedded images).")
                kwargs["stream"] = False
                t_start = time.time()
                response = self.client.chat.completions.create(**kwargs)
                cycle_metrics["llm"] = (time.time() - t_start) * 1000
                full_output = response.choices[0].message.content
                log.info(f"⏱️ ZAI_DIRECT LLM: {cycle_metrics['llm']/1000:.2f}s")
                     
            else:
                log.info("Using standard model (streaming).")
                kwargs["stream"] = True
                t_start = time.time()
                response = self.client.chat.completions.create(**kwargs)
                full_output = self._handle_streaming(response, timeout)
                cycle_metrics["llm"] = (time.time() - t_start) * 1000

        except Exception as e:
            log.error(f"LLM Interaction failed: {e}", exc_info=True)
            return None, None, None, None
            
        if not full_output:
            return None, None, None, None
            
        # Post-Processing
        output_tokens = count_tokens(full_output)
        self.tokens_used_session += input_tokens + output_tokens
        
        # History Management
        user_hist_content = [{"type": "text", "text": text_content}] # No images in history
        
        if not self.compress_chat_history(full_output):
             self.chat_history.append({"role": "user", "content": user_hist_content})
             self.chat_history.append({"role": "assistant", "content": full_output})
             
        # Cleanup
        self.response_count += 1
        cleanup_window = self.config.get("cleanup_window", 10)
        if self.response_count >= cleanup_window:
             summary_json = self.summarize_and_reset(benchmark, state_data)
             self.response_count = 0
             time.sleep(1) # Brief pause
             
        # Extraction
        analysis_text = self._extract_analysis(full_output)
        action, action_vision_analysis, req_diff = self._extract_action(full_output, state_data)
        
        if req_diff:
             self.agent_requested_diff = True
             
        if action_vision_analysis:
             vision_analysis_for_ui = action_vision_analysis
             
        return action, analysis_text, summary_json, vision_analysis_for_ui

    def _call_zai_api(self, kwargs: dict, cycle_metrics: dict) -> str:
        """Handle ZAI specific API call (manual HTTP to support thinking param)."""
        # ... Reimplementation of ZAI logic ...
        # For brevity, implementing a simplified version that matches llmdriver logic
        # Construct ZAI kwargs
        zai_kwargs = {
            "model": kwargs.get("model"),
            "messages": kwargs.get("messages"),
            "stream": False,
            "max_tokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "thinking": {"type": "enabled"}
        }
        
        # Convert to text-only messages
        text_only_messages = []
        for msg in zai_kwargs["messages"]:
            content = msg.get("content")
            if isinstance(content, list):
                text = ""
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                         text += item.get("text", "")
                text_only_messages.append({"role": msg.get("role"), "content": text})
            else:
                text_only_messages.append(msg)
                
        api_data = {
            "model": zai_kwargs["model"],
            "messages": text_only_messages,
            "max_tokens": zai_kwargs.get("max_tokens"),
            "temperature": zai_kwargs.get("temperature")
        }
        
        headers = {
            "Authorization": f"Bearer {self.client.api_key}",
            "Content-Type": "application/json"
        }
        
        t_start = time.time()
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=40.0) as http_client:
                     response = http_client.post(
                         f"{self.client.base_url}chat/completions",
                         json=api_data, headers=headers
                     )
                cycle_metrics["llm"] = (time.time() - t_start) * 1000
                
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    raise Exception(f"ZAI API Error: {response.text}")
                    
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as e:
                # Connection was closed by server or network error - retry
                if attempt < max_retries - 1:
                    log.warning(f"ZAI connection error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    log.error(f"ZAI connection failed after {max_retries} attempts: {e}")
                    raise e
            except Exception as e:
                raise e

    def _handle_streaming(self, response, timeout) -> str:
        """Handle streaming response."""
        full_output = ""
        start_time = time.time()
        print(">>> ", end="", flush=True)
        try:
             for chunk in response:
                 if time.time() - start_time > timeout:
                      raise TimeoutError("Stream timeout")
                 delta = chunk.choices[0].delta.content
                 if delta:
                      print(delta, end="", flush=True)
                      full_output += delta
        except Exception as e:
             log.warning(f"Stream interrupted: {e}")
        print("")
        return full_output.strip()

    def _extract_analysis(self, full_output: str) -> str:
        match = ANALYSIS_RE.search(full_output)
        if match:
             return f"<game_analysis>{match.group(1).strip()}</game_analysis>"
        # Fallback to non-JSON lines
        lines = [l for l in full_output.splitlines() if not l.strip().startswith('{') and not l.strip().endswith('}')]
        return "\n".join(lines) if lines else "No analysis available"

    def _extract_action(self, full_output: str, state_data: dict) -> Tuple[Optional[str], Optional[str], bool]:
        action = None
        vision = None
        req_diff = False
        
        # JSON search
        for json_match in re.finditer(r'\{[^{}]*\}', full_output):
             try:
                 parsed = json.loads(json_match.group())
                 if "action" in parsed:
                      act = parsed["action"]
                      act = self._translate_cardinal(act)
                      if ACTION_RE.match(act):
                           action = act
                 if "touch" in parsed:
                      # Touch logic
                      if COORD_RE.match(parsed["touch"]):
                           coords = [int(i) for i in parsed["touch"].split(",")]
                           action = touch_controls_path_find(state_data.get("map_id", 0), state_data["position"], coords)
                 if "vision_analysis" in parsed:
                      vision = parsed["vision_analysis"]
                 if parsed.get("request_diff"):
                      req_diff = True
                 if action: break
             except: continue
             
        # Fallback regex
        if not action:
             for line in full_output.splitlines():
                  if "ACTION" in line.upper() and ":" in line:
                       part = line.split(":", 1)[1].strip()
                       part = self._translate_cardinal(part)
                       if ACTION_RE.match(part):
                            action = part.rstrip(';') + ';'
                            break
                            
        return action, vision, req_diff

    def _translate_cardinal(self, action_str: str) -> str:
        """Translate cardinal directions to buttons."""
        if not action_str: return ""
        
        mapping = {'N': 'U', 'S': 'D', 'E': 'R', 'W': 'L'}
        # Only translate S->D if other cardinals present to avoid START ambiguity
        has_cardinal = any(c in action_str for c in "NEW")
        
        parts = action_str.split(';')
        translated = []
        for p in parts:
             p = p.strip()
             if not p: continue
             if p in mapping:
                  if p == 'S' and not has_cardinal:
                       translated.append(p) # Keep S as START
                  else:
                       translated.append(mapping[p])
             else:
                  translated.append(p)
                  
        return ";".join(translated)
