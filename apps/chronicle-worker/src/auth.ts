import { Context, Next } from 'hono';
import { verifyMessage } from 'viem';

export const authMiddleware = async (c: Context, next: Next) => {
  const apiKey = c.req.header('x-api-key');
  const secretKey = c.env.CHRONICLE_SECRET_KEY;

  // 1. API Key Auth
  if (apiKey && secretKey && apiKey === secretKey) {
    return next();
  }

  // 2. Wallet Signature Auth
  const walletAddress = c.req.header('x-wallet-address');
  const signature = c.req.header('x-signature');
  const timestamp = c.req.header('x-timestamp');

  if (!walletAddress || !signature || !timestamp) {
    return c.json({ error: "Missing authentication headers" }, 401);
  }

  const adminWallet = c.env.ADMIN_WALLET_ADDRESS || c.env.ZORA_CREATOR_ADDRESS;
  if (!adminWallet || walletAddress.toLowerCase() !== adminWallet.toLowerCase()) {
    return c.json({ error: "Unauthorized wallet" }, 403);
  }

  // Timestamp check
  const now = Date.now();
  const reqTime = parseInt(timestamp);
  if (isNaN(reqTime) || Math.abs(now - reqTime) > 300000) {
    return c.json({ error: "Request expired" }, 401);
  }

  try {
    const message = `Chronicle Admin Action: ${timestamp}`;
    const isValid = await verifyMessage({
      address: walletAddress as `0x${string}`,
      message: message,
      signature: signature as `0x${string}`,
    });

    if (!isValid) {
      return c.json({ error: "Invalid signature" }, 403);
    }

    await next();
  } catch (error) {
    console.error("Auth failed:", error);
    return c.json({ error: "Authentication failed" }, 403);
  }
};
