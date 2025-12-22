import { Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import path from 'path';
import fs from 'fs-extra';
import { Address, Hex } from 'viem';
import { TwitterApi } from 'twitter-api-v2';
import { insertDrop, getAllDrops, getDrafts, getDrop, updateDrop } from '../db';
import { uploadMetadata } from '../uploader';
import { createNewCoin } from '../coin-creator';

const SECURE_STORAGE_PATH = process.env.SECURE_STORAGE_PATH || 'secure_storage';
const PUBLIC_UPLOADS_PATH = 'public/uploads';

// Helper to ensure directories exist
fs.ensureDirSync(SECURE_STORAGE_PATH);
fs.ensureDirSync(PUBLIC_UPLOADS_PATH);

export const DropController = {
  // Get Public Feed
  getFeed: (req: Request, res: Response) => {
    try {
      const drops = getAllDrops.all().map((d: any) => ({
        ...d,
        images: d.images ? JSON.parse(d.images) : []
      }));
      res.json({ drops });
    } catch (e) {
      res.status(500).json({ error: "Failed to fetch feed" });
    }
  },

  // Get Drafts (Admin)
  getDrafts: (req: Request, res: Response) => {
    try {
      const drafts = getDrafts.all().map((d: any) => ({
        ...d,
        images: d.images ? JSON.parse(d.images) : []
      }));
      res.json({ drafts });
    } catch (e) {
      res.status(500).json({ error: "Failed to fetch drafts" });
    }
  },

  // Create Drop or Draft
  createDrop: async (req: Request, res: Response) => {
    try {
      const { name, symbol, description, attributes, status = 'published' } = req.body;
      const files = req.files as { [fieldname: string]: Express.Multer.File[] };
      const publicFile = files['image']?.[0];
      const galleryFiles = files['gallery'] || [];
      const exclusiveFile = files['exclusive']?.[0];

      if (!name || !symbol) {
        return res.status(400).json({ error: "Missing required fields" });
      }

      // Handle Images
      let publicImageUrl = '';
      let images: string[] = [];
      
      // Process primary image
      if (publicFile) {
          const ext = path.extname(publicFile.originalname);
          const filename = `${uuidv4()}${ext}`;
          const localPath = path.join(PUBLIC_UPLOADS_PATH, filename);
          await fs.move(publicFile.path, localPath);
          publicImageUrl = `/uploads/${filename}`;
          images.push(publicImageUrl);
      }

      // Process gallery images
      for (const file of galleryFiles) {
          const ext = path.extname(file.originalname);
          const filename = `${uuidv4()}${ext}`;
          const localPath = path.join(PUBLIC_UPLOADS_PATH, filename);
          await fs.move(file.path, localPath);
          images.push(`/uploads/${filename}`);
      }

      // Handle Exclusive Content
      let exclusiveContentPath = null;
      if (exclusiveFile) {
        const ext = path.extname(exclusiveFile.originalname);
        const filename = `${uuidv4()}${ext}`;
        exclusiveContentPath = path.join(SECURE_STORAGE_PATH, filename);
        await fs.move(exclusiveFile.path, exclusiveContentPath);
      }

      const dropId = uuidv4();

      if (status === 'draft') {
          insertDrop.run({
              id: dropId,
              coinAddress: `DRAFT-${dropId}`,
              name,
              symbol,
              description,
              publicImageUrl,
              metadataUri: '',
              exclusiveContentPath,
              marketCap: '0',
              volume24h: '0',
              priceChange24h: 0,
              status: 'draft',
              images: JSON.stringify(images)
          });
          
          return res.json({ success: true, id: dropId, status: 'draft' });
      }

      // PUBLISH FLOW
      if (!publicImageUrl) {
           return res.status(400).json({ error: "Image required for publishing" });
      }

      const privateKey = process.env.ZORA_PRIVATE_KEY as Hex;
      const creatorAddress = process.env.ZORA_CREATOR_ADDRESS as Address;

      let parsedAttributes = [];
      if (attributes) {
        try {
          parsedAttributes = typeof attributes === 'string' ? JSON.parse(attributes) : attributes;
        } catch (e) { /* ignore */ }
      }

      // Local path for upload
      const primaryLocalPath = path.join(PUBLIC_UPLOADS_PATH, path.basename(publicImageUrl));

      const metadataParams = await uploadMetadata(
        creatorAddress,
        name,
        symbol,
        description || "",
        primaryLocalPath,
        parsedAttributes
      );

      const result = await createNewCoin(
        privateKey,
        creatorAddress,
        name,
        symbol,
        metadataParams.metadata.uri
      );

      insertDrop.run({
        id: dropId,
        coinAddress: result.address,
        name,
        symbol,
        description,
        publicImageUrl: metadataParams.metadata.uri,
        metadataUri: metadataParams.metadata.uri,
        exclusiveContentPath,
        marketCap: '0',
        volume24h: '0',
        priceChange24h: 0,
        status: 'published',
        images: JSON.stringify(images)
      });

      res.json({ success: true, coinAddress: result.address, id: dropId });

    } catch (error: any) {
      console.error("Drop creation failed:", error);
      res.status(500).json({ error: error.message });
    }
  },

  // Update Draft
  updateDraft: async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const { name, description, status } = req.body;
        const files = req.files as { [fieldname: string]: Express.Multer.File[] };
        const publicFile = files['image']?.[0];
        const galleryFiles = files['gallery'] || [];

        const drop = getDrop.get(id) as any;
        if (!drop) return res.status(404).json({ error: "Drop not found" });
        if (drop.status === 'published') return res.status(400).json({ error: "Cannot edit published drop" });

        let currentImages = drop.images ? JSON.parse(drop.images) : [];
        let publicImageUrl = drop.publicImageUrl;

        // If replacing primary image
        if (publicFile) {
             const ext = path.extname(publicFile.originalname);
             const filename = `${uuidv4()}${ext}`;
             const localPath = path.join(PUBLIC_UPLOADS_PATH, filename);
             await fs.move(publicFile.path, localPath);
             publicImageUrl = `/uploads/${filename}`;
             
             // Replace first image if exists, or push
             if (currentImages.length > 0) {
                 currentImages[0] = publicImageUrl;
             } else {
                 currentImages.push(publicImageUrl);
             }
        }

        // Add new gallery images
        for (const file of galleryFiles) {
            const ext = path.extname(file.originalname);
            const filename = `${uuidv4()}${ext}`;
            const localPath = path.join(PUBLIC_UPLOADS_PATH, filename);
            await fs.move(file.path, localPath);
            currentImages.push(`/uploads/${filename}`);
        }

        updateDrop.run({
            id,
            name: name || drop.name,
            description: description || drop.description,
            publicImageUrl,
            metadataUri: drop.metadataUri,
            status: status || drop.status,
            coinAddress: drop.coinAddress,
            images: JSON.stringify(currentImages)
        });

        res.json({ success: true });

    } catch (e: any) {
        console.error("Update failed:", e);
        res.status(500).json({ error: e.message });
    }
  },

  // Publish Draft
  publishDraft: async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const drop = getDrop.get(id) as any;
        
        if (!drop) return res.status(404).json({ error: "Drop not found" });
        if (drop.status === 'published') return res.status(400).json({ error: "Already published" });

        const privateKey = process.env.ZORA_PRIVATE_KEY as Hex;
        const creatorAddress = process.env.ZORA_CREATOR_ADDRESS as Address;

        // Determine local path from publicImageUrl
        const localFileName = path.basename(drop.publicImageUrl);
        const localPath = path.join(PUBLIC_UPLOADS_PATH, localFileName);

        if (!fs.existsSync(localPath)) {
            return res.status(500).json({ error: "Image file missing locally" });
        }

        // Upload to IPFS
        const metadataParams = await uploadMetadata(
          creatorAddress,
          drop.name,
          drop.symbol,
          drop.description || "",
          localPath, 
          [] 
        );

        // Mint
        const result = await createNewCoin(
          privateKey,
          creatorAddress,
          drop.name,
          drop.symbol,
          metadataParams.metadata.uri
        );

        // Update DB
        updateDrop.run({
            id,
            name: drop.name,
            description: drop.description,
            publicImageUrl: metadataParams.metadata.uri,
            metadataUri: metadataParams.metadata.uri,
            status: 'published',
            coinAddress: result.address,
            images: drop.images // Keep existing image list
        });

        res.json({ success: true, coinAddress: result.address });

    } catch (e: any) {
        console.error("Publish failed:", e);
        res.status(500).json({ error: e.message });
    }
  },

  // Tweet Drop
  tweetDrop: async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const drop = getDrop.get(id) as any;
        if (!drop) return res.status(404).json({ error: "Drop not found" });

        const appKey = process.env.TWITTER_API_KEY;
        const appSecret = process.env.TWITTER_API_SECRET;
        const accessToken = process.env.TWITTER_ACCESS_TOKEN;
        const accessSecret = process.env.TWITTER_ACCESS_TOKEN_SECRET;

        if (!appKey || !appSecret || !accessToken || !accessSecret) {
             return res.status(500).json({ error: "Twitter credentials not configured" });
        }

        const client = new TwitterApi({
            appKey,
            appSecret,
            accessToken,
            accessSecret,
        });

        const images = drop.images ? JSON.parse(drop.images) : [drop.publicImageUrl];
        const mediaIds = [];

        // Upload images
        for (let imgUrl of images.slice(0, 4)) {
            // Check if it's a local path or URL
            let filePath;
            if (imgUrl.startsWith('/uploads/')) {
                filePath = path.join(PUBLIC_UPLOADS_PATH, path.basename(imgUrl));
            } else if (imgUrl.startsWith('http')) {
                continue; 
            } else {
                filePath = imgUrl; 
            }

            if (filePath && fs.existsSync(filePath)) {
                 const mediaId = await client.v1.uploadMedia(filePath);
                 mediaIds.push(mediaId);
            }
        }

        const tweetText = `${drop.name}\n\n${drop.description}\n\n#PokemonRed #LassPlaysPokemon`;
        
        await client.v2.tweet({
            text: tweetText,
            media: mediaIds.length > 0 ? { media_ids: mediaIds as [string] | [string, string] | [string, string, string] | [string, string, string, string] } : undefined
        });

        res.json({ success: true });

    } catch (e: any) {
        console.error("Tweet failed:", e);
        res.status(500).json({ error: e.message });
    }
  }
};
