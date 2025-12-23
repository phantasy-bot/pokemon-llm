# Discord Approval Setup (Chronicle Worker)

The project uses **Discord Interactions (Buttons)** powered by the Chronicle Cloudflare Worker for a stateless, human-in-the-loop approval workflow. 

## Overview

1.  **Agent** creates a `Draft` drop in Chronicle.
2.  **Worker** sends a message to your Discord channel with the image and buttons:
    *   `Approve & Publish`: Mints the Zora coin immediately.
    *   `Edit in Chronicle`: Deep-links to the Admin UI for editing.
    *   `Delete`: Marks the draft as deleted.
3.  **Discord** sends webhooks to the Worker's `/api/interactions` endpoint when buttons are clicked.

## Setup Steps

### 1. Create a Discord Application

1.  Go to [Discord Developer Portal](https://discord.com/developers/applications).
2.  Create a **New Application** (e.g., "Chronicle Bot").
3.  Copy the **Application ID** (This is your `DISCORD_APP_ID`).
4.  Copy the **Public Key** (This is your `DISCORD_PUBLIC_KEY`).

### 2. Configure Bot

1.  Go to the **Bot** tab.
2.  Click **Reset Token** to get your **Bot Token** (This is your `DISCORD_BOT_TOKEN`).
3.  Disable "Public Bot" (unless you want others to invite it).

### 3. Deploy Worker & Set Secrets

Before you can finish the Discord setup, you must deploy your Chronicle Worker so it has a public URL.

1.  **Set Secrets** in Cloudflare:
    ```bash
    cd apps/chronicle-worker
    npx wrangler secret put DISCORD_APP_ID
    npx wrangler secret put DISCORD_PUBLIC_KEY
    npx wrangler secret put DISCORD_BOT_TOKEN
    npx wrangler secret put DISCORD_CHANNEL_ID
    ```
    *   `DISCORD_CHANNEL_ID`: Right-click your desired channel in Discord (Developer Mode On) and "Copy ID".

2.  **Deploy**:
    ```bash
    npm run deploy
    ```
    Note your worker URL (e.g., `https://chronicle-worker.yourname.workers.dev`).

### 4. Configure Interactions Endpoint

1.  Back in the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Go to **General Information**.
3.  Scroll to **Interactions Endpoint URL**.
4.  Enter your worker URL appended with `/api/interactions`:
    ```
    https://chronicle-worker.yourname.workers.dev/api/interactions
    ```
5.  Click **Save Changes**.
    *   Discord will send a test ping. If your worker is configured correctly (and verified the signature), it will save successfully. If it fails, check your `DISCORD_PUBLIC_KEY`.

### 5. Invite Bot

1.  Go to **OAuth2** -> **URL Generator**.
2.  Select `bot` scope.
3.  Select Permissions: `Send Messages`, `Embed Links`, `Use External Emojis` (optional).
4.  Copy the URL and invite it to your server.
