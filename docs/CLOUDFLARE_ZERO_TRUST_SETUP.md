# Setting Up Cloudflare Access for Chronicle

## Naming Convention

This project uses the `llmletsplay-chronicle-` prefix for all Cloudflare resources to distinguish them from other projects that may also use the "chronicle" namespace (which serves as a generic blogging/content system).

| Resource Type | Name |
|---------------|------|
| Worker (Prod) | `llmletsplay-chronicle-worker` |
| Worker (Dev)  | `llmletsplay-chronicle-worker-dev` |
| Worker (UI)   | `llmletsplay-chronicle-ui` |
| Worker (UI Dev)| `llmletsplay-chronicle-ui-dev` |
| D1 Database   | `llmletsplay-chronicle-db` |
| R2 Bucket     | `llmletsplay-chronicle-assets` |

Worker URLs follow the pattern: `https://<worker-name>.phantasybot.workers.dev`

---

To secure your Worker while allowing public access to the feed, you must create **Separate Applications** in Cloudflare Access for specific paths. Cloudflare applies policies based on the most specific path match.

## Strategy: "Public Read, Private Write"

We will create **3 Applications** for the same domain (`llmletsplay-chronicle-worker.phantasybot.workers.dev`):

1.  **Public Feed** (Path: `/api/feed`) -> Allows Everyone.
2.  **Public Uploads** (Path: `/uploads`) -> Allows Everyone.
3.  **Admin/Agent** (Path: `/`) -> Catch-all, protected by Login & Service Token.

---

## Step 1: Create Service Token (For Python Agent)

1.  Go to **Zero Trust Dashboard** > **Access** > **Service Auth** > **Service Tokens**.
2.  Click **Create Service Token**.
3.  Name: `chronicle-agent`.
4.  **Copy `Client ID` and `Client Secret`**.
5.  Add to your local `.env`:
    ```bash
    CF_ACCESS_CLIENT_ID=...
    CF_ACCESS_CLIENT_SECRET=...
    ```

---

## Step 2: Create Public Applications

You need to create separate applications for **Production** and **Development**.

### A. Production Environment (`llmletsplay-chronicle-worker.phantasybot.workers.dev` or `chronicle-api.llmletsplay.com`)

1.  **Public Feed:**
    *   **Domain:** `chronicle-api.llmletsplay.com`
    *   **Path:** `/api/feed`
    *   **Action:** Bypass (Everyone)

2.  **Public Uploads:**
    *   **Domain:** `chronicle-api.llmletsplay.com`
    *   **Path:** `/uploads`
    *   **Action:** Bypass (Everyone)

3.  **Admin/Agent (Root):**
    *   **Domain:** `chronicle-api.llmletsplay.com`
    *   **Path:** (Root)
    *   **Policy 1:** Agent Write (Service Auth -> `chronicle-agent`)
    *   **Policy 2:** Admin Access (Allow -> Your Email)

---

### B. Development Environment (`llmletsplay-chronicle-worker-dev.phantasybot.workers.dev` or `chronicle-api-dev.llmletsplay.com`)

Repeat the same 3 applications but for the DEV domain.

1.  **Dev Feed:** `chronicle-api-dev.llmletsplay.com/api/feed` -> Bypass
2.  **Dev Uploads:** `chronicle-api-dev.llmletsplay.com/uploads` -> Bypass
3.  **Dev Admin:** `chronicle-api-dev.llmletsplay.com` -> Protected (Service Token + Email)

---

## Step 3: Configure Custom Domains

To use `chronicle-api.llmletsplay.com`:

1.  Go to your **Worker** in Cloudflare Dashboard (`llmletsplay-chronicle-worker`).
2.  Go to **Settings** > **Triggers** > **Custom Domains**.
3.  Add `chronicle-api.llmletsplay.com`.
4.  Do the same for the **Dev Worker** (`llmletsplay-chronicle-worker-dev`) -> `chronicle-api-dev.llmletsplay.com`.

Then ensure your Zero Trust Applications match these custom domains.


---

## Summary of Logic

*   Request to `.../api/feed` -> Matches **App 1** -> **Bypass** (Public).
*   Request to `.../uploads/xyz.png` -> Matches **App 2** -> **Bypass** (Public).
*   Request to `.../api/drop` -> No match on 1/2 -> Matches **App 3** (Root) -> **Checks Auth** (Requires Token or Login).

This ensures your site works for users, but your database is safe from hackers.
