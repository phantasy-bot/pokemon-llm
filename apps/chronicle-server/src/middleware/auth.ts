import { Request, Response, NextFunction } from 'express';
import { Address, verifyMessage } from 'viem';
import dotenv from 'dotenv';

dotenv.config();

const ADMIN_WALLET = process.env.ADMIN_WALLET_ADDRESS || process.env.ZORA_CREATOR_ADDRESS;
const CHRONICLE_SECRET_KEY = process.env.CHRONICLE_SECRET_KEY;

if (!ADMIN_WALLET) {
  console.warn("⚠️ SECURITY WARNING: ADMIN_WALLET_ADDRESS not set. Admin routes are unprotected!");
}

if (!CHRONICLE_SECRET_KEY) {
  console.warn("⚠️ AGENT WARNING: CHRONICLE_SECRET_KEY not set. Python agent will not be able to create drafts.");
}

export const authMiddleware = async (req: Request, res: Response, next: NextFunction) => {
  const apiKey = req.headers['x-api-key'] as string;
  
  // 1. API Key Auth (for Python Agent)
  if (apiKey && CHRONICLE_SECRET_KEY) {
    if (apiKey === CHRONICLE_SECRET_KEY) {
      return next();
    } else {
      return res.status(403).json({ error: "Invalid API key" });
    }
  }

  // 2. Wallet Signature Auth (for Admin UI)
  const walletAddress = req.headers['x-wallet-address'] as string;
  const signature = req.headers['x-signature'] as string;
  const timestamp = req.headers['x-timestamp'] as string;

  if (!walletAddress || !signature || !timestamp) {
    return res.status(401).json({ error: "Missing authentication headers" });
  }

  // Check if user claims to be admin
  if (!ADMIN_WALLET || walletAddress.toLowerCase() !== ADMIN_WALLET.toLowerCase()) {
    return res.status(403).json({ error: "Unauthorized wallet" });
  }

  // Prevent Replay Attacks (Timestamp check)
  const now = Date.now();
  const reqTime = parseInt(timestamp);
  // Allow 5 minute window
  if (isNaN(reqTime) || Math.abs(now - reqTime) > 300000) {
    return res.status(401).json({ error: "Request expired" });
  }

  try {
    // Verify Signature
    // Message format must match frontend exactly: "Chronicle Admin Action: [Timestamp]"
    const message = `Chronicle Admin Action: ${timestamp}`;
    
    const isValid = await verifyMessage({
      address: walletAddress as Address,
      message: message,
      signature: signature as `0x${string}`,
    });

    if (!isValid) {
      return res.status(403).json({ error: "Invalid signature" });
    }

    next();
  } catch (error) {
    console.error("Auth verification failed:", error);
    return res.status(403).json({ error: "Authentication failed" });
  }
};
