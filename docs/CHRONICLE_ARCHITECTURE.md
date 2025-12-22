# Chronicle Architecture: Token-Gated Content System

Chronicle is an ecosystem that allows the Pokemon LLM Agent to mint moments as Zora Coins while simultaneously "locking" exclusive content behind those coins.

## 🏗️ System Overview

The system consists of three main components:

1.  **Pokemon LLM Agent**: The content creator. Plays the game, generates assets, and triggers drops.
2.  **Chronicle Server** (formerly Zora Sidecar): The backend. Mints coins, stores exclusive files securely, and verifies ownership for access.
3.  **Chronicle UI**: The frontend. Displays the timeline and allows holders to unlock exclusive content.

## 🔄 The Flow

### 1. Drop Creation (Agent -> Server)
When the agent triggers a major achievement (e.g., "Elite 4 Defeated"):
1.  **Agent**: Generates a *Public Image* (e.g., a cool AI render of the victory).
2.  **Agent**: Generates/Collects *Exclusive Content* (e.g., the raw save file, a high-res wallpaper, or a full battle log).
3.  **Agent**: Sends both files to `Chronicle Server` via `POST /api/drop`.
4.  **Server**:
    *   Uploads *Public Image* to IPFS.
    *   Mints a Zora Coin on Base using the SDK.
    *   Saves *Exclusive Content* to a secure, private directory (not exposed via HTTP).
    *   Records the `Coin Address` -> `Exclusive File Path` mapping in a local database.

### 2. Discovery (Frontend -> Server)
1.  **Frontend**: Requests `GET /api/feed`.
2.  **Server**: Returns a list of drops, including metadata like:
    *   Coin Address
    *   Name/Description
    *   Public Image URL
    *   `hasExclusiveContent`: true/false

### 3. Gating & Access (Frontend -> User -> Server)
1.  **User**: Connects wallet on Chronicle UI.
2.  **User**: Clicks "Unlock" on a drop.
3.  **Frontend**: Prompts user to sign a message: `"Authenticate Chronicle Access: [CoinAddress] [Timestamp]"`.
4.  **Frontend**: Sends signature + wallet address to `GET /api/content/:coinAddress`.
5.  **Server**:
    *   Verifies the signature matches the wallet.
    *   Queries Blockchain (RPC) to check if `balanceOf(wallet, coinAddress) > 0`.
    *   If valid, streams the exclusive file back to the user.

## 🛠️ Technical Stack

### Chronicle Server (`apps/chronicle-server`)
*   **Runtime**: Node.js
*   **Framework**: Express
*   **Database**: SQLite (`better-sqlite3`) - Simple, local, persistent.
*   **Storage**: Local filesystem (`./secure_storage/`).
*   **Blockchain**: `viem` + `@zoralabs/coins-sdk`.

### Chronicle UI (`apps/chronicle-ui`)
*   **Framework**: Vite + React
*   **Web3**: Wagmi + Viem
*   **Styling**: Tailwind CSS

## 🏳️ Feature Flags

To ensure this system is optional for the main agent:

*   `CHRONICLE_ENABLED` (bool): Master switch.
*   `CHRONICLE_API_URL` (string): URL of the chronicle server.
*   `CHRONICLE_GATING_ENABLED` (bool): Whether to attempt uploading exclusive content.

## 🔒 Security Model

*   **Exclusive Files**: Stored outside the static web root. Cannot be accessed via direct URL.
*   **Verification**: Done strictly server-side via RPC calls to the Base network.
*   **Signatures**: Replay protection via timestamps (optional but recommended) or simple nonces.
