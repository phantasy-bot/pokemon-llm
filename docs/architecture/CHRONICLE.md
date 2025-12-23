# Chronicle Architecture

**Chronicle** is the token-gated content ecosystem for the Pokemon LLM Agent. It mints in-game moments as Zora Coins on the Base network and locks exclusive content (save files, high-res art) behind token ownership.

## 🏗️ System Overview

The system has migrated from a local Node.js sidecar to a scalable **Cloudflare Worker** architecture.

### Components

1.  **Pokemon LLM Agent (Python)**:
    *   Plays the game.
    *   Generates content (screenshots, AI art).
    *   Uploads drafts to the Chronicle Worker via API.

2.  **Chronicle Worker (Cloudflare)**:
    *   **API**: Hono-based REST API running on Edge Workers.
    *   **Database**: **D1** (SQLite) stores drop metadata and token mapping.
    *   **Storage**: **R2** stores images and exclusive files.
    *   **Minting**: Uses `viem` to interact with Zora Protocol on Base.

3.  **Chronicle UI (Cloudflare Worker/Static)**:
    *   React + Vite frontend.
    *   Displays the timeline feed.
    *   Handles wallet connection and "Unlock" signatures.

---

## 🔄 The Flow

### 1. Drop Creation (Agent -> Worker)
When a major achievement occurs:
1.  **Agent**: Sends `POST /api/drop` with images and exclusive files.
2.  **Worker**:
    *   Uploads files to **R2**.
    *   Creates a `Draft` record in **D1**.
    *   (Auto-Post) Mints the Zora Coin on Base.
    *   Updates D1 with the new `contractAddress`.

### 2. Discovery (Frontend -> Worker)
1.  **User**: Visits `chronicle.llmletsplay.com`.
2.  **UI**: Fetches `GET /api/feed`.
3.  **Worker**: Returns public metadata (images, description) from D1.

### 3. Gating & Unlock (User -> Worker)
1.  **User**: Clicks "Unlock" on a drop.
2.  **UI**: Request signature: `"Authenticate Chronicle Access: [ContractAddr] [Nonce]"`.
3.  **UI**: Sends signature to `GET /api/unlock/:id`.
4.  **Worker**:
    *   Verifies signature matches wallet.
    *   Calls **Base RPC** to check `balanceOf(user, contractAddress) > 0`.
    *   If valid, generates a signed R2 URL (Time-limited) for the exclusive file.
    *   Redirects user to the secure download.

### 4. Human-in-the-Loop (Discord -> Worker)
1.  **Notification**: When a draft is created, the Worker sends an Embed to Discord with "Approve", "Edit", and "Delete" buttons.
2.  **Interaction**: User clicks a button in Discord.
3.  **Webhook**: Discord calls `POST /api/interactions` on the Worker.
4.  **Verification**: Worker verifies the `Ed25519` signature using the `DISCORD_PUBLIC_KEY` to ensure authenticity.
5.  **Action**:
    *   **Approve**: Worker triggers the minting process and updates the Discord message to "Published".
    *   **Edit**: Opens the Chronicle Admin UI with `?edit=[id]` for immediate editing.
    *   **Delete**: Marks the draft as deleted in the database.

---

## 📊 Content Strategy

### Achievement Tiers

| Tier | Platform | Content | Gating |
| :--- | :--- | :--- | :--- |
| **Major** | Twitter + Zora | AI Art + Save File | ⭐ High |
| **Minor** | Zora Only | Screenshot | ⭐ Low |
| **Progress** | Zora Only | Collage | None |

### Exclusive Content Types
1.  **The Save File**: The actual `.sav` file at the moment of victory. Allows users to "continue" the run.
2.  **High-Res Art**: 4K upscaled versions of the AI generation.
3.  **Battle Logs**: Full JSON logs of competitive battles.

---

## 🛠️ Tech Stack

*   **Runtime**: Cloudflare Workers (V8 Isolation)
*   **Framework**: Hono
*   **Database**: Cloudflare D1
*   **Storage**: Cloudflare R2
*   **Blockchain**: Base (L2), Zora Protocol
*   **SDKs**: `viem`, `@zoralabs/protocol-sdk`

## 🔐 Security

*   **Zero Trust**: The Admin API (`POST /api/drop`) is protected by Cloudflare Access. The Python Agent authenticates via a **Service Token**.
*   **Edge Gating**: File access is verified at the edge. No direct R2 public access is allowed for exclusive files.
