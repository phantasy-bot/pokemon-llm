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
from typing import Optional, Dict, Any
from dataclasses import dataclass

import httpx

log = logging.getLogger("comfyui_tts")


@dataclass
class TTSRequest:
    """Represents a pending TTS request."""
    text: str
    request_id: str
    priority: int  # Higher = more important (game commentary > chat response)
    created_at: float
    audio_path: Optional[str] = None
    completed: bool = False
    error: Optional[str] = None


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
        timeout: float = 60.0
    ):
        """
        Initialize the ComfyUI TTS service.
        
        Args:
            base_url: ComfyUI server URL (e.g., "http://localhost:8188")
            workflow_path: Path to the TTS workflow JSON file
            output_dir: Directory to save generated audio files
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("COMFYUI_URL", "http://localhost:8188")).rstrip("/")
        self.workflow_path = workflow_path or os.getenv("COMFYUI_TTS_WORKFLOW", "")
        self.output_dir = output_dir or os.getenv("COMFYUI_OUTPUT_DIR", "tts_output")
        self.timeout = timeout
        
        # Request queue (priority queue simulation with sorting)
        self._queue: list[TTSRequest] = []
        self._processing = False
        self._client: Optional[httpx.AsyncClient] = None
        
        # Cached workflow template
        self._workflow_template: Optional[dict] = None
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if configured
        self._is_configured = bool(self.base_url)
        
        if not self._is_configured:
            log.warning("ComfyUI TTS not configured. Set COMFYUI_URL in .env")
    
    @property
    def is_available(self) -> bool:
        """Check if TTS service is configured."""
        return self._is_configured
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
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
        """Load the TTS workflow template from file."""
        if self._workflow_template:
            return self._workflow_template
        
        if not self.workflow_path or not os.path.exists(self.workflow_path):
            log.warning(f"TTS workflow not found: {self.workflow_path}")
            return None
        
        try:
            with open(self.workflow_path, 'r') as f:
                self._workflow_template = json.load(f)
            log.info(f"Loaded TTS workflow from: {self.workflow_path}")
            return self._workflow_template
        except Exception as e:
            log.error(f"Failed to load TTS workflow: {e}")
            return None
    
    def _prepare_workflow(self, text: str, workflow: dict = None) -> dict:
        """
        Prepare the workflow with the given text input.
        
        This method should be customized based on your specific TTS workflow.
        It looks for common TTS node patterns and injects the text.
        
        Args:
            text: Text to synthesize
            workflow: Workflow template (uses cached if not provided)
        
        Returns:
            Modified workflow dict ready for execution
        """
        if workflow is None:
            workflow = self.load_workflow()
        
        if workflow is None:
            # Create a minimal default workflow structure
            # This should be customized for your specific ComfyUI TTS setup
            log.warning("No workflow template - using placeholder. Configure COMFYUI_TTS_WORKFLOW.")
            return {
                "prompt": {
                    "1": {
                        "class_type": "CLIPTextEncode",
                        "inputs": {
                            "text": text
                        }
                    }
                }
            }
        
        # Deep copy to avoid modifying the template
        import copy
        prepared = copy.deepcopy(workflow)
        
        # Common patterns for TTS nodes - try to find and update text input
        # This handles various TTS node naming conventions
        text_input_keys = [
            "text", "input_text", "prompt", "tts_text", 
            "speech_text", "content", "message"
        ]
        
        # Search through nodes for text input fields
        if "prompt" in prepared:
            nodes = prepared["prompt"]
        else:
            nodes = prepared
        
        text_injected = False
        for node_id, node_data in nodes.items():
            if isinstance(node_data, dict):
                inputs = node_data.get("inputs", {})
                for key in text_input_keys:
                    if key in inputs:
                        inputs[key] = text
                        text_injected = True
                        log.debug(f"Injected text into node {node_id}, field {key}")
                        break
        
        if not text_injected:
            log.warning("Could not find text input field in workflow. TTS may not work correctly.")
        
        return prepared
    
    async def queue_tts(
        self,
        text: str,
        priority: int = None
    ) -> TTSRequest:
        """
        Queue a TTS request.
        
        Args:
            text: Text to synthesize
            priority: Request priority (higher = more important)
        
        Returns:
            TTSRequest object for tracking
        """
        if priority is None:
            priority = self.PRIORITY_CHAT_RESPONSE
        
        request = TTSRequest(
            text=text,
            request_id=str(uuid.uuid4())[:8],
            priority=priority,
            created_at=time.time()
        )
        
        self._queue.append(request)
        # Sort by priority (highest first)
        self._queue.sort(key=lambda r: -r.priority)
        
        log.info(f"🔊 Queued TTS (priority={priority}): {text[:50]}...")
        
        return request
    
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
        
        try:
            client = await self._get_client()
            
            # Queue the workflow
            prompt_response = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow.get("prompt", workflow)}
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
        Wait for a ComfyUI workflow to complete and get output.
        
        Args:
            prompt_id: The prompt ID to monitor
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
        
        Returns:
            Path to output audio file, or None if failed/timeout.
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
                        
                        # Check if completed
                        if prompt_history.get("status", {}).get("completed", False):
                            # Get outputs
                            outputs = prompt_history.get("outputs", {})
                            
                            # Look for audio output
                            for node_id, node_output in outputs.items():
                                if "audio" in node_output or "audios" in node_output:
                                    audio_data = node_output.get("audio") or node_output.get("audios", [{}])[0]
                                    if isinstance(audio_data, dict):
                                        filename = audio_data.get("filename")
                                        subfolder = audio_data.get("subfolder", "")
                                        if filename:
                                            return os.path.join(self.output_dir, subfolder, filename)
                            
                            # No audio found in outputs, check for completion anyway
                            log.warning("Workflow completed but no audio output found")
                            return None
                        
                        # Check for error
                        status_messages = prompt_history.get("status", {}).get("status_str", "")
                        if "error" in status_messages.lower():
                            log.error(f"Workflow error: {status_messages}")
                            return None
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                log.warning(f"Error checking workflow status: {e}")
                await asyncio.sleep(poll_interval)
        
        log.warning(f"Timeout waiting for workflow {prompt_id}")
        return None
    
    async def clear_queue(self):
        """Clear all pending TTS requests."""
        cleared = len(self._queue)
        self._queue.clear()
        log.info(f"Cleared {cleared} pending TTS requests")
    
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
    output_dir: str = None
) -> ComfyUITTSService:
    """
    Factory function to create a ComfyUITTSService instance.
    
    Uses environment variables if parameters not provided.
    """
    return ComfyUITTSService(
        base_url=base_url,
        workflow_path=workflow_path,
        output_dir=output_dir
    )
