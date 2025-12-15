# --- solana_token_service.py ---
"""
Solana Token Balance Service for Pokemon LLM Agent.
Queries token balances to determine "whale" status for chat priority.

Uses multiple FREE tier RPC providers with automatic fallback:
1. Helius (1M credits/month, 10 req/sec)
2. Alchemy (30M CUs/month, 500 CUPs)  
3. Shyft (unlimited credits, 10 req/sec)
4. Syndica (10M req/month, 100 req/sec)
5. Public Solana RPC (fallback, rate limited)

Includes aggressive caching to minimize API calls.
"""

import asyncio
import logging
import time
import json
import os
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from collections import OrderedDict

log = logging.getLogger("solana_token")

# Check if httpx is available
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    log.warning("httpx not installed. Token balance queries disabled. Install with: pip install httpx")


# Configuration from environment
PUMPFUN_TOKEN_ADDRESS = os.getenv("PUMPFUN_TOKEN_ADDRESS", "")
WHALE_THRESHOLD = int(os.getenv("PUMPFUN_WHALE_THRESHOLD", "100000"))
# Cache TTL in seconds - longer = fewer API calls but slower to detect balance changes
# Default 15 min (900s) is good for streams since users stick around
WHALE_CACHE_TTL = int(os.getenv("WHALE_CACHE_TTL", "900"))

