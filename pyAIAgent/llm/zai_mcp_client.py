"""
MCP (Model Context Protocol) Client for Z.AI Vision Server
Provides vision capabilities through Z.AI's MCP server for image understanding
"""

import os
import json
import logging
import subprocess
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

log = logging.getLogger('zai_mcp_client')

class ZAIMCPClient:
    """Client for interacting with Z.AI's MCP Vision Server"""

    def __init__(self, api_key: str, mode: str = "ZAI"):
        """
        Initialize the Z.AI MCP Client

        Args:
            api_key: Z.AI API key
            mode: MCP mode (should be "ZAI")
        """
        self.api_key = api_key
        self.mode = mode
        self.mcp_process = None
        self.is_connected = False

        log.info("Z.AI MCP Client initialized")

        # Start the MCP server synchronously
        self._start_mcp_server_sync()

    async def start_mcp_server(self) -> bool:
        """
        Start the Z.AI MCP vision server

        Returns:
            True if server started successfully, False otherwise
        """
        try:
            # Set up environment variables for MCP server
            env = os.environ.copy()
            env['Z_AI_API_KEY'] = self.api_key
            env['Z_AI_MODE'] = self.mode

            # Start MCP server using npx
            cmd = [
                'npx', '-y', '@z_ai/mcp-server'
            ]

            log.info("Starting Z.AI MCP vision server...")

            # Start the subprocess
            self.mcp_process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Give it a moment to start
            await asyncio.sleep(2)

            # Check if process is still running
            if self.mcp_process.returncode is None:
                self.is_connected = True
                log.info("Z.AI MCP vision server started successfully")
                return True
            else:
                log.error(f"MCP server exited with code: {self.mcp_process.returncode}")
                return False

        except Exception as e:
            log.error(f"Failed to start Z.AI MCP server: {e}", exc_info=True)
            return False

    def _start_mcp_server_sync(self):
        """Start the MCP server synchronously"""
        try:
            import subprocess
            import time

            # Set up environment variables for MCP server
            env = os.environ.copy()
            env['Z_AI_API_KEY'] = self.api_key
            env['Z_AI_MODE'] = self.mode

            # Start MCP server using npx
            cmd = [
                'npx', '-y', '@z_ai/mcp-server'
            ]

            log.info("Starting Z.AI MCP vision server...")

            # Start the subprocess
            self.mcp_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=False  # Use bytes mode for proper MCP communication
            )

            # Give it a moment to start
            time.sleep(2)

            # Check if process is still running
            if self.mcp_process.returncode is None:
                self.is_connected = True
                log.info("Z.AI MCP vision server started successfully")
            else:
                log.error(f"MCP server exited with code: {self.mcp_process.returncode}")

        except Exception as e:
            log.error(f"Failed to start Z.AI MCP server synchronously: {e}", exc_info=True)

    async def stop_mcp_server(self):
        """Stop the MCP server"""
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                await self.mcp_process.wait()
                log.info("Z.AI MCP vision server stopped")
            except Exception as e:
                log.warning(f"Error stopping MCP server: {e}")
            finally:
                self.mcp_process = None
                self.is_connected = False

    async def analyze_image(self, image_path: str, prompt: str = "What does this image show?") -> Optional[str]:
        """
        Analyze an image using the Z.AI MCP vision server

        Args:
            image_path: Path to the image file
            prompt: Text prompt to accompany the image

        Returns:
            Analysis result as string, or None if failed
        """
        if not self.is_connected:
            log.error("MCP server not connected")
            return None

        if not os.path.exists(image_path):
            log.error(f"Image file not found: {image_path}")
            return None

        try:
            # Create MCP request for image analysis
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "analyze_image",
                    "arguments": {
                        "image": os.path.basename(image_path),
                        "prompt": prompt
                    }
                }
            }

            # Send request to MCP server
            request_json = json.dumps(mcp_request) + '\n'
            self.mcp_process.stdin.write(request_json.encode())

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    self.mcp_process.stdout.readline(),
                    timeout=10.0
                )
                if not response_line:
                    log.error("No response from MCP server")
                    return None

                response_data = json.loads(response_line.decode())
            except asyncio.TimeoutError:
                log.error("MCP server response timeout")
                return None

            if 'result' in response_data:
                return response_data['result'].get('description', 'No description available')
            elif 'error' in response_data:
                log.error(f"MCP server error: {response_data['error']}")
                return None
            else:
                log.error(f"Unexpected MCP response: {response_data}")
                return None

        except Exception as e:
            log.error(f"Failed to analyze image: {e}", exc_info=True)
            return None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_mcp_server()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop_mcp_server()

class ZAIVisionFallback:
    """
    Fallback vision handler that uses Z.AI's direct API when MCP is not available
    """

    def __init__(self, client, model: str):
        """
        Initialize fallback vision handler

        Args:
            client: OpenAI-compatible client instance
            model: Model name to use
        """
        # Use the same coding plan endpoint for vision to avoid rate limits
        from openai import OpenAI
        api_key = os.getenv("ZAI_API_KEY")
        if api_key:
            self.client = OpenAI(
                base_url="https://api.z.ai/api/coding/paas/v4",  # Coding plan endpoint for vision
                api_key=api_key,
                timeout=30
            )
            log.info("Z.AI Vision fallback handler initialized with coding plan endpoint")
        else:
            # Fallback to provided client if no API key
            self.client = client
            log.warning("No ZAI_API_KEY found, using provided client for vision fallback")
        self.model = model

    def analyze_image(self, image_path: str, prompt: str = "What does this image show?") -> Optional[str]:
        """
        Analyze image using direct API calls

        Args:
            image_path: Path to image file
            prompt: Text prompt

        Returns:
            Analysis result or None if failed
        """
        try:
            # Read and encode image
            import base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Create message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ]

            # Use raw HTTP request for coding plan API compatibility
            import httpx

            api_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }

            headers = {
                "Authorization": f"Bearer {os.getenv('ZAI_API_KEY')}",
                "Content-Type": "application/json"
            }

            with httpx.Client(timeout=30.0) as http_client:
                response = http_client.post(
                    "https://api.z.ai/api/coding/paas/v4/chat/completions",
                    json=api_data,
                    headers=headers
                )

                if response.status_code == 200:
                    response_data = response.json()
                    if 'choices' in response_data and response_data['choices']:
                        return response_data['choices'][0]['message']['content']
                    else:
                        log.error(f"Vision API response missing choices: {response_data}")
                        return None
                else:
                    log.error(f"Vision API HTTP request failed: {response.status_code}")
                    log.error(f"Vision API response: {response.text}")
                    return None

        except Exception as e:
            log.error(f"Fallback image analysis failed: {e}", exc_info=True)
            return None

def create_zai_vision_client(client, model: str, use_mcp: bool = True) -> Any:
    """
    Create appropriate Z.AI vision client

    Args:
        client: OpenAI-compatible client
        model: Model name
        use_mcp: Whether to try MCP first

    Returns:
        Vision client instance
    """
    if use_mcp:
        api_key = os.getenv("ZAI_API_KEY")
        if api_key:
            log.info("Creating Z.AI MCP vision client")
            return ZAIMCPClient(api_key=api_key)
        else:
            log.warning("ZAI_API_KEY not found, falling back to direct API")

    log.info("Creating Z.AI direct API vision client")
    return ZAIVisionFallback(client, model)