import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
import httpx

log = logging.getLogger("chronicle_client")


class ChronicleClient:
    """
    Client for interacting with the Chronicle Cloudflare Worker.
    Handles authentication, retries, and multipart file uploads.
    """

    def __init__(self):
        self.base_url = os.getenv("ZORA_SIDECAR_URL", "http://localhost:8787")
        self.api_key = os.getenv("CHRONICLE_SECRET_KEY")

        # Cloudflare Access Service Token (for Zero Trust)
        self.cf_client_id = os.getenv("CF_ACCESS_CLIENT_ID")
        self.cf_client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")

        self._client: Optional[httpx.AsyncClient] = None

        if not self.api_key:
            log.warning(
                "CHRONICLE_SECRET_KEY not set. Chronicle interaction will fail."
            )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def create_draft(
        self,
        name: str,
        symbol: str,
        description: str,
        attributes: List[Dict[str, Any]],
        image_path: str,
        gallery_paths: Optional[List[str]] = None,
        exclusive_path: Optional[str] = None,
        status: str = "draft",
    ) -> bool:
        """
        Create a draft drop in Chronicle.
        """
        if not self.api_key:
            log.error("Cannot create draft: Missing API Key")
            return False

        client = await self._get_client()
        files_list = []
        open_files = []

        try:
            # 1. Main Image
            if image_path and os.path.exists(image_path):
                f = open(image_path, "rb")
                open_files.append(f)
                files_list.append(("image", ("image.png", f, "image/png")))
            else:
                log.error(f"Image path not found: {image_path}")
                return False

            # 2. Gallery Images
            if gallery_paths:
                for idx, path in enumerate(gallery_paths):
                    if os.path.exists(path):
                        f = open(path, "rb")
                        open_files.append(f)
                        files_list.append(
                            ("gallery", (f"gallery_{idx}.png", f, "image/png"))
                        )

            # 3. Exclusive Content
            if exclusive_path and os.path.exists(exclusive_path):
                f = open(exclusive_path, "rb")
                open_files.append(f)
                files_list.append(
                    ("exclusive", ("exclusive.dat", f, "application/octet-stream"))
                )

            # 4. Metadata
            data = {
                "name": name,
                "symbol": symbol,
                "description": description,
                "attributes": json.dumps(attributes),
                "status": status,
            }

            # 5. Prepare Headers
            headers = {"x-api-key": self.api_key}
            if self.cf_client_id and self.cf_client_secret:
                headers["CF-Access-Client-Id"] = self.cf_client_id
                headers["CF-Access-Client-Secret"] = self.cf_client_secret

            # 6. Send with Retry
            max_retries = 3
            response = None

            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        f"{self.base_url}/api/drop",
                        data=data,
                        files=files_list,
                        headers=headers,
                    )
                    break
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    if attempt == max_retries - 1:
                        log.error(
                            f"Chronicle connection failed after {max_retries} attempts: {e}"
                        )
                        return False
                    await asyncio.sleep(2 * (attempt + 1))

            if response and response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    log.info(f"✅ Draft created in Chronicle: {name}")
                    return True
                else:
                    log.error(f"Chronicle returned error: {result.get('error')}")
            else:
                status_code = response.status_code if response else "No Response"
                text = response.text if response else ""
                log.error(f"Chronicle HTTP Error {status_code}: {text}")

            return False

        except Exception as e:
            log.error(f"Chronicle client error: {e}")
            return False

        finally:
            for f in open_files:
                f.close()


# Singleton
_chronicle_client: Optional[ChronicleClient] = None


def get_chronicle_client() -> ChronicleClient:
    global _chronicle_client
    if _chronicle_client is None:
        _chronicle_client = ChronicleClient()
    return _chronicle_client
