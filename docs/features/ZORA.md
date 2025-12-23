# Zora Integration & LLMLetsPlay Brand

This document details the integration of Zora functionality into the Pokemon LLM Agent, establishing the **LLMLetsPlay** onchain brand.

## 🌟 Brand Architecture

**LLMLetsPlay** is the parent brand for AI agents playing games onchain.

*   **Primary Stream**: Multi-platform (Twitch + Pump.fun + Zora)
*   **Zora Handle**: `LLMLetsPlay`
*   **Tokens**:
    *   **$LASS** (Solana/Pump.fun): The meme token for the Lass character.
    *   **LLP Coins** (Base/Zora): Collectible moments minted as Zora coins for achievements.

## 🛠️ Components

### 1. Chronicle Worker (Cloudflare)
Located in `apps/chronicle-worker/`.
A scalable Edge Worker that interfaces with the **Zora Coins SDK**.
*   **Coin Creation**: Mints new ERC-20 coins on Base for achievements.
*   **Storage**: Uses Cloudflare R2 for images/assets.
*   **Database**: Uses Cloudflare D1 for state and draft management.
*   **API**: Exposes HTTP endpoints for the Python agent.

### 2. Zora Chat Service (Python)
Located in `services/zora_chat_service.py`.
*   Connects to Zora's GraphQL WebSocket to receive livestream chat.
*   Integrates with the main loop to allow the agent to respond to Zora viewers.

### 3. Zora Poster Service (Python)
Located in `services/zora_poster_service.py`.
*   Orchestrates the creation of posts (coins).
*   Manages a queue of achievements to prevent spam.
*   Decides between single screenshots or galleries (collages).

### 4. Base Token Service (Python)
Located in `services/base_token_service.py`.
*   Queries ERC-20 token balances on Base network.
*   Used to detect "whales" or holders of the Zora coin to prioritize their chat messages.

### 5. Achievement Tracking
*   **Major Achievements** (Badges, Legendaries): Posted to **Twitter & Zora**.
*   **Minor Achievements** (New routes, catches): Posted to **Zora Only**.
*   **Progress Updates**: Posted to Zora every ~60 cycles if no other activity.

## 🚀 Setup & Configuration

### Prerequisites
1.  **Node.js 18+** (for sidecar)
2.  **Zora API Key** (from [zora.co/settings/developer](https://zora.co/settings/developer))
3.  **Wallet Private Key** (Base enabled) for minting.

### Environment Variables (.env)

```bash
# Zora Configuration
ZORA_API_KEY=your_key
ZORA_USERNAME=LLMLetsPlay
ZORA_CHAT_ENABLED=true

# Zora Posting
ZORA_SIDECAR_URL=http://localhost:3001
ZORA_POSTING_ENABLED=true
ZORA_AUTO_POST=true
ZORA_MIN_POST_INTERVAL=300 # 5 minutes

# Wallet (for sidecar minting)
ZORA_CREATOR_ADDRESS=0x...
ZORA_PRIVATE_KEY=0x...

# Base Token Detection
BASE_TOKEN_ADDRESS=0x... # The contract address of your main coin on Base
BASE_RPC_URL=https://mainnet.base.org
```

### Starting the Worker

See [CHRONICLE.md](../architecture/CHRONICLE.md) for full deployment instructions.

```bash
cd apps/chronicle-worker
npm run deploy
```

The worker is serverless and runs on Cloudflare's Edge.

## 📸 Achievement Types

### Major (Twitter + Zora)
*   Gym Badges
*   Legendary Catches (Articuno, Zapdos, Moltres, Mewtwo)
*   Pokemon Champion
*   Starter Evolution

### Minor (Zora Only)
*   **New Route/City**: Documenting the journey map-by-map.
*   **First Catch**: First time catching a specific species.
*   **Team Updates**: Evolutions, full team.
*   **Key Items**: Bicycle, Silph Scope, etc.

## 💬 Chat Priority System

The agent prioritizes chat messages in this order:

1.  **🐋 Whales** (Holders of >100k $LASS or Base Tokens)
2.  **🟣 Zora Subscribers/Holders**
3.  **💎 Twitch Subscribers**
4.  **🪙 Regular Crypto Chatters** (Pump.fun/Zora)
5.  **👤 Regular Twitch Viewers**

## 📂 File Structure

*   `apps/chronicle-worker/`: Cloudflare backend for minting and state.
*   `services/zora_chat_service.py`: Chat connection.
*   `services/zora_poster_service.py`: Posting logic.
*   `services/base_token_service.py`: Holder detection.
*   `trackers/zora_achievement_tracker.py`: Extended achievement logic.
*   `services/screenshot_manager.py`: Manages screenshot buffer for galleries.
