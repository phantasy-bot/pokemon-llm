# --- comfyui_tts_service.py ---
"""
ComfyUI Text-to-Speech Service for Pokemon LLM Agent.
Triggers TTS workflows on a ComfyUI server to generate speech from text.
"""

import asyncio
import os
import json
import time
import uuid
import logging
import subprocess
import platform
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx

log = logging.getLogger("comfyui_tts")


@dataclass
class TTSRequest:
    """Represents a pending TTS request with async synthesis support."""
    text: str
    request_id: str
    priority: int  # Higher = more important (game commentary > chat response)
    created_at: float
    cycle_id: int = 0  # Which game cycle this request came from
    audio_path: Optional[str] = None
    completed: bool = False
    error: Optional[str] = None
    synthesis_task: Optional[asyncio.Task] = None  # Background synthesis task


class ComfyUITTSService:
    """
    Text-to-Speech service using ComfyUI as the backend.
    
    Triggers TTS workflows on ComfyUI and retrieves generated audio.
    Supports both localhost and hosted ComfyUI instances.
    """
    
    # Priority levels
    PRIORITY_COMMENTARY = 100  # Game commentary (highest)
    PRIORITY_CHAT_RESPONSE = 50  # Chat responses
    PRIORITY_LOW = 10  # Low priority items
    
    def __init__(
        self,
        base_url: str = None,
        workflow_path: str = None,
        output_dir: str = None,
        timeout: float = 10.0,  # Reduced from 60s for faster fallback
        on_playback_start: callable = None,
        audio_speed: float = None,
        audio_pitch: float = None
    ):
        """
        Initialize the ComfyUI TTS service.
        
        Args:
            base_url: ComfyUI server URL (e.g., "http://localhost:8188")
            workflow_path: Path to the TTS workflow JSON file
            output_dir: Directory to save generated audio files
            timeout: Request timeout in seconds
            on_playback_start: Callback(text, duration_ms) called when audio starts playing
            audio_speed: Playback speed multiplier (e.g., 1.1 = 10% faster)
            audio_pitch: Pitch shift in semitones (e.g., 2 = 2 semitones higher)
        """
        self.base_url = (base_url or os.getenv("COMFYUI_URL", "http://localhost:8188")).rstrip("/")
        self.workflow_path = workflow_path or os.getenv("COMFYUI_TTS_WORKFLOW", "")
        self.output_dir = output_dir or os.getenv("COMFYUI_OUTPUT_DIR", "tts_output")
        self.timeout = timeout
        
        # Callback for UI sync - called when playback starts with (text, duration_ms)
        self.on_playback_start = on_playback_start
        
        # Audio post-processing settings (from env or args)
        self.audio_speed = audio_speed or float(os.getenv("TTS_AUDIO_SPEED", "1.0"))
        self.audio_pitch = audio_pitch or float(os.getenv("TTS_AUDIO_PITCH", "0"))  # In semitones
        
        # Request queue (priority queue simulation with sorting)
        self._queue: List[TTSRequest] = []
        self._processing = False
        self._client: Optional[httpx.AsyncClient] = None
        
        # Audio playback process tracking for cancellation
        self._audio_process: Optional[subprocess.Popen] = None
        self._current_request: Optional[TTSRequest] = None
        self._current_audio_path: Optional[str] = None  # Track for post-playback cleanup
        self._cancelled = False
        
        # Lock to ensure TTS requests are serialized (no overlap)
        self._tts_lock = asyncio.Lock()
        
        # Cached workflow template
        self._workflow_template: Optional[dict] = None
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Cleanup stale audio files from previous runs
        self._cleanup_stale_audio()
        
        # Check if configured and enabled
        # TTS_ENABLED defaults to true if not set, for backward compatibility
        tts_enabled = os.getenv("TTS_ENABLED", "true").lower() in ("true", "1", "yes")
        self._is_configured = bool(self.base_url) and tts_enabled
        
        if not tts_enabled:
            log.info("🔇 TTS disabled via TTS_ENABLED=false in .env")
        elif not self._is_configured:
            log.warning("ComfyUI TTS not configured. Set COMFYUI_URL in .env")
    
    def _cleanup_stale_audio(self) -> None:
        """
        Remove any leftover audio files from previous sessions.
        Called on startup to ensure clean state.
        """
        if not os.path.exists(self.output_dir):
            return
        
        cleaned = 0
        for f in os.listdir(self.output_dir):
            if f.endswith(('.flac', '.mp3', '.wav')):
                try:
                    os.remove(os.path.join(self.output_dir, f))
                    cleaned += 1
                except Exception as e:
                    log.warning(f"Failed to cleanup {f}: {e}")
        
        if cleaned > 0:
            log.info(f"♻️ Cleaned up {cleaned} stale audio files from {self.output_dir}")
    
    def _cleanup_audio_file(self, audio_path: str) -> None:
        """
        Remove an audio file after playback.
        Called after wait_for_playback completes.
        """
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                log.debug(f"♻️ Cleaned up: {os.path.basename(audio_path)}")
            except Exception as e:
                log.warning(f"Failed to cleanup audio: {e}")
    
    def _get_audio_duration_ms(self, audio_path: str) -> Optional[int]:
        """
        Get audio duration in milliseconds.
        Uses mutagen for FLAC/MP3/WAV support.
        
        Returns:
            Duration in milliseconds, or None if detection fails
        """
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(audio_path)
            if audio and audio.info:
                duration_ms = int(audio.info.length * 1000)
                log.info(f"🔊 Audio duration: {duration_ms}ms ({audio.info.length:.2f}s)")
                return duration_ms
        except ImportError:
            log.warning("mutagen not installed, trying fallback audio duration detection")
            # Fallback for FLAC using soundfile or wave
            try:
                import soundfile as sf
                with sf.SoundFile(audio_path) as f:
                    duration_ms = int((len(f) / f.samplerate) * 1000)
                    log.info(f"🔊 Audio duration (soundfile): {duration_ms}ms")
                    return duration_ms
            except ImportError:
                log.warning("soundfile not installed, cannot detect audio duration")
            except Exception as e:
                log.warning(f"soundfile fallback failed: {e}")
        except Exception as e:
            log.warning(f"Failed to get audio duration: {e}")
        
        # Estimate based on text length (rough fallback: ~150ms per character)
        return None
    
    def _process_audio_speed_pitch(self, audio_path: str) -> str:
        """
        Apply speed and pitch adjustments to audio using ffmpeg.
        
        Uses the atempo filter for speed and asetrate+aresample for pitch.
        
        Args:
            audio_path: Path to the input audio file
            
        Returns:
            Path to processed audio file (or original if processing fails/not needed)
        """
        # Skip if no processing needed
        if self.audio_speed == 1.0 and self.audio_pitch == 0:
            return audio_path
        
        try:
            # Build output path
            base, ext = os.path.splitext(audio_path)
            processed_path = f"{base}_processed{ext}"
            
            # Build ffmpeg filter chain
            filters = []
            
            # Detect actual sample rate from the audio file
            original_sample_rate = 44100  # Default fallback
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(audio_path)
                if audio and audio.info and hasattr(audio.info, 'sample_rate'):
                    original_sample_rate = audio.info.sample_rate
                    log.info(f"🔊 Detected sample rate: {original_sample_rate}Hz")
            except Exception as e:
                log.warning(f"🔊 Could not detect sample rate, using 44100Hz default: {e}")
            
            # Pitch adjustment using asetrate + aresample + atempo compensation
            # NOTE: Pitch shifting with asetrate is imperfect. For best results, 
            # use small values (0.5 to 2 semitones) or install rubberband library.
            if self.audio_pitch != 0:
                pitch_factor = 2 ** (self.audio_pitch / 12)
                log.info(f"🔊 Pitch factor for {self.audio_pitch} semitones: {pitch_factor:.6f}")
                
                # Method: Change sample rate to shift pitch, then resample back and 
                # compensate tempo with atempo (1/pitch_factor)
                new_rate = int(original_sample_rate * pitch_factor)
                filters.append(f"asetrate={new_rate}")
                filters.append(f"aresample={original_sample_rate}")
                
                # Tempo compensation: pitch up = speed up, so we slow down to compensate
                tempo_comp = 1.0 / pitch_factor
                log.info(f"🔊 Tempo compensation: {tempo_comp:.6f}")
                
                # Apply tempo compensation (atempo range is 0.5-2.0)
                if tempo_comp <= 0.5 or tempo_comp >= 2.0:
                    log.warning(f"🔊 Large pitch shift ({self.audio_pitch} semitones) may cause quality issues")
                
                comp = tempo_comp
                while comp > 2.0:
                    filters.append("atempo=2.0")
                    comp /= 2.0
                while comp < 0.5:
                    filters.append("atempo=0.5")
                    comp *= 2.0
                if abs(comp - 1.0) > 0.001:
                    filters.append(f"atempo={comp:.6f}")
            
            # Speed adjustment using atempo (applied after pitch compensation)
            if self.audio_speed != 1.0:
                speed = self.audio_speed
                # atempo only supports 0.5-2.0, so chain multiple if needed
                while speed > 2.0:
                    filters.append("atempo=2.0")
                    speed /= 2.0
                while speed < 0.5:
                    filters.append("atempo=0.5")
                    speed *= 2.0
                if speed != 1.0:
                    filters.append(f"atempo={speed:.4f}")
            
            if not filters:
                return audio_path
            
            filter_str = ",".join(filters)
            log.info(f"🔊 Processing audio: speed={self.audio_speed}x, pitch={self.audio_pitch} semitones")
            log.info(f"🔊 FFmpeg filter chain: {filter_str}")
            
            # Run ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", filter_str,
                "-acodec", "flac" if audio_path.endswith(".flac") else "libmp3lame",
                processed_path
            ]
            
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(processed_path):
                log.info(f"🔊 Audio processed successfully: {processed_path}")
                # Remove original, rename processed
                os.remove(audio_path)
                os.rename(processed_path, audio_path)
                return audio_path
            else:
                log.warning(f"🔊 FFmpeg processing failed: {result.stderr.decode()[:200]}")
                return audio_path
                
        except FileNotFoundError:
            log.warning("🔊 ffmpeg not found, skipping audio processing. Install with: brew install ffmpeg")
            return audio_path
        except subprocess.TimeoutExpired:
            log.warning("🔊 FFmpeg processing timed out")
            return audio_path
        except Exception as e:
            log.warning(f"🔊 Audio processing failed: {e}")
            return audio_path
    
    @property
    def is_available(self) -> bool:
        """Check if TTS service is configured."""
        return self._is_configured
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    def cancel_current(self):
        """
        Cancel the currently playing audio and any pending ComfyUI workflow.
        Called when a higher priority TTS request comes in (e.g., new cycle commentary).
        """
        self._cancelled = True
        
        if self._audio_process and self._audio_process.poll() is None:
            try:
                self._audio_process.terminate()
                log.info("🔇 Cancelled current TTS playback")
            except Exception as e:
                log.warning(f"Error terminating audio process: {e}")
        
        self._audio_process = None
        
        # Also cancel any pending ComfyUI workflow via /interrupt endpoint
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                response = client.post(f"{self.base_url}/interrupt")
                if response.status_code == 200:
                    log.info("🔇 Cancelled pending ComfyUI TTS workflow")
                else:
                    log.debug(f"ComfyUI interrupt returned {response.status_code}")
        except Exception as e:
            log.debug(f"Could not interrupt ComfyUI workflow: {e}")
    
    def play_audio_ephemeral(self, audio_path: str) -> bool:
        """
        Play audio file ephemerally (no file retention).
        Uses system audio player (afplay on macOS, aplay/paplay on Linux).
        
        Args:
            audio_path: Path to the audio file
        
        Returns:
            True if playback started successfully
        """
        if not os.path.exists(audio_path):
            log.warning(f"Audio file not found: {audio_path}")
            return False
        
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                cmd = ["afplay", audio_path]
            elif system == "Linux":
                # Try paplay (PulseAudio) first, fall back to aplay
                cmd = ["paplay", audio_path]
            else:
                log.warning(f"Unsupported platform for audio playback: {system}")
                return False
            
            # Start audio playback as subprocess
            self._audio_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            log.info(f"🔊 Playing audio: {os.path.basename(audio_path)}")
            return True
            
        except FileNotFoundError:
            log.warning(f"Audio player not found. Install afplay (macOS) or paplay/aplay (Linux)")
            return False
        except Exception as e:
            log.error(f"Error playing audio: {e}")
            return False
    
    async def wait_for_playback(self, timeout: float = 30.0) -> bool:
        """
        Wait for current audio playback to complete.
        
        Args:
            timeout: Maximum seconds to wait
        
        Returns:
            True if playback completed, False if cancelled or timeout
        """
        if not self._audio_process:
            return True
        
        start = time.time()
        while time.time() - start < timeout:
            if self._cancelled:
                return False
            
            if self._audio_process.poll() is not None:
                return True
            
            await asyncio.sleep(0.1)
        
        # Timeout - kill process
        try:
            self._audio_process.terminate()
        except:
            pass
        
        return False
    
    async def check_connection(self) -> bool:
        """
        Check if ComfyUI server is reachable.
        Returns True if connected, False otherwise.
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/system_stats")
            return response.status_code == 200
        except Exception as e:
            log.warning(f"ComfyUI connection check failed: {e}")
            return False
    
    def load_workflow(self) -> Optional[dict]:
        """
        Load the TTS workflow template from file.
        Converts ComfyUI export format (nodes array) to API format (prompt dict).
        """
        if self._workflow_template:
            return self._workflow_template
        
        if not self.workflow_path or not os.path.exists(self.workflow_path):
            log.warning(f"TTS workflow not found: {self.workflow_path}")
            return None
        
        try:
            with open(self.workflow_path, 'r') as f:
                raw_workflow = json.load(f)
            log.info(f"Loaded TTS workflow from: {self.workflow_path}")
            
            # Check if this is export format (has 'nodes' array) vs API format (has 'prompt' dict)
            if "nodes" in raw_workflow:
                # Convert from export format to API format
                api_format = self._convert_export_to_api_format(raw_workflow)
                self._workflow_template = api_format
                log.info(f"Converted workflow from export format to API format ({len(api_format)} nodes)")
            else:
                self._workflow_template = raw_workflow
            
            return self._workflow_template
        except Exception as e:
            log.error(f"Failed to load TTS workflow: {e}")
            return None
    
    def _convert_export_to_api_format(self, export_workflow: dict) -> dict:
        """
        Convert ComfyUI export format (nodes array) to API prompt format (dict of node dicts).
        
        Export format has:
        - "nodes": [{"id": 1, "type": "NodeType", "widgets_values": [...], "inputs": [...]}]
        - "links": [[link_id, from_node, from_slot, to_node, to_slot, type]]
        
        API format expects:
        - {"1": {"class_type": "NodeType", "inputs": {...}}}
        """
        nodes = export_workflow.get("nodes", [])
        links = export_workflow.get("links", [])
        
        # Build link lookup: (to_node_id, to_slot_idx) -> (from_node_id, from_slot_idx)
        link_map = {}
        for link in links:
            if len(link) >= 5:
                link_id, from_node, from_slot, to_node, to_slot, *_ = link
                link_map[link_id] = (from_node, from_slot)
        
        api_prompt = {}
        
        for node in nodes:
            node_id = str(node.get("id"))
            node_type = node.get("type")
            
            # Skip Note nodes - they're not part of the execution graph
            if node_type == "Note":
                continue
            
            # Build inputs dict from connected links and widget values
            inputs = {}
            
            # Get connected inputs from links
            node_inputs = node.get("inputs", [])
            for input_def in node_inputs:
                input_name = input_def.get("name")
                link_id = input_def.get("link")
                if link_id and link_id in link_map:
                    from_node, from_slot = link_map[link_id]
                    inputs[input_name] = [str(from_node), from_slot]
            
            # Store widget values for later text injection
            # For ChatterboxTTS: widgets_values is [model, text, max_len, cfg_temp, temp, top_p, top_k, ...]
            widget_values = node.get("widgets_values", [])
            
            # Map widget values to input names based on node type
            if node_type == "ChatterboxTTS":
                # Server's current ChatterboxTTS required inputs (from /object_info):
                # model_pack_name, text, max_new_tokens, flow_cfg_scale, exaggeration, 
                # temperature, cfg_weight, repetition_penalty, min_p, top_p, seed, use_watermark
                # Optional: audio_prompt
                
                # Use server's default values to ensure compatibility
                chatterbox_defaults = {
                    "model_pack_name": "resembleai_default_voice",
                    "text": "Hello, this is a test of Chatterbox TTS.",
                    "max_new_tokens": 1000,
                    "flow_cfg_scale": 0.7,
                    "exaggeration": 0.5,
                    "temperature": 0.8,
                    "cfg_weight": 0.5,
                    "repetition_penalty": 1.2,
                    "min_p": 0.05,
                    "top_p": 1.0,
                    "seed": 0,
                    "use_watermark": False
                }
                
                # Start with defaults
                inputs.update(chatterbox_defaults)
                
                # Try to map old widget values if present
                # Old format: [model, text, max_len, cfg_temp, temp, top_p, top_k, exaggeration, speed, seed, ...]
                if len(widget_values) >= 2:
                    if isinstance(widget_values[0], str):
                        inputs["model_pack_name"] = widget_values[0]
                    if isinstance(widget_values[1], str):
                        inputs["text"] = widget_values[1]
            elif node_type == "LoadAudio":
                # LoadAudio: audio file path
                if widget_values:
                    inputs["audio"] = widget_values[0]
            elif node_type == "SaveAudio":
                # SaveAudio: filename_prefix
                if widget_values:
                    inputs["filename_prefix"] = widget_values[0]
            
            api_prompt[node_id] = {
                "class_type": node_type,
                "inputs": inputs
            }
        
        return api_prompt
    
    def _prepare_workflow(self, text: str, workflow: dict = None) -> dict:
        """
        Prepare the workflow with the given text input.
        
        For ChatterboxTTS: injects text into the 'text' field of ChatterboxTTS nodes.
        
        Args:
            text: Text to synthesize
            workflow: Workflow template (uses cached if not provided)
        
        Returns:
            Modified workflow dict ready for execution (wrapped in {"prompt": ...})
        """
        if workflow is None:
            workflow = self.load_workflow()
        
        if workflow is None:
            log.warning("No workflow template - TTS cannot proceed.")
            return None
        
        # Deep copy to avoid modifying the template
        import copy
        prepared = copy.deepcopy(workflow)
        
        # Text injection patterns for various TTS nodes
        text_input_keys = [
            "text", "input_text", "prompt", "tts_text", 
            "speech_text", "content", "message"
        ]
        
        text_injected = False
        for node_id, node_data in prepared.items():
            if isinstance(node_data, dict):
                class_type = node_data.get("class_type", "")
                inputs = node_data.get("inputs", {})
                
                # Inject text into ChatterboxTTS or similar TTS nodes
                if "TTS" in class_type or "Chatterbox" in class_type:
                    if "text" in inputs:
                        inputs["text"] = text
                        text_injected = True
                        log.debug(f"Injected text into {class_type} node {node_id}")
                else:
                    # Try generic text input keys
                    for key in text_input_keys:
                        if key in inputs and isinstance(inputs[key], str):
                            inputs[key] = text
                            text_injected = True
                            log.debug(f"Injected text into node {node_id}, field {key}")
                            break
        
        if not text_injected:
            log.warning("Could not find text input field in workflow. TTS may not work correctly.")
        
        # Return in API format
        return {"prompt": prepared}
    
    async def queue_tts(
        self,
        text: str,
        priority: int = None,
        cycle_id: int = 0
    ) -> TTSRequest:
        """
        Queue a TTS request.
        
        Args:
            text: Text to synthesize
            priority: Request priority (higher = more important)
            cycle_id: The game cycle this request is from (for pruning)
        
        Returns:
            TTSRequest object for tracking
        """
        if priority is None:
            priority = self.PRIORITY_CHAT_RESPONSE
        
        request = TTSRequest(
            text=text,
            request_id=str(uuid.uuid4())[:8],
            priority=priority,
            created_at=time.time(),
            cycle_id=cycle_id
        )
        
        self._queue.append(request)
        # Sort by priority (highest first)
        self._queue.sort(key=lambda r: -r.priority)
        
        log.info(f"🔊 Queued TTS (priority={priority}, cycle={cycle_id}): {text[:50]}...")
        
        return request
    
    # Maximum queue size for chat responses (persists across cycles)
    MAX_QUEUE_SIZE = 4
    
    async def queue_and_start_synthesis(
        self,
        text: str,
        priority: int = None,
        cycle_id: int = 0
    ) -> Optional[TTSRequest]:
        """
        Queue a TTS request AND start background synthesis immediately.
        Does not wait for synthesis to complete - returns immediately.
        
        Use get_next_ready_audio() to retrieve completed audio.
        
        Args:
            text: Text to synthesize
            priority: Request priority
            cycle_id: The game cycle this request is from
        
        Returns:
            TTSRequest with synthesis_task started, or None if queue full
        """
        # Prune old items first
        self.prune_old_items(current_cycle=cycle_id)
        
        # Check queue size limit
        pending = [r for r in self._queue if not r.completed]
        if len(pending) >= self.MAX_QUEUE_SIZE:
            log.info(f"⏳ TTS queue full ({len(pending)}/{self.MAX_QUEUE_SIZE}), skipping")
            return None
        
        # Queue the request
        request = await self.queue_tts(text, priority, cycle_id)
        
        # Start synthesis in background
        async def _synthesize():
            try:
                audio_path = await self.synthesize_speech(request.text)
                request.audio_path = audio_path
                request.completed = True
                log.info(f"✅ Background TTS ready: {request.request_id} -> {audio_path}")
            except Exception as e:
                request.error = str(e)
                request.completed = True
                log.error(f"❌ Background TTS failed: {request.request_id}: {e}")
        
        request.synthesis_task = asyncio.create_task(_synthesize())
        log.info(f"🚀 Started background synthesis: {request.request_id}")
        
        return request
    
    def get_next_ready_audio(self) -> Optional[TTSRequest]:
        """
        Get the next completed TTS request that has audio ready.
        Removes it from the queue.
        
        Returns:
            TTSRequest with audio_path populated, or None if none ready
        """
        for i, request in enumerate(self._queue):
            if request.completed and request.audio_path and not request.error:
                self._queue.pop(i)
                log.info(f"🎵 Returning ready audio: {request.request_id}")
                return request
        return None
    
    def prune_old_items(self, current_cycle: int) -> int:
        """
        Remove old TTS items from previous cycles (keep max 1 prev cycle).
        Also enforces MAX_QUEUE_SIZE.
        
        Args:
            current_cycle: The current game cycle number
        
        Returns:
            Number of items pruned
        """
        original_count = len(self._queue)
        
        # Keep items from current cycle and previous cycle only
        min_cycle = max(0, current_cycle - 1)
        self._queue = [r for r in self._queue if r.cycle_id >= min_cycle]
        
        # Also enforce max size (keep newest)
        if len(self._queue) > self.MAX_QUEUE_SIZE:
            # Cancel synthesis tasks for items we're removing
            for request in self._queue[self.MAX_QUEUE_SIZE:]:
                if request.synthesis_task and not request.synthesis_task.done():
                    request.synthesis_task.cancel()
            self._queue = self._queue[:self.MAX_QUEUE_SIZE]
        
        pruned = original_count - len(self._queue)
        if pruned > 0:
            log.info(f"♻️ Pruned {pruned} old TTS items (keeping cycle >= {min_cycle})")
        
        return pruned
    
    def cancel_pending_chat_responses(self) -> int:
        """
        Cancel all pending chat response synthesis (for game commentary priority).
        Keeps the queue but cancels in-progress synthesis tasks.
        
        Returns:
            Number of tasks cancelled
        """
        cancelled = 0
        for request in self._queue:
            if request.priority < self.PRIORITY_COMMENTARY:  # Only chat responses
                if request.synthesis_task and not request.synthesis_task.done():
                    request.synthesis_task.cancel()
                    cancelled += 1
        
        if cancelled > 0:
            log.info(f"🔇 Cancelled {cancelled} pending chat TTS synthesis tasks")
        
        return cancelled
    
    def get_queue_status(self) -> dict:
        """Get queue status for debugging."""
        return {
            "total": len(self._queue),
            "pending": len([r for r in self._queue if not r.completed]),
            "ready": len([r for r in self._queue if r.completed and r.audio_path]),
            "errors": len([r for r in self._queue if r.error])
        }
    
    async def play_ready_audio(self, request: TTSRequest, wait: bool = True) -> bool:
        """
        Play audio from a completed TTSRequest.
        
        Args:
            request: TTSRequest with audio_path populated
            wait: If True, wait for playback to complete
        
        Returns:
            True if playback completed successfully
        """
        if not request or not request.audio_path:
            log.warning("🔊 No audio path in request")
            return False
        
        audio_path = request.audio_path
        
        # Apply speed/pitch processing
        audio_path = self._process_audio_speed_pitch(audio_path)
        
        # Get duration for UI sync
        duration_ms = self._get_audio_duration_ms(audio_path)
        
        # Notify UI that playback is about to start
        if self.on_playback_start and duration_ms:
            try:
                log.info(f"🔊 Calling on_playback_start: text={request.text[:30]}..., duration={duration_ms}ms")
                await self.on_playback_start(request.text, duration_ms)
            except Exception as cb_err:
                log.warning(f"🔊 on_playback_start callback error: {cb_err}")
        
        # Play the audio
        if not self.play_audio_ephemeral(audio_path):
            log.warning("🔊 play_audio_ephemeral returned False")
            return False
        
        if wait:
            completed = await self.wait_for_playback()
            # Cleanup audio file after playback
            self._cleanup_audio_file(audio_path)
            return completed
        
        return True

    async def process_queue(self) -> Optional[TTSRequest]:
        """
        Process the next item in the TTS queue.
        
        Returns:
            Completed TTSRequest or None if queue is empty.
        """
        if not self._queue:
            return None
        
        if self._processing:
            log.debug("TTS already processing, skipping")
            return None
        
        self._processing = True
        request = self._queue.pop(0)
        
        try:
            audio_path = await self.synthesize_speech(request.text)
            request.audio_path = audio_path
            request.completed = True
            log.info(f"✅ TTS complete: {request.request_id} -> {audio_path}")
        except Exception as e:
            request.error = str(e)
            log.error(f"❌ TTS failed for {request.request_id}: {e}")
        finally:
            self._processing = False
        
        return request
    
    async def synthesize_speech(self, text: str) -> Optional[str]:
        """
        Synthesize speech from text using ComfyUI.
        
        Args:
            text: Text to convert to speech
        
        Returns:
            Path to generated audio file, or None if failed.
        """
        if not self.is_available:
            log.warning("TTS service not available")
            return None
        
        # Check connection
        if not await self.check_connection():
            log.error("ComfyUI server not reachable")
            return None
        
        # Prepare workflow
        workflow = self._prepare_workflow(text)
        
        if workflow is None:
            log.error("Failed to prepare TTS workflow")
            return None
        
        try:
            client = await self._get_client()
            
            # Queue the workflow - _prepare_workflow already returns {"prompt": ...} format
            prompt_response = await client.post(
                f"{self.base_url}/prompt",
                json=workflow
            )
            
            if prompt_response.status_code != 200:
                log.error(f"Failed to queue workflow: {prompt_response.text}")
                return None
            
            prompt_result = prompt_response.json()
            prompt_id = prompt_result.get("prompt_id")
            
            if not prompt_id:
                log.error("No prompt_id in response")
                return None
            
            log.info(f"Queued ComfyUI workflow: {prompt_id}")
            
            # Poll for completion
            audio_path = await self._wait_for_completion(prompt_id)
            return audio_path
            
        except Exception as e:
            log.error(f"TTS synthesis error: {e}")
            return None
    
    async def _wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 0.5,
        max_wait: float = 60.0
    ) -> Optional[str]:
        """
        Wait for a ComfyUI workflow to complete and download the output audio.
        
        Args:
            prompt_id: The prompt ID to monitor
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
        
        Returns:
            Path to downloaded audio file, or None if failed/timeout.
        """
        client = await self._get_client()
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check history for completion
                history_response = await client.get(
                    f"{self.base_url}/history/{prompt_id}"
                )
                
                if history_response.status_code == 200:
                    history = history_response.json()
                    
                    if prompt_id in history:
                        prompt_history = history[prompt_id]
                        outputs = prompt_history.get("outputs", {})
                        
                        # Check if we have outputs (indicates completion)
                        if outputs:
                            log.debug(f"Workflow completed, outputs: {list(outputs.keys())}")
                            
                            # Look for audio output in any node
                            for node_id, node_output in outputs.items():
                                # Handle both 'audio' and 'audios' keys
                                audio_list = node_output.get("audio") or node_output.get("audios", [])
                                if not isinstance(audio_list, list):
                                    audio_list = [audio_list]
                                
                                for audio_data in audio_list:
                                    if isinstance(audio_data, dict):
                                        filename = audio_data.get("filename")
                                        subfolder = audio_data.get("subfolder", "")
                                        audio_type = audio_data.get("type", "output")
                                        
                                        if filename:
                                            # Download the audio file from ComfyUI server
                                            local_path = await self._download_audio(
                                                filename, subfolder, audio_type
                                            )
                                            if local_path:
                                                return local_path
                            
                            # No audio found in outputs
                            log.warning(f"Workflow completed but no audio output found. Outputs: {outputs}")
                            return None
                        
                        # Check for error status
                        status_info = prompt_history.get("status", {})
                        if status_info.get("status_str") == "error":
                            messages = status_info.get("messages", [])
                            log.error(f"Workflow error: {messages}")
                            return None
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                log.warning(f"Error checking workflow status: {e}")
                await asyncio.sleep(poll_interval)
        
        log.warning(f"Timeout waiting for workflow {prompt_id}")
        return None
    
    async def _download_audio(
        self,
        filename: str,
        subfolder: str = "",
        file_type: str = "output"
    ) -> Optional[str]:
        """
        Download audio file from ComfyUI server.
        
        Args:
            filename: Name of the audio file
            subfolder: Subfolder within output directory
            file_type: 'output' or 'input'
        
        Returns:
            Local path to downloaded file, or None if failed.
        """
        try:
            client = await self._get_client()
            
            # Build download URL
            params = {
                "filename": filename,
                "type": file_type
            }
            if subfolder:
                params["subfolder"] = subfolder
            
            download_url = f"{self.base_url}/view"
            log.info(f"Downloading audio from ComfyUI: {filename}")
            
            response = await client.get(download_url, params=params)
            
            if response.status_code == 200:
                # Save to local output directory
                local_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                local_path = os.path.join(self.output_dir, local_filename)
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                log.info(f"Downloaded audio to: {local_path}")
                
                # Apply speed/pitch adjustments if configured
                local_path = self._process_audio_speed_pitch(local_path)
                
                return local_path
            else:
                log.error(f"Failed to download audio: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            log.error(f"Error downloading audio: {e}")
            return None
    
    async def clear_queue(self):
        """Clear all pending TTS requests."""
        cleared = len(self._queue)
        self._queue.clear()
        log.info(f"Cleared {cleared} pending TTS requests")
    
    async def synthesize_and_play(
        self,
        text: str,
        priority: int = None,
        wait: bool = True
    ) -> bool:
        """
        Synthesize speech and play it ephemerally (no file retention needed by caller).
        
        This is the main method for TTS playback - handles synthesis, playback,
        and waiting for completion.
        
        Args:
            text: Text to synthesize
            priority: Priority level (PRIORITY_COMMENTARY or PRIORITY_CHAT_RESPONSE)
            wait: If True, wait for playback to complete before returning
        
        Returns:
            True if synthesis and playback started successfully
        """
        if not self.is_available:
            log.warning("TTS service not available")
            return False
        
        if priority is None:
            priority = self.PRIORITY_CHAT_RESPONSE
        
        # Acquire lock to ensure TTS requests are serialized (no overlap)
        async with self._tts_lock:
            # Reset cancelled flag for new request
            self._cancelled = False
            total_start = time.time()
            
            # Log the request
            log.info(f"🔊 TTS START: synthesizing (priority={priority}): {text[:50]}...")
            
            try:
                # Synthesize speech
                synthesis_start = time.time()
                audio_path = await self.synthesize_speech(text)
                synthesis_time = time.time() - synthesis_start
                
                if not audio_path:
                    log.warning(f"🔊 TTS FAILED: synthesis returned no audio path after {synthesis_time:.2f}s")
                    return False
                
                log.info(f"🔊 TTS Synthesis complete: {synthesis_time:.2f}s -> {audio_path}")
                
                # Check if cancelled during synthesis
                if self._cancelled:
                    log.info("🔇 TTS cancelled during synthesis")
                    return False
                
                # Get audio duration for UI sync
                duration_ms = self._get_audio_duration_ms(audio_path)
                
                # Notify UI that playback is about to start (for typewriter sync)
                if self.on_playback_start and duration_ms:
                    try:
                        log.info(f"🔊 Calling on_playback_start callback: text={text[:30]}..., duration={duration_ms}ms")
                        await self.on_playback_start(text, duration_ms)
                    except Exception as cb_err:
                        log.warning(f"🔊 on_playback_start callback error: {cb_err}")
                
                # Play the audio
                playback_start = time.time()
                if not self.play_audio_ephemeral(audio_path):
                    log.warning("🔊 TTS FAILED: play_audio_ephemeral returned False")
                    return False
                
                # Wait for playback if requested
                if wait:
                    completed = await self.wait_for_playback()
                    playback_time = time.time() - playback_start
                    total_time = time.time() - total_start
                    log.info(f"🔊 TTS COMPLETE: synthesis={synthesis_time:.2f}s, playback={playback_time:.2f}s, total={total_time:.2f}s")
                    # Cleanup audio file after playback
                    self._cleanup_audio_file(audio_path)
                    return completed
                
                total_time = time.time() - total_start
                log.info(f"🔊 TTS STARTED PLAYBACK: synthesis={synthesis_time:.2f}s, total_so_far={total_time:.2f}s (not waiting)")
                return True
                
            except Exception as e:
                total_time = time.time() - total_start
                log.error(f"🔊 TTS ERROR after {total_time:.2f}s: {e}")
                return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "available": self.is_available,
            "queue_size": len(self._queue),
            "processing": self._processing,
            "base_url": self.base_url
        }


# Convenience function
def create_tts_service(
    base_url: str = None,
    workflow_path: str = None,
    output_dir: str = None,
    on_playback_start: callable = None
) -> ComfyUITTSService:
    """
    Factory function to create a ComfyUITTSService instance.
    
    Uses environment variables if parameters not provided.
    
    Args:
        on_playback_start: Async callback(text, duration_ms) called when audio starts
    """
    return ComfyUITTSService(
        base_url=base_url,
        workflow_path=workflow_path,
        output_dir=output_dir,
        on_playback_start=on_playback_start
    )
