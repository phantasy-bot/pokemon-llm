# --- services/base_token_service.py ---
"""
Base (EVM) Token Balance Service for LLMLetsPlay (Zora/Base) Tokens.

Determines if a user is a "whale" or token holder on Base network.
Used for prioritizing chat messages from token holders.

Features:
- Queries ERC-20 token balances via JSON-RPC
- Multi-provider fallback (Alchemy, QuickNode, Public)
- LRU Caching
- No Web3.py dependency (uses raw JSON-RPC)
"""

import asyncio
import logging
import time
import json
import os
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass
from collections import OrderedDict

log = logging.getLogger("base_token")

# Check if httpx is available
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    log.warning("httpx not installed. Base token queries disabled.")

# Configuration
BASE_TOKEN_ADDRESS = os.getenv("BASE_TOKEN_ADDRESS", "")
WHALE_THRESHOLD = int(os.getenv("BASE_WHALE_THRESHOLD", "10000"))
CACHE_TTL = int(os.getenv("BASE_CACHE_TTL", "900"))  # 15 min default

# ERC-20 balanceOf selector: keccak256("balanceOf(address)")[:4]
BALANCE_OF_SELECTOR = "0x70a08231"

# RPC Providers
RPC_PROVIDERS = [
    {
        "name": "alchemy",
        "url_template": "https://base-mainnet.g.alchemy.com/v2/{api_key}",
        "api_key_env": "ALCHEMY_BASE_API_KEY",
    },
    {
        "name": "quicknode",
        "url_template": "{api_key}",  # QuickNode provides full URL
        "api_key_env": "QUICKNODE_BASE_URL",
    },
    {
        "name": "public",
        "url_template": "https://mainnet.base.org",
        "api_key_env": None,
    },
]


@dataclass
class ProviderStatus:
    """Tracks status of an RPC provider."""

    name: str
    url: str
    is_available: bool = True
    last_error: Optional[str] = None
    error_count: int = 0
    disabled_until: float = 0


class LRUCache:
    """Simple LRU cache for token balances."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, Tuple[float, int]] = OrderedDict()

    def get(self, key: str) -> Optional[int]:
        if key not in self._cache:
            return None
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: int):
        if key in self._cache:
            self._cache.move_to_end(key)
        elif len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (time.time(), value)


class BaseTokenService:
    """
    Service for querying ERC-20 token balances on Base network.
    """

    def __init__(
        self,
        token_address: Optional[str] = None,
        whale_threshold: Optional[int] = None,
        cache_ttl: Optional[int] = None,
    ):
        self.token_address = token_address or BASE_TOKEN_ADDRESS
        self.whale_threshold = whale_threshold or WHALE_THRESHOLD
        self.cache = LRUCache(ttl_seconds=cache_ttl or CACHE_TTL)

        self.providers: List[ProviderStatus] = []
        self._init_providers()
        self._current_provider_index = 0
        self._client: Optional[httpx.AsyncClient] = None

        # Stats
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "api_errors": 0,
            "whales_detected": 0,
        }

        if not self.token_address:
            log.warning("No Base token address configured. Holder detection disabled.")

    def _init_providers(self):
        """Initialize RPC providers."""
        for config in RPC_PROVIDERS:
            api_key = None
            if config["api_key_env"]:
                api_key = os.getenv(config["api_key_env"], "")
                if not api_key:
                    continue

            if api_key:
                url = config["url_template"].format(api_key=api_key)
            else:
                url = config["url_template"]

            self.providers.append(ProviderStatus(name=config["name"], url=url))

        if not self.providers:
            # Add public fallback if nothing else configured
            self.providers.append(
                ProviderStatus(name="public", url="https://mainnet.base.org")
            )
            log.info("Using public Base RPC (no API keys found)")

    async def _get_client(self) -> httpx.AsyncClient:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx not installed")

        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    @property
    def is_available(self) -> bool:
        return HTTPX_AVAILABLE and bool(self.token_address) and len(self.providers) > 0

    async def get_token_balance(self, wallet_address: str) -> int:
        """Get raw token balance for wallet."""
        if not self.is_available or not wallet_address:
            return 0

        # Check cache
        cache_key = f"{wallet_address}:{self.token_address}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.stats["cache_hits"] += 1
            return cached

        self.stats["cache_misses"] += 1

        # Try providers
        attempts = 0
        max_attempts = len(self.providers) * 2

        while attempts < max_attempts:
            attempts += 1
            provider = self.providers[self._current_provider_index]

            if provider.disabled_until > time.time():
                self._rotate_provider()
                continue

            try:
                balance = await self._query_balance(provider, wallet_address)

                # Success
                self.cache.set(cache_key, balance)
                self.stats["api_calls"] += 1
                provider.error_count = 0
                return balance

            except Exception as e:
                self.stats["api_errors"] += 1
                log.warning(f"Base RPC error from {provider.name}: {e}")

                provider.disabled_until = time.time() + 300  # 5 min cooldown
                provider.last_error = str(e)
                provider.error_count += 1
                self._rotate_provider()

        return 0

    def _rotate_provider(self):
        self._current_provider_index = (self._current_provider_index + 1) % len(
            self.providers
        )

    async def _query_balance(
        self, provider: ProviderStatus, wallet_address: str
    ) -> int:
        """Execute eth_call via JSON-RPC."""
        client = await self._get_client()

        # Prepare data: selector + padded address (remove 0x, pad to 64 chars)
        clean_addr = wallet_address.lower().replace("0x", "")
        padded_addr = clean_addr.rjust(64, "0")
        data = f"{BALANCE_OF_SELECTOR}{padded_addr}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": self.token_address, "data": data}, "latest"],
        }

        response = await client.post(provider.url, json=payload)
        response.raise_for_status()

        res_data = response.json()
        if "error" in res_data:
            raise Exception(res_data["error"].get("message", "Unknown RPC error"))

        hex_balance = res_data.get("result", "0x0")
        return int(hex_balance, 16)

    async def is_holder(self, wallet_address: str) -> bool:
        """Check if wallet holds significant amount of tokens."""
        if not self.is_available:
            return False

        balance = await self.get_token_balance(wallet_address)

        # Assuming 18 decimals for standard ERC-20
        # If your token has different decimals, adjust here
        decimals = 18
        human_balance = balance / (10**decimals)

        is_whale = human_balance >= self.whale_threshold
        if is_whale:
            self.stats["whales_detected"] += 1
            log.info(
                f"🐋 Base Whale detected! {wallet_address[:6]}... holds {human_balance:.0f}"
            )

        return is_whale

    async def check_holder_status_batch(
        self, wallet_addresses: List[str]
    ) -> Dict[str, bool]:
        """Check status for multiple wallets."""
        if not self.is_available:
            return {addr: False for addr in wallet_addresses}

        # Concurrency limit
        semaphore = asyncio.Semaphore(5)

        async def check_one(addr: str) -> Tuple[str, bool]:
            async with semaphore:
                return (addr, await self.is_holder(addr))

        tasks = [check_one(addr) for addr in wallet_addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        status = {}
        for result in results:
            if isinstance(result, BaseException):
                continue
            addr, is_holder = result
            status[addr] = is_holder

        return status

    async def close(self):
        if self._client:
            await self._client.aclose()


# Singleton
_base_token_service: Optional[BaseTokenService] = None


def get_base_token_service() -> BaseTokenService:
    global _base_token_service
    if _base_token_service is None:
        _base_token_service = BaseTokenService()
    return _base_token_service