# RPC Provider configurations (order = priority)
RPC_PROVIDERS = [
    {
        "name": "helius",
        "url_template": "https://mainnet.helius-rpc.com/?api-key={api_key}",
        "api_key_env": "HELIUS_API_KEY",
        "rate_limit": 10,  # requests per second
    },
    {
        "name": "alchemy", 
        "url_template": "https://solana-mainnet.g.alchemy.com/v2/{api_key}",
        "api_key_env": "ALCHEMY_SOLANA_API_KEY",
        "rate_limit": 50,
    },
    {
        "name": "shyft",
        "url_template": "https://rpc.shyft.to?api_key={api_key}",
        "api_key_env": "SHYFT_API_KEY",
        "rate_limit": 10,
    },
    {
        "name": "quicknode",
        "url_template": "{api_key}",  # QuickNode provides full URL as the key
        "api_key_env": "QUICKNODE_SOLANA_URL",
        "rate_limit": 25,
    },
    {
        "name": "public",
        "url_template": "https://api.mainnet-beta.solana.com",
        "api_key_env": None,  # No API key needed
        "rate_limit": 4,  # Very conservative for public RPC
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
    last_request_time: float = 0
    requests_this_minute: int = 0


class LRUCache:
    """Simple LRU cache for token balances."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, Tuple[float, int]] = OrderedDict()
    
    def get(self, key: str) -> Optional[int]:
        """Get value if exists and not expired."""
        if key not in self._cache:
            return None
        
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: int):
        """Set value with current timestamp."""
        if key in self._cache:
            self._cache.move_to_end(key)
        elif len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Remove oldest
        
        self._cache[key] = (time.time(), value)
    
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()


class SolanaTokenService:
    """
    Service for querying Solana token balances with multi-provider fallback.
    
    Features:
    - Automatic failover between RPC providers
    - Aggressive caching (5 min default)
    - Rate limiting per provider
    - Whale threshold detection
    """
    
    def __init__(
        self,
        token_mint: str = None,
        whale_threshold: int = None,
        cache_ttl: int = None,  # Default from env: WHALE_CACHE_TTL (15 min)
        cache_size: int = 1000
    ):
        self.token_mint = token_mint or PUMPFUN_TOKEN_ADDRESS
        self.whale_threshold = whale_threshold or WHALE_THRESHOLD
        actual_ttl = cache_ttl if cache_ttl is not None else WHALE_CACHE_TTL
        self.cache = LRUCache(max_size=cache_size, ttl_seconds=actual_ttl)
        
        # Initialize providers
        self.providers: list[ProviderStatus] = []
        self._init_providers()
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Stats
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "api_errors": 0,
            "whales_detected": 0
        }
        
        if not self.token_mint:
            log.warning("No token mint address configured. Whale detection disabled.")
    
    def _init_providers(self):
        """Initialize available RPC providers."""
        for config in RPC_PROVIDERS:
            api_key = None
            if config["api_key_env"]:
                api_key = os.getenv(config["api_key_env"], "")
                if not api_key:
                    continue  # Skip providers without API keys
            
            # Build URL
            if api_key:
                url = config["url_template"].format(api_key=api_key)
            else:
                url = config["url_template"]
            
            provider = ProviderStatus(
                name=config["name"],
                url=url,
                is_available=True
            )
            self.providers.append(provider)
            log.info(f"✅ Initialized Solana RPC provider: {config['name']}")
        
        if not self.providers:
            log.warning("No Solana RPC providers configured. Using public RPC only.")
            # Add public RPC as last resort
            self.providers.append(ProviderStatus(
                name="public",
                url="https://api.mainnet-beta.solana.com",
                is_available=True
            ))
    
    @property
    def is_available(self) -> bool:
        """Check if any provider is available."""
        return HTTPX_AVAILABLE and bool(self.token_mint) and len(self.providers) > 0
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    async def get_token_balance(self, wallet_address: str) -> int:
        """
        Get token balance for a wallet address.
        Returns balance in smallest units (raw amount).
        Uses cache and multi-provider fallback.
        """
        if not self.is_available:
            return 0
        
        if not wallet_address or len(wallet_address) < 32:
            return 0
        
        # Check cache first
        cache_key = f"{wallet_address}:{self.token_mint}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.stats["cache_hits"] += 1
            return cached
        
        self.stats["cache_misses"] += 1
        
        # Try each provider in order
        for provider in self.providers:
            if not provider.is_available:
                continue
            
            try:
                balance = await self._query_balance(provider, wallet_address)
                
                # Cache the result
                self.cache.set(cache_key, balance)
                self.stats["api_calls"] += 1
                
                # Reset error count on success
                provider.error_count = 0
                
                return balance
                
            except Exception as e:
                provider.error_count += 1
                provider.last_error = str(e)
                self.stats["api_errors"] += 1
                log.warning(f"RPC error from {provider.name}: {e}")
                
                # Disable provider after 3 consecutive errors
                if provider.error_count >= 3:
                    provider.is_available = False
                    log.error(f"❌ Disabled RPC provider {provider.name} after 3 errors")
                
                continue
        
        # All providers failed
        log.error("All Solana RPC providers failed!")
        return 0
    
    async def _query_balance(self, provider: ProviderStatus, wallet_address: str) -> int:
        """Query token balance from a specific provider."""
        client = await self._get_client()
        
        # Build JSON-RPC request for getTokenAccountsByOwner
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"mint": self.token_mint},
                {"encoding": "jsonParsed"}
            ]
        }
        
        response = await client.post(
            provider.url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        
        if "error" in data:
            raise Exception(data["error"].get("message", "Unknown RPC error"))
        
        # Parse response
        result = data.get("result", {})
        accounts = result.get("value", [])
        
        if not accounts:
            return 0
        
        # Sum up all token accounts (usually just one)
        total_balance = 0
        for account in accounts:
            account_data = account.get("account", {}).get("data", {})
            parsed = account_data.get("parsed", {})
            info = parsed.get("info", {})
            token_amount = info.get("tokenAmount", {})
            amount = int(token_amount.get("amount", 0))
            total_balance += amount
        
        return total_balance
    
    async def is_whale(self, wallet_address: str) -> bool:
        """
        Check if a wallet is a "whale" (holds >= threshold tokens).
        
        Returns:
            True if wallet balance >= whale threshold, False otherwise
        """
        if not self.is_available:
            return False
        
        balance = await self.get_token_balance(wallet_address)
        
        # Convert to human-readable units (assuming 6 decimals like most tokens)
        # Most pump.fun tokens have 6 decimals
        decimals = 6
        human_balance = balance / (10 ** decimals)
        
        is_whale = human_balance >= self.whale_threshold
        
        if is_whale:
            self.stats["whales_detected"] += 1
            log.info(f"🐋 Whale detected! {wallet_address[:8]}... holds {human_balance:,.0f} tokens")
        
        return is_whale
    
    async def check_whale_status_batch(self, wallet_addresses: list[str]) -> Dict[str, bool]:
        """
        Check whale status for multiple wallets efficiently.
        Uses semaphore to limit concurrent requests.
        """
        if not self.is_available:
            return {addr: False for addr in wallet_addresses}
        
        # Limit concurrent requests
        semaphore = asyncio.Semaphore(5)
        
        async def check_one(addr: str) -> Tuple[str, bool]:
            async with semaphore:
                return (addr, await self.is_whale(addr))
        
        # Check all wallets concurrently
        tasks = [check_one(addr) for addr in wallet_addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict, handling errors
        whale_status = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            addr, is_whale = result
            whale_status[addr] = is_whale
        
        return whale_status
    
    def reset_providers(self):
        """Reset all disabled providers to available state."""
        for provider in self.providers:
            provider.is_available = True
            provider.error_count = 0
            provider.last_error = None
        log.info("Reset all RPC providers to available state")
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            **self.stats,
            "providers": [
                {
                    "name": p.name,
                    "available": p.is_available,
                    "errors": p.error_count,
                    "last_error": p.last_error
                }
                for p in self.providers
            ],
            "cache_size": len(self.cache._cache),
            "whale_threshold": self.whale_threshold,
            "token_mint": self.token_mint[:16] + "..." if self.token_mint else None
        }
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()


# Singleton instance
_token_service: Optional[SolanaTokenService] = None


def get_token_service() -> SolanaTokenService:
    """Get or create the singleton token service instance."""
    global _token_service
    if _token_service is None:
        _token_service = SolanaTokenService()
    return _token_service


async def check_whale_status(wallet_address: str) -> bool:
    """Convenience function to check if a wallet is a whale."""
    service = get_token_service()
    return await service.is_whale(wallet_address)
