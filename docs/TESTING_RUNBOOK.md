# Chronicle System Testing Runbook

This runbook guides you through testing the full **Pokemon LLM -> Chronicle -> Zora/Twitter** pipeline.

## 🎯 Testing Goals

1.  **Infrastructure**: Verify Cloudflare Worker, UI, D1, and R2 are healthy.
2.  **Auth**: Confirm Cloudflare Zero Trust (Service Token) protects the Admin API.
3.  **Flow**: Ensure game events trigger drafts, drafts publish to Zora Testnet, and tweets go out.
4.  **Gating**: Verify exclusive content is locked/unlocked based on ownership.

---

## 🛠️ 1. Environment Setup

### 1.1 Base Sepolia (Testnet) Preparation
We use **Base Sepolia** for development to avoid spending real money.

1.  **Get a Wallet**: Use a test wallet (e.g., MetaMask or Rabby).
2.  **Network Config**:
    *   Network Name: Base Sepolia
    *   RPC URL: `https://sepolia.base.org`
    *   Chain ID: `84532`
    *   Currency Symbol: `ETH`
3.  **Get Testnet ETH**:
    *   Go to [coinbase.com/faucets/base-sepolia-faucet](https://www.coinbase.com/faucets/base-sepolia-faucet) or [superchain.faucet.com](https://superchain.faucet.com/).
    *   Send some ETH to your `ZORA_CREATOR_ADDRESS`.

### 1.2 Configuration Check
Ensure your `.env` is set for **Development**.

```bash
# Core
CHRONICLE_API_URL=https://chronicle-api-dev.llmletsplay.com
ZORA_SIDECAR_URL=https://chronicle-api-dev.llmletsplay.com

# Feature Flags
CHRONICLE_ENABLED=true
ZORA_POSTING_ENABLED=true
ZORA_GATING_ENABLED=true
TWITTER_ENABLED=true # Set to false if you want to skip Twitter for now

# Keys
CHRONICLE_SECRET_KEY=...
CF_ACCESS_CLIENT_ID=...
CF_ACCESS_CLIENT_SECRET=...
```

---

## 🔍 2. Component Health Checks

### 2.1 Backend API (Worker)
Visit: `https://chronicle-api-dev.llmletsplay.com/health`
*   **Expected**: `{"status": "ok"}`
*   **Note**: If you get a Cloudflare Access login screen, the domain is correctly protected. The Python agent uses the Service Token to bypass this.

### 2.2 Frontend (UI)
Visit: `https://chronicle-dev.llmletsplay.com`
*   **Expected**: The Chronicle UI loads. It might be empty if D1 is fresh.
*   **Action**: Connect your wallet (ensure it's on Base Sepolia).

---

## 🧪 3. End-to-End Test Scenarios

### Scenario A: Manual "Stream Start" (Twitter Only)
Test if the agent can post to Twitter/Discord without minting.

1.  **Trigger**:
    In `run.py` or via a test script, invoke:
    ```python
    from services.tweet_generator import get_tweet_generator
    await get_tweet_generator().generate_tweet("stream_start")
    ```
2.  **Verify**:
    *   Check Discord channel for approval request.
    *   Approve it.
    *   Check X (Twitter) for the post.

### Scenario B: The "Zora Drop" Flow
Test the full pipeline: Game -> Draft -> Mint -> Unlock.

#### 1. Trigger Achievement
We will simulate a "Badge Earned" event.

*   **Option 1 (Code)**: Run `scripts/test_chronicle_integration.py`
    *   This script manually calls `chronicle_client.create_draft()`.
    *   *Make sure to update the script to use a dummy image path.*

*   **Option 2 (Agent)**:
    *   Start the agent: `python run.py`
    *   Manually insert an achievement into the tracker:
        ```python
        tracker.track_achievement("badge_boulder", {"leader": "Brock"})
        ```

#### 2. Verify Draft Creation
*   Go to **Chronicle Admin UI** (at `/admin` if implemented, or check logs).
*   The agent logs should say: `✅ Successfully sent draft to Chronicle`.
*   Check `https://chronicle-api-dev.llmletsplay.com/api/drafts` (requires Auth headers or login).

#### 3. Publish & Mint (On Chain)
*   The `ZoraPosterService` should automatically pick up the draft if `ZORA_AUTO_POST=true`.
*   **Log check**: Look for `Minting coin on Chain ID 84532...`
*   **Explorer check**: Go to [sepolia.basescan.org](https://sepolia.basescan.org/) and search your `ZORA_CREATOR_ADDRESS`.
    *   You should see a `Contract Creation` or `Mint` transaction.

#### 4. Verify in UI
*   Refresh `https://chronicle-dev.llmletsplay.com`.
*   The new drop should appear in the feed.
*   Status should be `published`.

#### 5. Test Token Gating
*   **Switch Wallet**: Use a different wallet (Account 2) that **does not** own the coin.
*   **Click Unlock**: Should say "You do not own this coin".
*   **Buy Coin**: Use the "Mint/Collect" button (if integrated with Zora Embed or standard mint link).
    *   *Alternative*: Manually send 0.0001 ETH to the coin contract if it's a standard Zora 1155/ERC20.
*   **Click Unlock**: Should now reveal the exclusive content (image/save file).

---

## 🐛 Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| **403 Forbidden on API** | Missing/Wrong Service Token | Check `CF_ACCESS_CLIENT_ID` in `.env`. |
| **500 Error on Mint** | RPC Fail / No Gas | Check `BASE_RPC_URL` (Sepolia) and wallet balance. |
| **Image not loading** | R2 Bucket permissions | Ensure Worker has `R2Bucket` binding correctly set. |
| **"Signature Expired"** | System clock drift | Sync your computer's clock. |

---

## 🧹 Cleanup
After testing:
1.  Clear the `llmletsplay-chronicle-db-dev` D1 database if you want a fresh start.
    ```bash
    npx wrangler d1 execute llmletsplay-chronicle-db-dev --command "DELETE FROM drops" --remote
    ```
