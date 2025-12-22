# Chronicle Cloudflare Migration Guide

This guide details how to migrate the Chronicle backend from a local Node.js server to a scalable Cloudflare Worker architecture using D1 (Database) and R2 (Storage).

## 1. Architecture

| Component | Current (Node.js) | New (Cloudflare) |
| :--- | :--- | :--- |
| **Runtime** | Express (Node.js) | Hono (Workers V8) |
| **Database** | SQLite (Local File) | D1 (Distributed SQLite) |
| **Storage** | Local Disk (`/uploads`) | R2 (Object Storage) |
| **Auth** | Middleware + Viem | Middleware + Viem (Edge Compatible) |

## 2. Prerequisites

*   Cloudflare Account
*   Node.js & npm
*   Wrangler CLI (`npm install -g wrangler`)

## 3. Setup Steps

### Step A: Initialize Infrastructure

1.  **Create D1 Database**
    ```bash
    wrangler d1 create chronicle-db
    ```
    *Copy the `database_id` output.*

2.  **Create R2 Bucket**
    ```bash
    wrangler r2 bucket create chronicle-assets
    ```

### Step B: Configure Worker

1.  Navigate to the worker directory:
    ```bash
    cd apps/chronicle-worker
    ```

2.  Edit `wrangler.toml` with your IDs:
    ```toml
    name = "chronicle-worker"
    main = "src/index.ts"
    compatibility_date = "2023-12-01"

    [vars]
    CHAIN_ID = "8453"
    BASE_RPC_URL = "https://mainnet.base.org"
    ZORA_CREATOR_ADDRESS = "0x..."
    ADMIN_WALLET_ADDRESS = "0x..."

    [[d1_databases]]
    binding = "DB"
    database_name = "chronicle-db"
    database_id = "PASTE_YOUR_D1_ID_HERE"

    [[r2_buckets]]
    binding = "BUCKET"
    bucket_name = "chronicle-assets"
    ```

3.  **Set Secrets** (Do not commit these!):
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
    wrangler d1 execute chronicle-db --file=../chronicle-server/data/schema_d1.sql
    ```

### Step D: Deploy Worker

1.  Install dependencies:
    ```bash
    npm install
    ```

2.  Deploy to Cloudflare:
    ```bash
    npm run deploy
    ```
    *Note the URL output (e.g., `https://chronicle-worker.yourname.workers.dev`).*

## 4. Frontend Update

1.  Go to `apps/chronicle-ui`.
2.  Update `.env` (or Cloudflare Pages Environment Variables):
    ```bash
    VITE_CHRONICLE_API_URL=https://chronicle-worker.yourname.workers.dev
    ```
3.  Deploy Frontend to Cloudflare Pages:
    ```bash
    npm run build
    wrangler pages deploy dist --project-name chronicle-ui
    ```

## 5. Agent Update

1.  Update the root `.env` for the Python Agent:
    ```bash
    ZORA_SIDECAR_URL=https://chronicle-worker.yourname.workers.dev
    CHRONICLE_SECRET_KEY=your_secret_key
    ```

## 6. Migration Notes

*   **Existing Data**: Use `sqlite3` to export your local `chronicle.db` to SQL, then import into D1 if you want to keep history.
*   **Images**: Manually upload existing `public/uploads` to your R2 bucket using the Cloudflare Dashboard or `rclone`.
