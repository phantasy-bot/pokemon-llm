# Unified Cloudflare Setup Guide

This guide covers the complete setup for the **Chronicle** infrastructure on Cloudflare, including Workers, D1 Database, R2 Storage, and Zero Trust security.

## 🏗️ Architecture

The system is deployed entirely on Cloudflare's edge network:

| Component | Service | Name |
| :--- | :--- | :--- |
| **Backend API** | Cloudflare Workers | `llmletsplay-chronicle-worker` |
| **Frontend UI** | Cloudflare Workers (Assets) | `llmletsplay-chronicle-ui` |
| **Database** | D1 (SQLite) | `llmletsplay-chronicle-db` |
| **Storage** | R2 (Object Storage) | `llmletsplay-chronicle-assets` |
| **Security** | Zero Trust (Access) | `Service Token` authentication |

---

## 🚀 1. Initial Setup

### Prerequisites
*   Cloudflare Account
*   Node.js & npm
*   Wrangler CLI (`npm install -g wrangler`)

### Step A: Infrastructure Creation

1.  **Create D1 Database**
    ```bash
    wrangler d1 create llmletsplay-chronicle-db
    ```
    *Copy the `database_id` output.*

2.  **Create R2 Bucket**
    ```bash
    wrangler r2 bucket create llmletsplay-chronicle-assets
    ```

### Step B: Configure Worker (`apps/chronicle-worker`)

1.  Update `wrangler.toml` with your `database_id` and bucket binding.
2.  **Set Secrets** (Do not commit these!):
    ```bash
    wrangler secret put ZORA_PRIVATE_KEY
    wrangler secret put CHRONICLE_SECRET_KEY
    wrangler secret put TWITTER_API_KEY
    wrangler secret put TWITTER_API_SECRET
    wrangler secret put TWITTER_ACCESS_TOKEN
    wrangler secret put TWITTER_ACCESS_TOKEN_SECRET
    ```

### Step C: Deploy Schema

1.  Run the migration using the provided schema file:
    ```bash
    wrangler d1 execute llmletsplay-chronicle-db --file=schema.sql
    ```

### Step D: Deploy Worker & UI

```bash
# Backend
cd apps/chronicle-worker
npm run deploy

# Frontend
cd apps/chronicle-ui
npm run deploy
```

---

## 🔒 2. Zero Trust Security

To secure your Worker while allowing public access to the feed, you must create **Separate Applications** in Cloudflare Access.

### Strategy: "Public Read, Private Write"

We create **3 Applications** for the same domain (`llmletsplay-chronicle-worker.phantasybot.workers.dev`):

1.  **Public Feed** (Path: `/api/feed`) -> **Bypass** (Allows Everyone)
2.  **Public Uploads** (Path: `/uploads`) -> **Bypass** (Allows Everyone)
3.  **Admin/Agent** (Path: `/`) -> **Service Auth** (Requires Token)

### Step A: Create Service Token
1.  Go to **Zero Trust Dashboard** > **Access** > **Service Auth**.
2.  Create Token: `chronicle-agent`.
3.  Add `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` to your local `.env`.

### Step B: Configure Policies
Create the Cloudflare Access applications matching the strategy above. Ensure the "Admin" policy requires the Service Token you created.

---

## 🌐 3. Custom Domains & Routes

We use Cloudflare Worker Routes to map custom domains.

### Production
*   **API**: `chronicle-api.llmletsplay.com` -> `llmletsplay-chronicle-worker`
*   **UI**: `chronicle.llmletsplay.com` -> `llmletsplay-chronicle-ui`

### Development (Base Sepolia)
*   **API**: `chronicle-api-dev.llmletsplay.com` -> `llmletsplay-chronicle-worker-dev`
*   **UI**: `chronicle-dev.llmletsplay.com` -> `llmletsplay-chronicle-ui-dev`

---

## 4. Development Environment

To deploy to the dev environment:

```bash
# Backend (uses Base Sepolia RPC)
wrangler deploy --env dev

# Frontend
wrangler deploy --env dev
```

This uses the separate `llmletsplay-chronicle-db-dev` and `llmletsplay-chronicle-assets-dev` resources defined in `wrangler.toml`.
