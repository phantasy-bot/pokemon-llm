import express from "express";
import cors from "cors";
import multer from "multer";
import dotenv from "dotenv";
import fs from "fs-extra";
import path from "path";
import { v4 as uuidv4 } from "uuid";
import { Address, Hex } from "viem";
import { uploadMetadata } from "./uploader";
import { createNewCoin } from "./coin-creator";
import { insertDrop, getAllDrops, getDropByAddress } from "./db";
import { checkOwnership, verifySignature } from "./gating";

dotenv.config();

const app = express();
const port = process.env.PORT || 3001;
const SECURE_STORAGE_PATH = process.env.SECURE_STORAGE_PATH || 'secure_storage';

// Ensure storage exists
fs.ensureDirSync(SECURE_STORAGE_PATH);

app.use(cors());
app.use(express.json());

const upload = multer({ dest: "uploads/" });

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

// GET /api/feed - Public feed of drops
app.get("/api/feed", (req, res) => {
  try {
    const drops = getAllDrops.all();
    res.json({ drops });
  } catch (e) {
    res.status(500).json({ error: "Failed to fetch feed" });
  }
});

// POST /api/drop - Create a new drop (Mint + Secure Storage)
// Expects 'image' (public) and optionally 'exclusive' (private) files
app.post("/api/drop", upload.fields([{ name: 'image', maxCount: 1 }, { name: 'exclusive', maxCount: 1 }]), async (req, res) => {
  try {
    const { name, symbol, description, attributes } = req.body;
    const files = req.files as { [fieldname: string]: Express.Multer.File[] };
    const publicFile = files['image']?.[0];
    const exclusiveFile = files['exclusive']?.[0];

    if (!publicFile || !name || !symbol) {
      return res.status(400).json({ error: "Missing required fields" });
    }

    // 1. Zora Minting Flow
    const privateKey = process.env.ZORA_PRIVATE_KEY as Hex;
    const creatorAddress = process.env.ZORA_CREATOR_ADDRESS as Address;

    let parsedAttributes = [];
    if (attributes) {
      try {
        parsedAttributes = JSON.parse(attributes);
      } catch (e) { /* ignore */ }
    }

    const metadataParams = await uploadMetadata(
      creatorAddress,
      name,
      symbol,
      description || "",
      publicFile.path,
      parsedAttributes
    );

    const result = await createNewCoin(
      privateKey,
      creatorAddress,
      name,
      symbol,
      metadataParams.metadata.uri
    );

    const coinAddress = result.address;
    
    // 2. Handle Exclusive Content
    let exclusiveContentPath = null;
    if (exclusiveFile) {
      const ext = path.extname(exclusiveFile.originalname);
      const filename = `${uuidv4()}${ext}`;
      exclusiveContentPath = path.join(SECURE_STORAGE_PATH, filename);
      await fs.move(exclusiveFile.path, exclusiveContentPath);
    }

    // 3. Save to DB
    insertDrop.run({
      id: uuidv4(),
      coinAddress,
      name,
      symbol,
      description,
      publicImageUrl: metadataParams.metadata.uri, // Use IPFS URI or gateway URL
      metadataUri: metadataParams.metadata.uri,
      exclusiveContentPath
    });

    // Cleanup public file
    await fs.remove(publicFile.path);

    res.json({ success: true, coinAddress });

  } catch (error: any) {
    console.error("Drop creation failed:", error);
    res.status(500).json({ error: error.message });
  }
});

// GET /api/content/:coinAddress - Access exclusive content
app.get("/api/content/:coinAddress", async (req, res) => {
  const { coinAddress } = req.params;
  const { walletAddress, signature, timestamp } = req.query;

  if (!walletAddress || !signature) {
    return res.status(401).json({ error: "Missing auth params" });
  }

  try {
    // 1. Get Drop info
    const drop = getDropByAddress.get(coinAddress) as any;
    if (!drop || !drop.exclusiveContentPath) {
      return res.status(404).json({ error: "No content found for this drop" });
    }

    // 2. Verify Signature
    // Message format: "Authenticate Chronicle Access: [CoinAddress] [Timestamp]"
    // Timestamp check prevents replay attacks (allow 5 min window)
    const now = Date.now();
    const reqTime = parseInt(timestamp as string);
    if (Math.abs(now - reqTime) > 300000) { // 5 mins
        return res.status(401).json({ error: "Signature expired" });
    }

    const message = `Authenticate Chronicle Access: ${coinAddress} ${timestamp}`;
    const isValid = await verifySignature(message, signature as `0x${string}`, walletAddress as Address);
    
    if (!isValid) {
      return res.status(403).json({ error: "Invalid signature" });
    }

    // 3. Check Ownership
    const isHolder = await checkOwnership(walletAddress as Address, coinAddress as Address);
    if (!isHolder) {
      return res.status(403).json({ error: "You do not own this coin" });
    }

    // 4. Serve File
    res.download(drop.exclusiveContentPath);

  } catch (e: any) {
    console.error("Content access error:", e);
    res.status(500).json({ error: "Server error" });
  }
});

app.listen(port, () => {
  console.log(`Chronicle server running on port ${port}`);
});
