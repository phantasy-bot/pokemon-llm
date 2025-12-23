# --- services/comfyui_vision_service.py ---
"""
ComfyUI Vision Service for Pokemon LLM Agent.
Triggers Vision workflows on a ComfyUI server to analyze images using models like Moondream.
"""

import asyncio
import os
import json
import time
import uuid
import logging
import httpx
from typing import Optional, Dict, Any, Tuple

log = logging.getLogger("comfyui_vision")


class ComfyUIVisionService:
    """
    Vision service using ComfyUI as the backend.
    """

    def __init__(
        self,
        base_url: str = None,
        workflow_path: str = None,
        timeout: float = 30.0,
        node_id: str = "7",
    ):
        """
        Initialize the ComfyUI Vision service.

        Args:
            base_url: ComfyUI server URL (e.g., "http://localhost:8188")
            workflow_path: Path to the Vision workflow JSON file
            timeout: Request timeout in seconds
            node_id: ID of the node producing the text output
        """
        self.base_url = (
            base_url or os.getenv("COMFYUI_URL", "http://localhost:8188")
        ).rstrip("/")
        self.workflow_path = workflow_path or os.getenv(
            "COMFYUI_VISION_WORKFLOW", "workflows/lass-vision.json"
        )
        self.output_node_id = node_id or os.getenv("COMFYUI_VISION_NODE_ID", "7")
        self.timeout = timeout

        # Basic auth credentials
        self._auth_username = os.getenv("COMFYUI_USERNAME", "")
        self._auth_password = os.getenv("COMFYUI_PASSWORD", "")
        self._auth: Optional[httpx.BasicAuth] = None
        if self._auth_username and self._auth_password:
            self._auth = httpx.BasicAuth(self._auth_username, self._auth_password)
            log.info(
                f"🔐 ComfyUI vision auth configured for user: {self._auth_username}"
            )

        self._workflow_template: Optional[dict] = None

        # Check configuration
        self.enabled = os.getenv("VISION_PROVIDER", "ZAI") == "COMFYUI"
        if self.enabled:
            log.info(f"👁️ ComfyUI Vision Service ENABLED (Node {self.output_node_id})")
        else:
            log.info("👁️ ComfyUI Vision Service available but not active provider")

    def _create_client(self) -> httpx.AsyncClient:
        """Create a new client instance (caller must close or use context manager)."""
        return httpx.AsyncClient(timeout=self.timeout, auth=self._auth)

    async def check_connection(self) -> bool:
        try:
            async with self._create_client() as client:
                response = await client.get(f"{self.base_url}/system_stats")
                return response.status_code == 200
        except Exception as e:
            log.warning(f"ComfyUI vision connection check failed: {e}")
            return False

    def load_workflow(self) -> Optional[dict]:
        if self._workflow_template:
            return self._workflow_template

        if not self.workflow_path or not os.path.exists(self.workflow_path):
            log.warning(f"Vision workflow not found: {self.workflow_path}")
            return None

        try:
            with open(self.workflow_path, "r") as f:
                raw = json.load(f)

            # Simple API format check (if keys are node IDs)
            # The lass-vision.json is in API format (nodes list)?
            # Wait, the file I read started with {"id":..., "nodes": [...]}
            # That is the EXPORT format (Graph). API needs PROMPT format.
            # I need to convert it.

            if "nodes" in raw:
                # Need conversion
                self._workflow_template = self._convert_export_to_api_format(raw)
            else:
                # Assume already API format
                self._workflow_template = raw

            return self._workflow_template
        except Exception as e:
            log.error(f"Failed to load Vision workflow: {e}")
            return None

    def _convert_export_to_api_format(self, export_workflow: dict) -> dict:
        # Simplified conversion similar to TTS service
        nodes = export_workflow.get("nodes", [])
        links = export_workflow.get("links", [])

        link_map = {}
        for link in links:
            if len(link) >= 5:
                link_id, from_node, from_slot, to_node, to_slot, *_ = link
                link_map[link_id] = (from_node, from_slot)

        api_prompt = {}
        for node in nodes:
            node_id = str(node.get("id"))
            node_type = node.get("type")
            inputs = {}

            # Inputs from links
            for input_def in node.get("inputs", []):
                input_name = input_def.get("name")
                link_id = input_def.get("link")
                if link_id and link_id in link_map:
                    from_node, from_slot = link_map[link_id]
                    inputs[input_name] = [str(from_node), from_slot]

            # Widget values
            widgets_values = node.get("widgets_values", [])

            # Map known nodes
            if node_type == "LoadImage":
                if widgets_values:
                    inputs["image"] = widgets_values[0]
                    inputs["upload"] = "image"  # typical default
            elif node_type == "UnifiedVisionPromptGenerator":
                # widgets: [question, max_tokens, temp, seed, model, keep_loaded]
                # Map based on index if input names match?
                # Actually API format usually expects inputs dict with keys matching widget names if they are converted to inputs?
                # Or just pass them if they are simple values.
                # But UnifiedVisionPromptGenerator might expect inputs dict to contain values for widgets.
                # Let's verify mapping based on widget names in input definition if possible?
                # In export format, 'widgets_values' is a list. In API format, 'inputs' dict has keys.
                # I need to know the mapping.
                # Based on file read:
                # inputs: image, question, max_new_tokens...
                # question, max_new_tokens etc have "widget": {"name": ...}
                # So they correspond to widgets_values in order?
                pass

            # For simplicity, if we don't know the mapping, we might struggle.
            # But wait, TTS service mapping was manual.
            # Let's inspect the JSON again to see order.
            # UnifiedVisionPromptGenerator: ["Describe...", 1024, 0.7, 9014..., "randomize", "vikhyatk/moondream2", false]
            # Inputs: image (link), question (widget), max_new_tokens (widget), temperature (widget), seed (widget), model (widget), keep_model_loaded (widget)
            # So order matches.

            if node_type == "UnifiedVisionPromptGenerator":
                # Map widgets_values list to named inputs
                # Order from JSON: question, max_new_tokens, temperature, seed, model, keep_model_loaded
                # (Note: 'randomize' is usually control_after_generate, ignored in API execution usually?)
                # Wait, 'seed' widget value is int. 'control_after_generate' is string "randomize".
                # The JSON has `widgets_values`: ["Describe...", 1024, 0.7, 901..., "randomize", "vikhyatk/...", false]
                # indices: 0=question, 1=max_tokens, 2=temp, 3=seed, 4=control?, 5=model, 6=keep_loaded?
                # Actually ComfyUI API expects specific keys.

                inputs["question"] = widgets_values[0]
                inputs["max_new_tokens"] = widgets_values[1]
                inputs["temperature"] = widgets_values[2]
                inputs["seed"] = widgets_values[3]
                # skip 4 "randomize"
                inputs["model"] = widgets_values[5]
                inputs["keep_model_loaded"] = widgets_values[6]

            api_prompt[node_id] = {"class_type": node_type, "inputs": inputs}

        return {"prompt": api_prompt}

    async def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image to ComfyUI and return filename."""
        if not os.path.exists(image_path):
            return None

        try:
            async with self._create_client() as client:
                with open(image_path, "rb") as f:
                    files = {"image": f}
                    response = await client.post(
                        f"{self.base_url}/upload/image", files=files
                    )

            if response.status_code == 200:
                data = response.json()
                # Returns: {"name": "filename.png", "subfolder": "", "type": "input"}
                return data.get("name")
            return None
        except Exception as e:
            log.error(f"Image upload failed: {e}")
            return None

    async def analyze_image(
        self, image_path: str, prompt_text: str = "Describe this image in detail."
    ) -> Optional[str]:
        """
        Analyze image using ComfyUI workflow.
        Returns description string.
        """
        if not self.enabled:
            return None

        # 1. Upload Image
        filename = await self.upload_image(image_path)
        if not filename:
            log.error("Failed to upload image to ComfyUI")
            return None

        # 2. Prepare Workflow
        workflow = self.load_workflow()
        if not workflow:
            return None

        import copy

        prompt = copy.deepcopy(workflow["prompt"])

        # Update inputs
        # Node 2: LoadImage
        # Node 1: UnifiedVisionPromptGenerator

        # Find LoadImage node (usually '2' based on our file)
        # But we should find by type to be safe? Or stick to ID since we converted it?
        # The IDs are preserved in conversion.

        if "2" in prompt:
            prompt["2"]["inputs"]["image"] = filename
        else:
            # Fallback search
            for nid, data in prompt.items():
                if data["class_type"] == "LoadImage":
                    data["inputs"]["image"] = filename
                    break

        # Update Prompt
        if self.output_node_id in prompt:
            prompt[self.output_node_id]["inputs"]["question"] = prompt_text

        # 3. Queue Prompt
        try:
            async with self._create_client() as client:
                response = await client.post(
                    f"{self.base_url}/prompt", json={"prompt": prompt}
                )

            if response.status_code != 200:
                log.error(f"Failed to queue vision workflow: {response.text}")
                return None

            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                return None

            log.info(f"Queued vision workflow: {prompt_id}")

            # 4. Wait for completion
            return await self._wait_for_result(prompt_id)

        except Exception as e:
            log.error(f"Vision analysis error: {e}")
            return None

    async def _wait_for_result(self, prompt_id: str) -> Optional[str]:
        async with self._create_client() as client:
            start = time.time()

            while time.time() - start < self.timeout:
                try:
                    # Check history
                    res = await client.get(f"{self.base_url}/history/{prompt_id}")
                    if res.status_code == 200:
                        history = res.json()
                        if prompt_id in history:
                            outputs = history[prompt_id].get("outputs", {})

                            # Look for our target node output
                            if self.output_node_id in outputs:
                                node_output = outputs[self.output_node_id]
                                # UnifiedVisionPromptGenerator outputs 'prompt' (STRING)
                                # API output structure: {"prompt": ["The description text"]}
                                # Usually values are lists
                                if "prompt" in node_output:
                                    val = node_output["prompt"]
                                    if isinstance(val, list) and len(val) > 0:
                                        return val[0]
                                    return str(val)

                                # If key isn't 'prompt', return first value
                                for k, v in node_output.items():
                                    if isinstance(v, list) and len(v) > 0:
                                        return v[0]
                                    return str(v)
                            else:
                                log.debug(
                                    f"Target node {self.output_node_id} not in outputs. Available nodes: {list(outputs.keys())}"
                                )

                                # Fallback: Check if ANY node has text output?
                                # Or check for 'text' or 'prompt' keys in any node
                                for nid, nout in outputs.items():
                                    for k, v in nout.items():
                                        if k in ["prompt", "text", "string", "output"]:
                                            val = (
                                                v[0]
                                                if isinstance(v, list) and v
                                                else str(v)
                                            )
                                            log.info(
                                                f"Found fallback output in node {nid} key {k}"
                                            )
                                            return val

                    await asyncio.sleep(0.5)
                except Exception as e:
                    log.warning(f"Error checking vision status: {e}")
                    await asyncio.sleep(1)

            log.error("Vision workflow timed out")
            return None


# Factory
def create_vision_service() -> ComfyUIVisionService:
    return ComfyUIVisionService()
