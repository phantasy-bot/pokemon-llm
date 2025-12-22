import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { Database } from './db';
import { Storage } from './storage';
import { authMiddleware } from './auth';
import { createMetadataBuilder, createZoraUploaderForCreator } from "@zoralabs/coins-sdk";
import { createWalletClient, createPublicClient, http } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import { TwitterApi } from 'twitter-api-v2';

type Bindings = {
  DB: D1Database;
  BUCKET: R2Bucket;
  ZORA_CREATOR_ADDRESS: string;
  ADMIN_WALLET_ADDRESS: string;
  CHRONICLE_SECRET_KEY: string;
  CHAIN_ID: string;
  BASE_RPC_URL: string;
  TWITTER_API_KEY: string;
  TWITTER_API_SECRET: string;
  TWITTER_ACCESS_TOKEN: string;
  TWITTER_ACCESS_TOKEN_SECRET: string;
  ZORA_PRIVATE_KEY: string;
}

const app = new Hono<{ Bindings: Bindings }>();

app.use('/*', cors());

app.get('/health', (c) => c.json({ status: 'ok' }));

// Helper factories
const getDB = (c: any) => new Database(c.env.DB);
const getStorage = (c: any) => new Storage(c.env.BUCKET);

// Routes
app.get('/api/feed', async (c) => {
  try {
    const db = getDB(c);
    const drops = await db.getAllDrops();
    // Parse images JSON
    const parsed = drops.map((d: any) => ({
      ...d,
      images: d.images ? JSON.parse(d.images) : []
    }));
    return c.json({ drops: parsed });
  } catch (e: any) {
    return c.json({ error: e.message }, 500);
  }
});

app.get('/api/drafts', authMiddleware, async (c) => {
  try {
    const db = getDB(c);
    const drafts = await db.getDrafts();
    const parsed = drafts.map((d: any) => ({
      ...d,
      images: d.images ? JSON.parse(d.images) : []
    }));
    return c.json({ drafts: parsed });
  } catch (e: any) {
    return c.json({ error: e.message }, 500);
  }
});

app.post('/api/drop', authMiddleware, async (c) => {
  try {
    const body = await c.req.parseBody();
    const db = getDB(c);
    const storage = getStorage(c);

    const name = body['name'] as string;
    const symbol = body['symbol'] as string;
    const description = body['description'] as string;
    const status = (body['status'] as string) || 'published';
    const attributes = body['attributes'];

    if (!name || !symbol) {
      return c.json({ error: "Missing required fields" }, 400);
    }

    const dropId = crypto.randomUUID();
    let publicImageUrl = '';
    let images: string[] = [];

    // Handle Image
    const imageFile = body['image'];
    if (imageFile instanceof File) {
      const ext = imageFile.name.split('.').pop();
      const filename = `${crypto.randomUUID()}.${ext}`;
      await storage.upload(filename, imageFile);
      // Construct URL (Assuming Worker handles /uploads/ proxy or public bucket)
      // For now, store key, serve via /uploads/ endpoint
      publicImageUrl = `/uploads/${filename}`;
      images.push(publicImageUrl);
    }

    // Handle Gallery
    // Note: Hono parseBody might return array for 'gallery' if multiple files
    // BUT usually it handles multiple fields with same name as array.
    // If not, we check.
    const gallery = body['gallery'];
    const galleryFiles = Array.isArray(gallery) ? gallery : (gallery ? [gallery] : []);
    
    for (const file of galleryFiles) {
      if (file instanceof File) {
        const ext = file.name.split('.').pop();
        const filename = `${crypto.randomUUID()}.${ext}`;
        await storage.upload(filename, file);
        images.push(`/uploads/${filename}`);
      }
    }

    // Exclusive
    let exclusiveContentPath = null;
    const exclusiveFile = body['exclusive'];
    if (exclusiveFile instanceof File) {
      const ext = exclusiveFile.name.split('.').pop();
      const filename = `${crypto.randomUUID()}.${ext}`;
      exclusiveContentPath = filename; // Store key directly
      await storage.upload(filename, exclusiveFile);
    }

    if (status === 'draft') {
      await db.insertDrop({
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
      return c.json({ success: true, id: dropId, status: 'draft' });
    }

    // PUBLISH FLOW (Immediate)
    // IMPORTANT: Minting takes time. Worker might timeout.
    // We attempt it, but if it fails, user should use 'publish' endpoint later.
    // Ideally we return early, but we need the address.
    // For now, we block.
    
    // ... Minting logic would go here ...
    // Since we don't have 'fs', we need to adapt uploader.
    // For this MVP scaffold, I will stub the actual minting logic with a TODO 
    // because porting the SDK to run without FS requires more care.
    // I'll return an error if trying to publish immediately for now, enforcing Draft flow.
    
    return c.json({ error: "Direct publishing not supported on Edge yet. Please save as Draft first." }, 400);

  } catch (e: any) {
    return c.json({ error: e.message }, 500);
  }
});

// Proxy for uploads
app.get('/uploads/:key', async (c) => {
  const key = c.req.param('key');
  const storage = getStorage(c);
  const object = await storage.get(key);
  
  if (!object) return c.json({ error: "Not found" }, 404);
  
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('etag', object.httpEtag);
  
  return new Response(object.body, { headers });
});

export default app;
