# Setup Guide

This guide covers the installation, configuration, and running of the Pokemon LLM Agent.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for UI)
- **mGBA Emulator** (Development build with scaffolding support recommended)
- **Pokemon ROM** (FireRed `.gba` or Red/Blue `.gbc`)

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/phantasy-bot/pokemon-llm
    cd pokemon-llm
    ```

2.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Install UI dependencies:**
    ```bash
    cd llmletsplay
    npm install
    cd ..
    ```

## Configuration

The agent is configured primarily via the `.env` file.

1.  **Create your env file:**

    ```bash
    cp .env.example .env
    ```

2.  **Configure Core Settings:**

    | Variable            | Description                                      |
    | :------------------ | :----------------------------------------------- |
    | `POKEMON_ROM`       | Path to your ROM file (e.g., `roms/firered.gba`) |
    | `OPENAI_API_KEY`    | (If using OpenAI) Your API key                   |
    | `ANTHROPIC_API_KEY` | (If using Claude) Your API key                   |
    | `GEMINI_API_KEY`    | (If using Gemini) Your API key                   |

3.  **Configure Chat Response Service (The Personality):**

    The agent uses a separate LLM for "Lass" personality chat responses.

    - **Development**: Use **Featherless.ai**
      ```ini
      FEATHERLESS_API_KEY=your_key
      FEATHERLESS_MODEL=mistral-7b-instruct
      ```
    - **Production**: Use **Alkahest**
      ```ini
      ALKAHEST_API_KEY=your_key
      ALKAHEST_BASE_URL=https://api.alkahest.ai/v1
      ```

4.  **Configure Twitch Integration:**

    To enable chat interaction, polls, and predictions:

    ```ini
    TWITCH_BOT_TOKEN=oauth:your_token
    TWITCH_CLIENT_ID=your_client_id
    TWITCH_CLIENT_SECRET=your_secret
    TWITCH_CHANNEL=channel_name
    TWITCH_BOT_USERNAME=bot_username
    ```

    **Feature Flags:**

    ```ini
    TWITCH_ENABLE_POLLS=true
    TWITCH_ENABLE_PREDICTIONS=true  # Requires channel:manage:predictions scope
    TWITCH_ENABLE_CHAT_MEMORY=true
    ```

5.  **Configure Pump.fun Integration (Optional):**

    To interact with token chats:

    ```ini
    PUMPFUN_TOKEN_ADDRESS=your_token_address
    PUMPFUN_COOKIE=your_auth_cookie  # Required for sending messages
    ```

6.  **Configure Solana RPC (Optional):**

    For whale detection features:

    ```ini
    # Add your RPC URLs (comma-separated)
    HELIUS_RPC_URL=https://mainnet.helius-rpc.com/...
    ALCHEMY_RPC_URL=https://solana-mainnet.g.alchemy.com/v2/...
    ```

## Running the Agent

1.  **Start the UI (Terminal 1):**

    ```bash
    cd llmletsplay
    npm run dev
    ```

    Access at `http://localhost:5174`.

2.  **Start the Agent (Terminal 2):**

    ```bash
    # Run with default settings (auto mode)
    python run.py --auto

    # Run with specific model
    python run.py --mode OPENAI --auto
    ```

3.  **Start mGBA:**
    - Open mGBA.
    - Load your ROM.
    - Tools -> Scripting -> Load `socketserver.lua`.
    - (The agent should auto-connect).

## Testing Mode

You can run components in test mode without live connections:

```ini
# in .env
Twitch_TEST_MODE=true
PUMPFUN_TEST_MODE=true
```
