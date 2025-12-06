"""
MCP (Model Context Protocol) Client for Z.AI Vision Server
Provides vision capabilities through Z.AI's MCP server for image understanding
"""

import os
import json
import logging
import subprocess
import asyncio
import time
import threading
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

        # CRITICAL: Thread lock to prevent concurrent MCP access
        self._mcp_lock = threading.Lock()
        self._request_cancelled = False  # Flag to cancel pending requests
        
        # SIMPLIFIED RETRY SYSTEM: 3 attempts → restart MCP → repeat forever (never give up)
        self.max_attempts_before_restart = 3
        self._attempt_count = 0
        self._restart_count = 0
        
        # Status tracking for UI updates
        self.current_status = "INITIALIZING"
        
        # Request ID counter - reset on each MCP restart
        self._request_id_counter = 0
        
        # Cache tools list - only fetch once per MCP session
        self._tools_cached = False
        self._available_tools = None

        log.info("Z.AI MCP Client initialized with SIMPLIFIED retry system + thread lock")
        log.info("Retry strategy: 3 attempts → restart MCP → repeat forever (never give up)")

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

    def restart_mcp_server(self):
        """Kill and restart MCP server to clear any hung state and reset ID counters"""
        self._restart_count += 1
        log.warning(f"🔄 Restarting MCP server (restart #{self._restart_count})...")
        
        # Kill existing process
        if self.mcp_process:
            try:
                # Drain any pending stdout to prevent buffer issues
                import select
                while True:
                    ready, _, _ = select.select([self.mcp_process.stdout], [], [], 0.1)
                    if not ready:
                        break
                    data = self.mcp_process.stdout.read(1024)
                    if not data:
                        break
                    log.debug(f"Drained {len(data)} bytes from stdout before restart")
                
                self.mcp_process.terminate()
                try:
                    self.mcp_process.wait(timeout=3)
                except:
                    log.warning("MCP process did not terminate, killing forcefully")
                    self.mcp_process.kill()
                    self.mcp_process.wait(timeout=2)
            except Exception as e:
                log.error(f"Error killing MCP process: {e}")
        
        # Reset state
        self._request_id_counter = 0
        self._tools_cached = False
        self._available_tools = None
        self._attempt_count = 0
        self.is_connected = False
        
        # Restart
        log.info("🔄 Starting fresh MCP server subprocess...")
        self._start_mcp_server_sync()
        log.info(f"🔄 MCP server restart #{self._restart_count} complete")

    def handle_vision_failure(self, error_message: str) -> bool:
        """
        Handle vision analysis failure.
        Returns True if we should restart MCP server.
        """
        self._attempt_count += 1
        log.error(f"VISION FAILURE (Attempt {self._attempt_count}/{self.max_attempts_before_restart}): {error_message}")
        
        if self._attempt_count >= self.max_attempts_before_restart:
            log.warning(f"🔄 {self._attempt_count} consecutive failures - will restart MCP server")
            return True  # Signal to restart
        return False

    def handle_vision_success(self) -> None:
        """Reset failure counters after successful vision analysis"""
        if self._attempt_count > 0:
            log.info(f"✅ VISION SUCCESS after {self._attempt_count} attempts (restart #{self._restart_count})")
        self._attempt_count = 0

    def _get_next_request_id(self) -> int:
        """Get the next unique request ID for MCP communication"""
        self._request_id_counter += 1
        return self._request_id_counter

    def _read_response_with_id_match(self, expected_id: int, timeout: float = 30.0) -> Optional[dict]:
        """
        Read responses from MCP server until we get one with the matching ID.
        This drains any stale responses that may be buffered from previous cycles.
        
        Args:
            expected_id: The request ID we're looking for
            timeout: Maximum time to wait for matching response
            
        Returns:
            The response dict if found, None if timeout or error
        """
        import select
        import time as time_module
        
        start_time = time_module.time()
        stale_count = 0
        
        while True:
            elapsed = time_module.time() - start_time
            remaining_timeout = timeout - elapsed
            
            if remaining_timeout <= 0:
                log.error(f"Timeout waiting for response with id={expected_id} after draining {stale_count} stale responses")
                return None
            
            # Wait for data with remaining timeout
            if hasattr(select, 'select'):
                ready, _, _ = select.select([self.mcp_process.stdout], [], [], min(remaining_timeout, 5.0))
                if not ready:
                    if remaining_timeout <= 5.0:
                        log.error(f"Timeout waiting for response id={expected_id}")
                        return None
                    continue  # Try again with remaining timeout
            
            response_line = self.mcp_process.stdout.readline()
            if not response_line:
                log.error("No response from MCP server (empty readline)")
                return None
            
            try:
                response_data = json.loads(response_line.decode())
                response_id = response_data.get('id')
                
                if response_id == expected_id:
                    if stale_count > 0:
                        log.info(f"✅ Found matching response id={expected_id} after draining {stale_count} stale responses")
                    return response_data
                else:
                    stale_count += 1
                    log.warning(f"⏭️ Draining stale response id={response_id} (looking for id={expected_id}, drained {stale_count} so far)")
                    # Continue loop to read next response
                    
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse MCP response: {e}")
                return None

    def analyze_image_sync(self, image_path: str, prompt: str = "What does this image show?") -> Optional[str]:
        """
        SIMPLIFIED RETRY SYSTEM: 3 attempts → restart MCP → repeat forever (never give up)
        Uses thread lock to prevent concurrent access to MCP.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt to accompany the image

        Returns:
            Analysis result as string (blocks until success)
        """
        import time as time_module
        import select
        
        # CRITICAL: Cancel any pending request from previous call
        self._request_cancelled = True
        
        # Acquire lock - this will block if another analyze_image_sync is running
        log.info("🔒 Acquiring MCP lock...")
        with self._mcp_lock:
            log.info("🔓 MCP lock acquired")
            self._request_cancelled = False  # Reset for this request
            
            # Drain any stale responses before starting fresh
            if self.mcp_process and self.mcp_process.stdout:
                try:
                    drained = 0
                    while True:
                        ready, _, _ = select.select([self.mcp_process.stdout], [], [], 0.1)
                        if not ready:
                            break
                        data = self.mcp_process.stdout.readline()
                        if not data:
                            break
                        drained += 1
                        log.debug(f"🗑️ Pre-drained stale response before new request")
                    if drained > 0:
                        log.info(f"🗑️ Drained {drained} stale responses before starting fresh")
                except Exception as e:
                    log.warning(f"Error draining stale responses: {e}")
            
            log.info("🔍 Starting vision analysis (will retry forever until success)")
            
            while True:
                # Check if this request was cancelled by a newer one
                if self._request_cancelled:
                    log.warning("⏹️ Request cancelled by newer call, exiting")
                    return None
                
                try:
                    log.info(f"🚀 Vision attempt {self._attempt_count + 1}/{self.max_attempts_before_restart} (MCP restart #{self._restart_count})")
                    result = asyncio.run(self.analyze_image(image_path, prompt))

                    if result is not None:
                        self.handle_vision_success()
                        log.info("✅ Vision analysis completed successfully!")
                        return result
                    else:
                        should_restart = self.handle_vision_failure("Vision analysis returned None/empty result")
                        if should_restart:
                            self.restart_mcp_server()

                except Exception as e:
                    error_msg = f"Vision analysis exception: {str(e)}"
                    should_restart = self.handle_vision_failure(error_msg)
                    log.error(f"❌ {error_msg}", exc_info=True)
                    if should_restart:
                        self.restart_mcp_server()
                
                # Brief delay between attempts to prevent hammering
                time_module.sleep(2.0)

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
            # FIX: Cache tools list - only fetch once per session, not on every analyze call
            if not self._tools_cached:
                tools_list_id = self._get_next_request_id()
                
                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": tools_list_id,
                    "method": "tools/list",
                    "params": {}
                }

                log.info(f"Requesting available tools (first time only): {json.dumps(list_tools_request, indent=2)}")

                # Send list tools request
                list_tools_json = json.dumps(list_tools_request) + '\n'
                self.mcp_process.stdin.write(list_tools_json.encode())
                self.mcp_process.stdin.flush()

                # Read tools list response, draining any stale responses
                tools_data = self._read_response_with_id_match(tools_list_id, timeout=15.0)
                if tools_data is None:
                    log.error("Failed to get tools list response - will retry tools fetch next call")
                    # Don't return None - we can still try analyze_image without cached tools list
                    # Tools caching will be retried on next call
                elif 'result' in tools_data and 'tools' in tools_data['result']:
                    log.info(f"Available tools: {json.dumps(tools_data, indent=2)}")
                    self._available_tools = tools_data['result']['tools']
                    self._tools_cached = True
                    log.info(f"Found {len(self._available_tools)} available tools (cached for future calls)")
                    for tool in self._available_tools:
                        log.info(f"Tool: {tool.get('name', 'unknown')} - {tool.get('description', 'no description')}")
                else:
                    log.warning(f"tools/list response missing expected structure: {tools_data}")
            else:
                log.debug("Using cached tools list")

            # Use the correct tool name and parameters from the schema
            tool_name = "analyze_image"

            # CRITICAL FIX: Use unique request ID for analysis request
            analyze_request_id = self._get_next_request_id()
            
            # Create MCP request for image analysis with correct schema
            mcp_request = {
                "jsonrpc": "2.0",
                "id": analyze_request_id,
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

            # Read response, draining any stale responses
            log.info(f"Waiting for MCP server response for {tool_name}...")
            response_data = self._read_response_with_id_match(analyze_request_id, timeout=30.0)
            
            if response_data is None:
                log.error(f"Failed to get {tool_name} response (timeout or stale response mismatch)")
                # Check if server is still running
                if self.mcp_process.poll() is not None:
                    log.error(f"MCP server process has terminated with code: {self.mcp_process.returncode}")
                # Return None to trigger retry in analyze_image_sync
                return None
                
            log.info(f"Got MCP response for {tool_name}: id={response_data.get('id')}")

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
    Includes robust retry logic with exponential backoff
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

        # CRITICAL: Add retry state for fallback client
        self.fallback_failure_count = 0
        self.last_fallback_failure_time = 0
        self.fallback_backoff_seconds = 60  # Start with 60 seconds backoff
        self.max_fallback_backoff_seconds = 300  # Max 5 minutes backoff
        self.fallback_temporarily_disabled = False

    def should_attempt_fallback_analysis(self) -> bool:
        """
        Check if fallback vision analysis should be attempted based on failure history and backoff timing

        Returns:
            True if fallback vision analysis should be attempted, False if in backoff period
        """
        current_time = time.time()

        # If fallback is temporarily disabled, check if backoff period has elapsed
        if self.fallback_temporarily_disabled:
            if current_time - self.last_fallback_failure_time >= self.fallback_backoff_seconds:
                # Backoff period elapsed, re-enable fallback with caution
                log.info(f"Fallback vision backoff period elapsed ({self.fallback_backoff_seconds}s). Re-enabling fallback vision analysis.")
                self.fallback_temporarily_disabled = False
                return True
            else:
                # Still in backoff period
                remaining_time = self.fallback_backoff_seconds - (current_time - self.last_fallback_failure_time)
                log.info(f"Fallback vision analysis temporarily disabled. {remaining_time:.0f}s remaining in backoff period.")
                return False

        # If not disabled, allow attempt
        return True

    def handle_fallback_failure(self, error_message: str) -> None:
        """
        Handle fallback vision analysis failure by implementing exponential backoff

        Args:
            error_message: Description of the error that occurred
        """
        self.fallback_failure_count += 1
        self.last_fallback_failure_time = time.time()

        # Calculate exponential backoff: 60s, 120s, 240s, max 300s (5min)
        if self.fallback_failure_count == 1:
            self.fallback_backoff_seconds = 60
        else:
            # Double the backoff time, but cap at max
            self.fallback_backoff_seconds = min(
                self.fallback_backoff_seconds * 2,
                self.max_fallback_backoff_seconds
            )

        # Disable fallback temporarily
        self.fallback_temporarily_disabled = True

        log.error(f"FALLBACK VISION FAILURE #{self.fallback_failure_count}: {error_message}")
        log.error(f"Fallback vision analysis temporarily disabled for {self.fallback_backoff_seconds} seconds (exponential backoff)")

    def handle_fallback_success(self) -> None:
        """
        Reset failure counters after successful fallback vision analysis
        """
        if self.fallback_failure_count > 0:
            log.info(f"Fallback vision analysis succeeded after {self.fallback_failure_count} previous failures. Resetting failure counters.")
            self.fallback_failure_count = 0
            self.fallback_backoff_seconds = 60  # Reset to initial backoff
            self.fallback_temporarily_disabled = False
            self.last_fallback_failure_time = 0

    def analyze_image(self, image_path: str, prompt: str = "What does this image show?") -> Optional[str]:
        """
        Analyze image using direct API calls with robust retry logic

        Args:
            image_path: Path to image file
            prompt: Text prompt

        Returns:
            Analysis result or None if failed and in backoff period
        """
        # CRITICAL: Check if we should attempt fallback vision analysis based on failure history
        if not self.should_attempt_fallback_analysis():
            # We're in a backoff period - return None to indicate vision unavailable
            remaining_time = self.fallback_backoff_seconds - (time.time() - self.last_fallback_failure_time)
            log.warning(f"Fallback vision analysis skipped - in backoff period ({remaining_time:.0f}s remaining)")
            return None

        # Attempt fallback vision analysis with try/catch for robust error handling
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
                        result = response_data['choices'][0]['message']['content']

                        # SUCCESS: Fallback vision analysis completed successfully
                        self.handle_fallback_success()
                        return result
                    else:
                        # FAILURE: Invalid response format
                        error_msg = f"Vision API response missing choices: {response_data}"
                        self.handle_fallback_failure(error_msg)
                        log.error(error_msg)
                        return None
                else:
                    # FAILURE: HTTP error
                    error_msg = f"Vision API HTTP request failed: {response.status_code} - {response.text}"
                    self.handle_fallback_failure(error_msg)
                    log.error(error_msg)
                    return None

        except Exception as e:
            # FAILURE: Exception occurred during fallback vision analysis
            error_msg = f"Fallback vision analysis exception: {str(e)}"
            self.handle_fallback_failure(error_msg)
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