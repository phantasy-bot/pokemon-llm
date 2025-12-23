import httpx
import logging
import json
import os
import base64
import subprocess
import time
import shutil
import sys
import atexit
import socket

log = logging.getLogger("opencode_client")


class OpenCodeClient:
    def __init__(self, base_url="http://localhost:4096"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        self.http = httpx.Client(timeout=60.0)
        self.chat = self._Chat(self)
        self._last_msg_len = 0
        self.models = self._Models(self)
        self._server_proc = None
        self._has_tried_starting = False

    class _Chat:
        def __init__(self, client):
            self.completions = self._Completions(client)

        class _Completions:
            def __init__(self, client):
                self.client = client

            def create(self, **kwargs):
                return self.client._create_completion(**kwargs)

    class _Models:
        def __init__(self, client):
            self.client = client
            self.data = []  # Mock data

        def list(self):
            # Perform a real connection check by ensuring a session exists
            # This validates that the server is reachable and responsive
            self.client._ensure_session()

            # Return mock model data since OpenCode doesn't have a models endpoint yet
            # but we've now verified the server is actually up and talking
            class ModelList:
                data = [{"id": "opencode-agent"}]

            return ModelList()

    def _start_server(self):
        """Attempts to start the OpenCode server as a subprocess."""
        if self._has_tried_starting:
            return False

        self._has_tried_starting = True
        log.info("🚀 Attempting to start OpenCode server automatically...")

        # 1. Find executable
        opencode_bin = shutil.which("opencode")

        # Fallback for conda environment if not in PATH
        if not opencode_bin:
            conda_prefix = os.environ.get("CONDA_PREFIX")
            if conda_prefix:
                candidate = os.path.join(conda_prefix, "bin", "opencode")
                if os.path.exists(candidate):
                    opencode_bin = candidate

        if not opencode_bin:
            log.error("❌ Could not find 'opencode' executable in PATH.")
            return False

        try:
            # 2. Start subprocess
            log.info(f"Starting: {opencode_bin} --port 4096")
            self._server_proc = subprocess.Popen(
                [opencode_bin, "--port", "4096"],
                stdout=subprocess.DEVNULL,  # Redirect to prevent spam
                stderr=subprocess.PIPE,  # Capture errors if needed
                text=True,
            )

            # Register cleanup
            atexit.register(self._kill_server)

            # 3. Wait for it to be ready (up to 10s)
            log.info("⏳ Waiting for OpenCode server to initialize...")
            for i in range(20):
                if self._server_proc.poll() is not None:
                    # It died immediately
                    err = ""
                    if self._server_proc.stderr:
                        err = self._server_proc.stderr.read()
                    log.error(f"❌ OpenCode server failed to start: {err}")
                    return False

                try:
                    # Check if port is open and responding
                    # We use a raw socket check or just try to connect with httpx
                    # Simple TCP connect check to avoid 404s on unknown endpoints
                    with socket.create_connection(("localhost", 4096), timeout=0.5):
                        return True
                except (socket.error, socket.timeout):
                    pass  # Still starting
                except Exception:
                    pass

                time.sleep(0.5)

            log.error("❌ Timed out waiting for OpenCode server.")
            self._kill_server()
            return False

        except Exception as e:
            log.error(f"Failed to auto-start OpenCode: {e}")
            return False

    def _kill_server(self):
        if self._server_proc:
            try:
                log.info("🛑 Stopping auto-started OpenCode server...")
                self._server_proc.terminate()
                self._server_proc.wait(timeout=2)
            except Exception:
                try:
                    self._server_proc.kill()
                except:
                    pass
            self._server_proc = None

    def _ensure_session(self):
        if not self.session_id:
            try:
                # Create a new session
                # API: POST /session
                # Body: { title: "Pokemon Agent" }
                resp = self.http.post(
                    f"{self.base_url}/session",
                    json={"title": "Pokemon Agent"},
                )
                if resp.status_code != 200:
                    log.error(
                        f"Failed to create session: {resp.status_code} {resp.text}"
                    )
                    raise Exception(f"OpenCode Session Create Failed: {resp.text}")

                data = resp.json()
                self.session_id = data.get("id")
                log.info(f"Created OpenCode session: {self.session_id}")
            except httpx.ConnectError:
                # Auto-start logic
                if not self._has_tried_starting:
                    if self._start_server():
                        # Retry session creation recursively (once)
                        return self._ensure_session()

                log.critical(
                    f"❌ Could not connect to OpenCode server at {self.base_url}"
                )
                log.critical(
                    "   Please verify that 'opencode --port 4096' is running in another terminal."
                )
                # We raise a clean exception to stop the crash loop with a clear message
                raise Exception(
                    "OpenCode server is not running. Please start it with 'opencode --port 4096'"
                )
            except Exception as e:
                log.error(f"Failed to connect to OpenCode: {e}")
                raise

    def _create_completion(self, messages, model=None, **kwargs):
        # 1. State Management
        # If the history length decreased, it means a reset/summary occurred.
        if len(messages) < self._last_msg_len:
            log.info("Context length decreased - assuming reset. Creating new session.")
            self.session_id = None

        self._ensure_session()
        self._last_msg_len = len(messages)

        # 2. Extract Latest Message
        # We assume OpenCode maintains the history statefully.
        # We only send the *last* message (the new user prompt).
        if not messages:
            return self._wrap_response("")

        last_msg = messages[-1]

        # 3. Extract System Prompt
        # We check for a system prompt to send as a parameter
        system_content = None
        sys_msg = next((m for m in messages if m.get("role") == "system"), None)
        if sys_msg:
            content = sys_msg.get("content")
            if isinstance(content, list):
                system_content = " ".join(
                    [x.get("text", "") for x in content if x.get("type") == "text"]
                )
            else:
                system_content = str(content)

        # 4. Prepare Body Parts
        parts = []
        content = last_msg.get("content")

        if isinstance(content, str):
            parts.append({"type": "text", "text": content})
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    parts.append({"type": "text", "text": item.get("text")})
                elif item.get("type") == "image_url":
                    img_url = item.get("image_url", {}).get("url", "")
                    if img_url.startswith("data:image"):
                        try:
                            # Parse mime type from data URI
                            # Format: data:image/png;base64,...
                            header, encoded = img_url.split(",", 1)
                            mime = header.split(":")[1].split(";")[0]

                            # OpenCode expects 'file' type for images with 'url' field
                            parts.append(
                                {
                                    "type": "file",
                                    "mime": mime,
                                    "url": img_url,  # Pass full data URI
                                }
                            )
                        except Exception as e:
                            log.error(f"Failed to parse data URI: {e}")
                    else:
                        # For remote URLs, we can also use 'file' type if supported,
                        # or just pass it through if OpenCode supports it.
                        # For now, let's try passing as file with URL
                        parts.append(
                            {
                                "type": "file",
                                "mime": "image/jpeg",  # Default fallback
                                "url": img_url,
                            }
                        )

        # 5. Construct Request Body
        body = {"parts": parts, "noReply": False}

        if system_content:
            body["system"] = system_content

        # Model handling
        # Ignore placeholder model "opencode-agent"
        if model and model != "opencode-agent":
            if "/" in model:
                p, m = model.split("/", 1)
                body["model"] = {"providerID": p, "modelID": m}
            else:
                body["model"] = {"modelID": model}

        # 6. Send Request
        try:
            url = f"{self.base_url}/session/{self.session_id}/message"
            # log.info(f"Sending to OpenCode: {url}")
            # log.debug(f"Body: {json.dumps(body)[:200]}...") # Log truncated body

            resp = self.http.post(url, json=body)
            resp.raise_for_status()

            response_content = ""
            data = resp.json()

            # Parse response parts
            # Response format: { info: Message, parts: Part[] }
            if "parts" in data:
                for p in data["parts"]:
                    if p.get("type") == "text":
                        response_content += p.get("text", "")

            return self._wrap_response(response_content)

        except httpx.HTTPStatusError as e:
            log.error(
                f"OpenCode API Error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            log.error(f"Prompt failed: {e}")
            raise

    def _wrap_response(self, content):
        class Message:
            def __init__(self, c):
                self.content = c

        class Choice:
            def __init__(self, c):
                self.message = Message(c)

        class Response:
            def __init__(self, c):
                self.choices = [Choice(c)]

        return Response(content)
