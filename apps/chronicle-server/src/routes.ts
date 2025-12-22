import express from 'express';
import multer from 'multer';
import { DropController } from './controllers/drop.controller';
import { checkOwnership, verifySignature } from './gating';
import { getDropByAddress } from './db';
import { Address } from 'viem';
import { authMiddleware } from './middleware/auth';
import { v4 as uuidv4 } from 'uuid';
import path from 'path';

// Secure File Upload Configuration
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${uuidv4()}${ext}`);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB Limit
  },
  fileFilter: (req, file, cb) => {
    // Allow only images
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only image files are allowed!'));
    }
  }
});

const router = express.Router();

// Public Feed
router.get("/feed", DropController.getFeed);

// Admin Routes - PROTECTED
router.get("/drafts", authMiddleware, DropController.getDrafts);
router.post("/drop", authMiddleware, upload.fields([{ name: 'image', maxCount: 1 }, { name: 'gallery', maxCount: 4 }, { name: 'exclusive', maxCount: 1 }]), DropController.createDrop);
router.put("/drop/:id", authMiddleware, upload.fields([{ name: 'image', maxCount: 1 }, { name: 'gallery', maxCount: 4 }]), DropController.updateDraft);
router.post("/drop/:id/publish", authMiddleware, DropController.publishDraft);
router.post("/drop/:id/tweet", authMiddleware, DropController.tweetDrop);

// Gated Content Route (Kept inline as it's specific to serving files)
router.get("/content/:coinAddress", async (req, res) => {
  const { coinAddress } = req.params;
  const { walletAddress, signature, timestamp } = req.query;

  if (!walletAddress || !signature) {
    return res.status(401).json({ error: "Missing auth params" });
  }

  try {
    const drop = getDropByAddress.get(coinAddress) as any;
    if (!drop || !drop.exclusiveContentPath) {
      return res.status(404).json({ error: "No content found for this drop" });
    }

    const now = Date.now();
    const reqTime = parseInt(timestamp as string);
    if (Math.abs(now - reqTime) > 300000) { 
        return res.status(401).json({ error: "Signature expired" });
    }

    const message = `Authenticate Chronicle Access: ${coinAddress} ${timestamp}`;
    const isValid = await verifySignature(message, signature as `0x${string}`, walletAddress as Address);
    
    if (!isValid) {
      return res.status(403).json({ error: "Invalid signature" });
    }

    const isHolder = await checkOwnership(walletAddress as Address, coinAddress as Address);
    if (!isHolder) {
      return res.status(403).json({ error: "You do not own this coin" });
    }

    res.download(drop.exclusiveContentPath);

  } catch (e: any) {
    console.error("Content access error:", e);
    res.status(500).json({ error: "Server error" });
  }
});

export default router;
