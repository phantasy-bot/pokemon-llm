import unittest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock httpx before importing service
sys.modules["httpx"] = MagicMock()

import services.solana_token_service
services.solana_token_service.HTTPX_AVAILABLE = True
from services.solana_token_service import SolanaTokenService, ProviderStatus

import logging

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock httpx before importing service
sys.modules["httpx"] = MagicMock()

import services.solana_token_service
services.solana_token_service.HTTPX_AVAILABLE = True
from services.solana_token_service import SolanaTokenService, ProviderStatus

# Setup Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class TestSolanaRPCFallback(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Initialize service with mock config
        self.service = SolanaTokenService(
            token_mint="mint123",
            whale_threshold=1000,
            cache_ttl=60, # 1 min cache
            cooldown_seconds=10 # Short cooldown for testing
        )
        
        # Override providers for testing
        self.service.providers = [
            ProviderStatus(name="provider_A", url="url_A"),
            ProviderStatus(name="provider_B", url="url_B"),
            ProviderStatus(name="provider_C", url="url_C"),
        ]
        self.service._current_provider_index = 0
        
        # Disable caching for logic testing
        self.service.cache.get = MagicMock(return_value=None)
        self.service.cache.set = MagicMock()
        
        # DEBUG
        print(f"DEBUG: HTTPX_AVAILABLE = {services.solana_token_service.HTTPX_AVAILABLE}")
        print(f"DEBUG: service.is_available = {self.service.is_available}")
        print(f"DEBUG: providers = {len(self.service.providers)}")

    async def test_sticky_provider_success(self):
        """Test that the service sticks to the first working provider."""
        # Mock query balance to return success
        async def mock_query(provider, wallet_address):
            print(f"DEBUG: Called _query_balance with {provider.name}")
            return 1000
            
        self.service._query_balance = AsyncMock(side_effect=mock_query)
        
        # Valid length wallet address (32+ chars)
        wallet = "A" * 44
        
        # Make 3 calls
        print("DEBUG: Calling get_token_balance 1")
        await self.service.get_token_balance(wallet)
        await self.service.get_token_balance(wallet)
        await self.service.get_token_balance(wallet)
        
        # Should have called provider A 3 times
        # Verify _current_provider_index is still 0 (Provider A)
        self.assertEqual(self.service._current_provider_index, 0)
        
        # Verify query_balance calls
        calls = self.service._query_balance.call_args_list
        self.assertEqual(len(calls), 3)
        for call in calls:
            # Check the first arg (provider) is provider A
            provider_arg = call[0][0]
            self.assertEqual(provider_arg.name, "provider_A")

    async def test_failover_logic(self):
        """Test that service switches to next provider on error."""
        # Mock functionality: 
        # Call 1: Provider A fails
        # Call 2: Provider B succeeds
        
        async def side_effect(provider, wallet):
            if provider.name == "provider_A":
                raise Exception("Network Error A")
            return 2000

        self.service._query_balance = AsyncMock(side_effect=side_effect)
        
        # Valid wallet
        wallet = "B" * 44
        
        # Call service
        balance = await self.service.get_token_balance(wallet)
        
        # Balance should be from Provider B
        self.assertEqual(balance, 2000)
        
        # Provider A should be disabled
        provider_A = self.service.providers[0]
        self.assertGreater(provider_A.disabled_until, 0)
        
        # Current index should be 1 (Provider B)
        self.assertEqual(self.service._current_provider_index, 1)

    async def test_sticky_on_new_provider(self):
        """Test that after switching, it sticks to the new provider."""
        # Set explicitly to Provider B
        self.service._current_provider_index = 1
        
        self.service._query_balance = AsyncMock(return_value=3000)
        
        wallet = "C" * 44
        await self.service.get_token_balance(wallet)
        await self.service.get_token_balance(wallet)
        
        # Should remain on B
        self.assertEqual(self.service._current_provider_index, 1)
        
        calls = self.service._query_balance.call_args_list
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertEqual(call[0][0].name, "provider_B")

    async def test_all_providers_disabled(self):
        """Test graceful failure when all providers are failing/disabled."""
        # Mark all as disabled manually for setup
        future_time = time.time() + 100
        for p in self.service.providers:
            p.disabled_until = future_time
            
        # Mock query just in case it reaches (should not)
        self.service._query_balance = AsyncMock(return_value=5000)
        
        # Call service
        wallet = "D" * 44
        balance = await self.service.get_token_balance(wallet)
        
        # Should return 0 (failure)
        self.assertEqual(balance, 0)
        
        # Should not have called query_balance at all if logic checks disabled first
        self.service._query_balance.assert_not_called()

    async def test_recovery_after_cooldown(self):
        """Test that a provider becomes valid again after cooldown."""
        # Set Provider A disabled for 0.1s
        self.service.providers[0].disabled_until = time.time() + 0.1
        self.service._current_provider_index = 0
        
        # Wait for cooldown
        await asyncio.sleep(0.2)
        
        # Mock success
        self.service._query_balance = AsyncMock(return_value=6000)
        
        # Call
        wallet = "E" * 44
        balance = await self.service.get_token_balance(wallet)
        
        # Should succeed using Provider A
        self.assertEqual(balance, 6000)
        self.assertEqual(self.service._current_provider_index, 0)
        self.assertEqual(self.service._query_balance.call_args[0][0].name, "provider_A")

    async def test_cycle_through_failures(self):
        """Test that single request cycles through all failures until one works."""
        
        # A fails, B fails, C succeeds
        async def side_effect(provider, wallet):
            if provider.name in ["provider_A", "provider_B"]:
                raise Exception("Fail")
            return 7000
            
        self.service._query_balance = AsyncMock(side_effect=side_effect)
        
        # Call
        wallet = "F" * 44
        balance = await self.service.get_token_balance(wallet)
        
        self.assertEqual(balance, 7000)
        
        # A and B should be disabled
        self.assertGreater(self.service.providers[0].disabled_until, 0)
        self.assertGreater(self.service.providers[1].disabled_until, 0)
        
        # C should be clean
        self.assertEqual(self.service.providers[2].disabled_until, 0)
        
        # Current index should be 2 (Provider C)
        self.assertEqual(self.service._current_provider_index, 2)

if __name__ == '__main__':
    unittest.main()
