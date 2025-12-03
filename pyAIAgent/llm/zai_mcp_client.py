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
            log.info(f"Command: {' '.join(cmd)}")
            log.info(f"Environment variables: Z_AI_API_KEY={'*' * len(self.api_key)}, Z_AI_MODE={self.mode}")

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
            time.sleep(3)  # Increased startup time

            # Check if process is still running
            if self.mcp_process.returncode is None:
                self.is_connected = True
                log.info("Z.AI MCP vision server started successfully")
                log.info(f"MCP server PID: {self.mcp_process.pid}")
            else:
                log.error(f"MCP server exited with code: {self.mcp_process.returncode}")
                # Read stderr to see what went wrong
                if self.mcp_process.stderr:
                    stderr_output = self.mcp_process.stderr.read().decode()
                    log.error(f"MCP server stderr during startup: {stderr_output}")

        except Exception as e:
            log.error(f"Failed to start Z.AI MCP server synchronously: {e}", exc_info=True)

    def analyze_image_sync(self, image_path: str, prompt: str = "What does this image show?") -> Optional[str]:
        """
        Synchronous version of analyze_image for use in sync contexts

        Args:
            image_path: Path to the image file
            prompt: Text prompt to accompany the image

        Returns:
            Analysis result as string, or None if failed
        """
        # Use asyncio.run to call the async method
        try:
            return asyncio.run(self.analyze_image(image_path, prompt))
        except Exception as e:
            log.error(f"Sync image analysis failed: {e}", exc_info=True)
            return None

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
            # First, try to list available tools
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            log.info(f"Requesting available tools: {json.dumps(list_tools_request, indent=2)}")

            # Send list tools request
            list_tools_json = json.dumps(list_tools_request) + '\n'
            self.mcp_process.stdin.write(list_tools_json.encode())
            self.mcp_process.stdin.flush()

            # Read tools list response
            import time
            import select

            if hasattr(select, 'select'):
                ready, _, _ = select.select([self.mcp_process.stdout], [], [], 10.0)
                if not ready:
                    log.error("Timeout waiting for tools list")
                    return None

            tools_response = self.mcp_process.stdout.readline()
            if tools_response:
                tools_data = json.loads(tools_response.decode())
                log.info(f"Available tools: {json.dumps(tools_data, indent=2)}")

                if 'result' in tools_data and 'tools' in tools_data['result']:
                    available_tools = tools_data['result']['tools']
                    log.info(f"Found {len(available_tools)} available tools")
                    for tool in available_tools:
                        log.info(f"Tool: {tool.get('name', 'unknown')} - {tool.get('description', 'no description')}")
            else:
                log.error("No response for tools list")

            # Use the correct tool name and parameters from the schema
            tool_name = "analyze_image"
            log.info(f"Using tool: {tool_name}")

            # Create MCP request for image analysis with correct schema
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {
                        "image_source": image_path,  # Use correct parameter name from schema
                        "prompt": prompt
                    }
                }
            }

            log.info(f"Sending MCP request: {json.dumps(mcp_request, indent=2)}")

            # Send request to MCP server
            request_json = json.dumps(mcp_request) + '\n'
            self.mcp_process.stdin.write(request_json.encode())
            self.mcp_process.stdin.flush()

                # Read response with timeout using sync approach since process was started with Popen
            try:
                log.info(f"Waiting for MCP server response for {tool_name}...")

                # Use select for timeout on subprocess stdout
                if hasattr(select, 'select'):
                    ready, _, _ = select.select([self.mcp_process.stdout], [], [], 30.0)
                    if not ready:
                        log.error(f"MCP server response timeout for {tool_name}")
                        return None

                response_line = self.mcp_process.stdout.readline()
                if not response_line:
                    log.error(f"No response from MCP server for {tool_name}")
                    # Check if server is still running
                    if self.mcp_process.poll() is not None:
                        log.error(f"MCP server process has terminated with code: {self.mcp_process.returncode}")
                        # Read stderr to see what went wrong
                        if self.mcp_process.stderr:
                            stderr_output = self.mcp_process.stderr.read().decode()
                            log.error(f"MCP server stderr: {stderr_output}")
                    return None

                log.info(f"Raw MCP response for {tool_name}: {response_line.decode().strip()}")
                response_data = json.loads(response_line.decode())
            except Exception as read_error:
                log.error(f"MCP server communication error for {tool_name}: {read_error}")
                return None

            if 'result' in response_data:
                result = response_data['result']
                # Handle different response formats
                if isinstance(result, dict):
                    # Check for MCP content format first
                    if 'content' in result and isinstance(result['content'], list) and len(result['content']) > 0:
                        content = result['content'][0]
                        if isinstance(content, dict) and 'text' in content:
                            analysis = content['text']
                            log.info(f"Successfully parsed MCP content format: {len(analysis)} chars")
                        else:
                            analysis = str(content)
                            log.warning(f"MCP content format unexpected, got: {type(content)}")
                    elif 'tools' in result:
                        # This is an INVALID response - MCP server returned tools list instead of analysis
                        log.error(f"MCP server returned tools list instead of analysis. This indicates a server error. Response: {result}")
                        return None
                    else:
                        # Fallback to other possible formats
                        analysis = result.get('description', result.get('analysis', str(result)))
                        log.info(f"Using fallback format for MCP response: {len(str(analysis))} chars")
                elif isinstance(result, str):
                    analysis = result
                else:
                    analysis = str(result)

                # Additional validation: ensure analysis is not just tool descriptions
                if analysis and isinstance(analysis, str):
                    # Check if the analysis contains tool-like content instead of actual image analysis
                    tool_keywords = ['analyze_image', 'analyze_video', 'inputSchema', 'maximum file size', 'supports both local files and remote URL']
                    if any(keyword.lower() in analysis.lower() for keyword in tool_keywords):
                        log.error(f"Analysis appears to contain tool descriptions instead of actual image analysis. Treating as invalid. Analysis preview: {analysis[:200]}...")
                        return None

                log.info(f"Successfully got analysis from {tool_name}")
                return analysis
            elif 'error' in response_data:
                log.error(f"MCP server error for {tool_name}: {response_data['error']}")
                return None
            else:
                log.error(f"Unexpected MCP response for {tool_name}: {response_data}")
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