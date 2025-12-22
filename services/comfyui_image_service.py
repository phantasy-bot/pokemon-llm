"""
ComfyUI Image Generation Service for Pokemon LLM Agent.

Triggers image generation workflows on a ComfyUI server to create
images for tweet attachments.
"""

import asyncio
import os
import json
import time
import logging
import httpx
from typing import Optional
from pathlib import Path

log = logging.getLogger("comfyui_image")


class ComfyUIImageService:
    """
    Image generation service using ComfyUI as the backend.
    Generates 1024x1024 images for tweet attachments.
    """

    def __init__(
        self,
        base_url: str = None,
        workflow_path: str = None,
        output_dir: str = None,
        timeout: float = 120.0,
    ):
        """
        Initialize the ComfyUI Image Generation service.

        Args:
            base_url: ComfyUI server URL (e.g., "http://localhost:8188")
            workflow_path: Path to the image generation workflow JSON file
            output_dir: Local directory to save generated images
            timeout: Request timeout in seconds (image gen can be slow)
        """
        self.base_url = (
            base_url or os.getenv("COMFYUI_URL", "http://localhost:8188")
        ).rstrip("/")
        self.workflow_path = workflow_path or os.getenv(
            "COMFYUI_IMAGE_WORKFLOW", "workflows/lass-image-gen.json"
        )
        self.output_dir = output_dir or os.path.join(os.getcwd(), "outputs", "images")
        self.timeout = timeout

        # Basic auth credentials (shared with TTS/Vision)
        self._auth_username = os.getenv("COMFYUI_USERNAME", "")
        self._auth_password = os.getenv("COMFYUI_PASSWORD", "")
        self._auth: Optional[httpx.BasicAuth] = None
        if self._auth_username and self._auth_password:
            self._auth = httpx.BasicAuth(self._auth_username, self._auth_password)
            log.info(f"ComfyUI image auth configured for user: {self._auth_username}")

        self._workflow_template: Optional[dict] = None

        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Check if workflow exists
        if os.path.exists(self.workflow_path):
            log.info(
                f"ComfyUI Image Service initialized with workflow: {self.workflow_path}"
            )
        else:
            log.warning(f"Image workflow not found: {self.workflow_path}")

        # Cleanup stale images from previous runs
        self._cleanup_stale_images()

    def _cleanup_stale_images(self) -> None:
        """
        Remove any leftover image files from previous sessions.
        Called on startup to ensure clean state.
        """
        if not os.path.exists(self.output_dir):
            return

        cleaned = 0
        for f in os.listdir(self.output_dir):
            if f.endswith((".png", ".jpg", ".jpeg", ".webp")):
                try:
                    os.remove(os.path.join(self.output_dir, f))
                    cleaned += 1
                except Exception as e:
                    log.warning(f"Failed to cleanup image {f}: {e}")

        if cleaned > 0:
            log.info(f"Cleaned up {cleaned} stale image files from {self.output_dir}")

    def cleanup_image(self, image_path: str) -> None:
        """
        Remove an image file after it has been used (posted/denied).
        Called after tweet flow completes.
        """
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                log.debug(f"Cleaned up image: {os.path.basename(image_path)}")
            except Exception as e:
                log.warning(f"Failed to cleanup image: {e}")

    def _create_client(self) -> httpx.AsyncClient:
        """Create a new client instance."""
        return httpx.AsyncClient(timeout=self.timeout, auth=self._auth)

    async def check_connection(self) -> bool:
        """Check if ComfyUI server is reachable."""
        try:
            async with self._create_client() as client:
                response = await client.get(f"{self.base_url}/system_stats")
                return response.status_code == 200
        except Exception as e:
            log.warning(f"ComfyUI image connection check failed: {e}")
            return False

    def load_workflow(self) -> Optional[dict]:
        """Load and convert the workflow template."""
        if self._workflow_template:
            return self._workflow_template

        if not self.workflow_path or not os.path.exists(self.workflow_path):
            log.warning(f"Image workflow not found: {self.workflow_path}")
            return None

        try:
            with open(self.workflow_path, "r") as f:
                raw = json.load(f)

            # Check if export format (has "nodes" list) or API format
            if "nodes" in raw:
                self._workflow_template = self._convert_export_to_api_format(raw)
            else:
                self._workflow_template = raw

            return self._workflow_template
        except Exception as e:
            log.error(f"Failed to load image workflow: {e}")
            return None

    def _convert_export_to_api_format(self, export_workflow: dict) -> dict:
        """
        Convert ComfyUI export format (graph with nodes list) to API format (prompt dict).
        """
        nodes = export_workflow.get("nodes", [])
        links = export_workflow.get("links", [])

        # Build link map: link_id -> (from_node_id, from_slot_index)
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

            # Process linked inputs
            for input_def in node.get("inputs", []):
                input_name = input_def.get("name")
                link_id = input_def.get("link")
                if link_id and link_id in link_map:
                    from_node, from_slot = link_map[link_id]
                    inputs[input_name] = [str(from_node), from_slot]

            # Process widget values
            widgets_values = node.get("widgets_values", [])

            # Handle common node types
            if node_type == "SaveImage" and widgets_values:
                inputs["filename_prefix"] = (
                    widgets_values[0] if widgets_values else "lass_tweet"
                )

            # For other nodes, we preserve widget values as-is
            # The workflow should work with its defaults

            api_prompt[node_id] = {"class_type": node_type, "inputs": inputs}

        return {"prompt": api_prompt}

    async def generate_image(
        self,
        seed: int = None,
        positive_prompt_addition: str = None,
        negative_prompt_addition: str = None,
    ) -> Optional[str]:
        """
        Generate an image using the ComfyUI workflow.

        Args:
            seed: Optional seed for reproducibility. If None, uses random.
            positive_prompt_addition: Text to append to the positive prompt.
            negative_prompt_addition: Text to append to the negative prompt.

        Returns:
            Path to the downloaded image file, or None on failure.
        """
        # Load workflow
        workflow = self.load_workflow()
        if not workflow:
            log.error("Failed to load image generation workflow")
            return None

        import copy
        import random

        prompt = copy.deepcopy(workflow.get("prompt", workflow))

        # Update seed if provided (find KSampler or similar nodes)
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        for node_id, node_data in prompt.items():
            class_type = node_data.get("class_type", "")

            # Update seed on sampler nodes
            if "Sampler" in class_type or "KSampler" in class_type:
                if "seed" in node_data.get("inputs", {}):
                    node_data["inputs"]["seed"] = seed
                    log.debug(f"Set seed={seed} on node {node_id}")

            # Update prompts on CLIPTextEncode nodes
            if class_type == "CLIPTextEncode" and (
                positive_prompt_addition or negative_prompt_addition
            ):
                inputs = node_data.get("inputs", {})
                # Check if this is a text widget (widgets_values style)
                # or direct input style
                if "text" in inputs and isinstance(inputs["text"], str):
                    current_text = inputs["text"]

                    # Determine if positive or negative based on content
                    is_negative = any(
                        neg in current_text.lower()
                        for neg in ["lowres", "worst quality", "bad anatomy", "ugly"]
                    )

                    if is_negative and negative_prompt_addition:
                        inputs["text"] = current_text + ", " + negative_prompt_addition
                        log.debug(f"Added to negative prompt on node {node_id}")
                    elif not is_negative and positive_prompt_addition:
                        inputs["text"] = current_text + ", " + positive_prompt_addition
                        log.debug(f"Added to positive prompt on node {node_id}")

        # Queue the workflow
        try:
            async with self._create_client() as client:
                response = await client.post(
                    f"{self.base_url}/prompt", json={"prompt": prompt}
                )

            if response.status_code != 200:
                log.error(f"Failed to queue image workflow: {response.text}")
                return None

            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                log.error("No prompt_id in response")
                return None

            log.info(f"Queued image generation workflow: {prompt_id}")

            # Wait for completion and get the image
            return await self._wait_for_completion(prompt_id)

        except Exception as e:
            log.error(f"Image generation error: {e}")
            return None

    async def _wait_for_completion(self, prompt_id: str) -> Optional[str]:
        """Wait for workflow completion and download the generated image."""
        async with self._create_client() as client:
            start = time.time()

            while time.time() - start < self.timeout:
                try:
                    # Check history for completion
                    res = await client.get(f"{self.base_url}/history/{prompt_id}")
                    if res.status_code == 200:
                        history = res.json()
                        if prompt_id in history:
                            outputs = history[prompt_id].get("outputs", {})

                            # Find SaveImage node output
                            for node_id, node_output in outputs.items():
                                if "images" in node_output:
                                    images = node_output["images"]
                                    if images:
                                        # Download the first image
                                        img_info = images[0]
                                        filename = img_info.get("filename")
                                        subfolder = img_info.get("subfolder", "")

                                        log.info(f"Image generated: {filename}")
                                        return await self._download_image(
                                            client, filename, subfolder
                                        )

                            # Check if workflow errored
                            status = history[prompt_id].get("status", {})
                            if status.get("status_str") == "error":
                                log.error(f"Workflow execution error: {status}")
                                return None

                    await asyncio.sleep(1.0)
                except Exception as e:
                    log.warning(f"Error checking image status: {e}")
                    await asyncio.sleep(2.0)

            log.error("Image generation timed out")
            return None

    async def _download_image(
        self, client: httpx.AsyncClient, filename: str, subfolder: str = ""
    ) -> Optional[str]:
        """Download generated image from ComfyUI server."""
        try:
            params = {"filename": filename, "type": "output"}
            if subfolder:
                params["subfolder"] = subfolder

            response = await client.get(f"{self.base_url}/view", params=params)

            if response.status_code == 200:
                # Save to local output directory
                local_filename = f"tweet_{int(time.time())}_{filename}"
                local_path = os.path.join(self.output_dir, local_filename)

                with open(local_path, "wb") as f:
                    f.write(response.content)

                log.info(f"Downloaded image to: {local_path}")
                return local_path
            else:
                log.error(f"Failed to download image: {response.status_code}")
                return None
        except Exception as e:
            log.error(f"Image download error: {e}")
            return None


def create_image_service(
    base_url: str = None,
    workflow_path: str = None,
    output_dir: str = None,
) -> ComfyUIImageService:
    """Factory function to create a ComfyUI Image Service instance."""
    return ComfyUIImageService(
        base_url=base_url,
        workflow_path=workflow_path,
        output_dir=output_dir,
    )
