import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { Database } from './db';
import { Storage } from './storage';
import { authMiddleware } from './auth';
import { createMetadataBuilder, createZoraUploaderForCreator, createCoin, CreateConstants } from "@zoralabs/coins-sdk";
import { createWalletClient, createPublicClient, http, Address, Hex, toHex } from "viem";
import { base, baseSepolia } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import { TwitterApi } from 'twitter-api-v2';
import { checkOwnership } from './gating';

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

// --- HELPER FUNCTIONS FOR WEB3 ---

async function mintCoin(c: any, drop: any) {
    const chainId = parseInt(c.env.CHAIN_ID || "8453");
    const chain = chainId === 84532 ? baseSepolia : base;
    const account = privateKeyToAccount(c.env.ZORA_PRIVATE_KEY as Hex);
    const creatorAddress = c.env.ZORA_CREATOR_ADDRESS as Address;
    
    // We need to fetch the image from R2 to pass to SDK
    // SDK expects a File object usually. We can construct one.
    const storage = getStorage(c);
    const imageKey = drop.publicImageUrl.split('/').pop();
    const imageObject = await storage.get(imageKey);
    
    if (!imageObject) throw new Error("Image not found in storage");
    
    // Convert ReadableStream to ArrayBuffer -> Uint8Array -> File
    const arrayBuffer = await imageObject.arrayBuffer();
    const imageFile = new File([arrayBuffer], "image.png", { type: "image/png" });

    // 1. Upload Metadata (IPFS)
    // We use the SDK which handles uploads via Pinata/Zora API usually. 
    // It requires a signer/uploader.
    const uploader = createZoraUploaderForCreator(creatorAddress);
    
    const builder = createMetadataBuilder()
        .withName(drop.name)
        .withSymbol(drop.symbol)
        .withDescription(drop.description || "")
        .withImage(imageFile);
    
    // TODO: attributes
    
    const { createMetadataParameters } = await builder.upload(uploader);
    const metadataUri = createMetadataParameters.metadata.uri;

    // 2. Mint Coin
    const transport = c.env.BASE_RPC_URL ? http(c.env.BASE_RPC_URL) : http();
    const publicClient = createPublicClient({ chain, transport });
    const walletClient = createWalletClient({ account, chain, transport });

    const result = await createCoin({
        publicClient,
        walletClient,
        call: {
            creator: creatorAddress,
            name: drop.name,
            symbol: drop.symbol,
            metadata: { type: "RAW_URI", uri: metadataUri },
            currency: CreateConstants.ContentCoinCurrencies.ZORA,
            chainId: chain.id,
            startingMarketCap: CreateConstants.StartingMarketCaps.LOW
        }
    });

    return { coinAddress: result.address, metadataUri };
}

// --- ROUTES ---

app.get('/api/feed', async (c) => {
  try {
    const db = getDB(c);
    const drops = await db.getAllDrops();
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
    
    // attributes handling if needed

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
      publicImageUrl = `/uploads/${filename}`;
      images.push(publicImageUrl);
    }

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

    let exclusiveContentPath = null;
    const exclusiveFile = body['exclusive'];
    if (exclusiveFile instanceof File) {
      const ext = exclusiveFile.name.split('.').pop();
      const filename = `${crypto.randomUUID()}.${ext}`;
      exclusiveContentPath = filename; 
      await storage.upload(filename, exclusiveFile);
    }

    // Always create as DRAFT first if status is 'draft' OR if we want to enforce it.
    // Given the complexity of minting on Edge, enforcing draft is safer.
    
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
        status: status === 'published' ? 'draft' : status, // Force draft if attempted publish directly? 
        // Actually, if status is 'published', the user expects it live.
        // But minting is slow.
        // Let's create it as DRAFT, then background process? No background queues here easily.
        // We will just return it as a DRAFT and tell the agent/user "Saved as draft".
        // The Admin UI handles publishing.
        images: JSON.stringify(images)
    });
      
    return c.json({ success: true, id: dropId, status: 'draft' });

  } catch (e: any) {
    return c.json({ error: e.message }, 500);
  }
});

// Update Draft
app.put('/api/drop/:id', authMiddleware, async (c) => {
    try {
        const id = c.req.param('id');
        const body = await c.req.parseBody();
        const db = getDB(c);
        const storage = getStorage(c);

        const drop = await db.getDrop(id);
        if (!drop) return c.json({ error: "Drop not found" }, 404);
        if (drop.status === 'published') return c.json({ error: "Cannot edit published drop" }, 400);

        const name = (body['name'] as string) || drop.name;
        const description = (body['description'] as string) || drop.description;
        const status = (body['status'] as string) || drop.status;

        let currentImages = drop.images ? JSON.parse(drop.images) : [];
        let publicImageUrl = drop.publicImageUrl;

        const imageFile = body['image'];
        if (imageFile instanceof File) {
             const ext = imageFile.name.split('.').pop();
             const filename = `${crypto.randomUUID()}.${ext}`;
             await storage.upload(filename, imageFile);
             publicImageUrl = `/uploads/${filename}`;
             
             if (currentImages.length > 0) {
                 currentImages[0] = publicImageUrl;
             } else {
                 currentImages.push(publicImageUrl);
             }
        }

        const gallery = body['gallery'];
        const galleryFiles = Array.isArray(gallery) ? gallery : (gallery ? [gallery] : []);
        for (const file of galleryFiles) {
            if (file instanceof File) {
                const ext = file.name.split('.').pop();
                const filename = `${crypto.randomUUID()}.${ext}`;
                await storage.upload(filename, file);
                currentImages.push(`/uploads/${filename}`);
            }
        }

        await db.updateDrop({
            id,
            name,
            description,
            publicImageUrl,
            metadataUri: drop.metadataUri,
            status,
            coinAddress: drop.coinAddress,
            images: JSON.stringify(currentImages)
        });

        return c.json({ success: true });

    } catch (e: any) {
        return c.json({ error: e.message }, 500);
    }
});

// Publish Draft
app.post('/api/drop/:id/publish', authMiddleware, async (c) => {
    try {
        const id = c.req.param('id');
        const db = getDB(c);
        const drop = await db.getDrop(id);
        
        if (!drop) return c.json({ error: "Drop not found" }, 404);
        if (drop.status === 'published') return c.json({ error: "Already published" }, 400);

        // Perform Minting
        const { coinAddress, metadataUri } = await mintCoin(c, drop);

        await db.updateDrop({
            id,
            name: drop.name,
            description: drop.description,
            publicImageUrl: metadataUri, // Use IPFS URI now? Or keep local URL? 
            // Usually we keep local for speed, but metadataUri is definitive.
            // Let's update metadataUri but maybe keep publicImageUrl as local R2 for speed?
            // Actually, frontend handles ipfs:// urls? 
            // If frontend handles ipfs via gateway, we can switch.
            // For now, let's update metadataUri.
            metadataUri: metadataUri,
            status: 'published',
            coinAddress: coinAddress,
            images: drop.images
        });

        return c.json({ success: true, coinAddress });

    } catch (e: any) {
        return c.json({ error: e.message }, 500);
    }
});

// Tweet Drop
app.post('/api/drop/:id/tweet', authMiddleware, async (c) => {
    try {
        const id = c.req.param('id');
        const db = getDB(c);
        const storage = getStorage(c);
        const drop = await db.getDrop(id);
        if (!drop) return c.json({ error: "Drop not found" }, 404);

        if (!c.env.TWITTER_API_KEY) {
             return c.json({ error: "Twitter credentials not configured" }, 500);
        }

        const client = new TwitterApi({
            appKey: c.env.TWITTER_API_KEY,
            appSecret: c.env.TWITTER_API_SECRET,
            accessToken: c.env.TWITTER_ACCESS_TOKEN,
            accessSecret: c.env.TWITTER_ACCESS_TOKEN_SECRET,
        });

        const images = drop.images ? JSON.parse(drop.images) : [drop.publicImageUrl];
        const mediaIds = [];

        // Upload images
        for (let imgUrl of images.slice(0, 4)) {
            // Need to get file content from R2
            let key = imgUrl;
            if (imgUrl.startsWith('/uploads/')) {
                key = imgUrl.split('/').pop();
            } else if (imgUrl.startsWith('http')) {
                continue; 
            }

            const object = await storage.get(key);
            if (object) {
                 // Twitter API expects Buffer. Workers use ArrayBuffer.
                 const arrayBuffer = await object.arrayBuffer();
                 const buffer = Buffer.from(arrayBuffer);
                 
                 // Determine mime type
                 const mimeType = "image/png"; // Simplified, should detect
                 
                 const mediaId = await client.v1.uploadMedia(buffer, { mimeType });
                 mediaIds.push(mediaId);
            }
        }

        const tweetText = `${drop.name}\n\n${drop.description}\n\n#PokemonRed #LassPlaysPokemon`;
        
        await client.v2.tweet({
            text: tweetText,
            media: mediaIds.length > 0 ? { media_ids: mediaIds as [string] | [string, string] | [string, string, string] | [string, string, string, string] } : undefined
        });

        return c.json({ success: true });

    } catch (e: any) {
        return c.json({ error: e.message }, 500);
    }
});

// Gated Content
app.get('/content/:coinAddress', async (c) => {
  const coinAddress = c.req.param('coinAddress');
  const walletAddress = c.req.query('walletAddress');
  const signature = c.req.query('signature');
  const timestamp = c.req.query('timestamp');

  if (!walletAddress || !signature || !timestamp) {
    return c.json({ error: "Missing auth params" }, 401);
  }

  try {
    const db = getDB(c);
    const drop = await db.getDropByAddress(coinAddress);
    
    if (!drop || !drop.exclusiveContentPath) {
      return c.json({ error: "No content found for this drop" }, 404);
    }

    const now = Date.now();
    const reqTime = parseInt(timestamp);
    if (Math.abs(now - reqTime) > 300000) { 
        return c.json({ error: "Signature expired" }, 401);
    }

    // Verify signature logic... (using same verifyMessage)
    // ...

    // Check Ownership
    const isHolder = await checkOwnership(
        walletAddress, 
        coinAddress, 
        c.env.BASE_RPC_URL
    );
    
    if (!isHolder) {
      return c.json({ error: "You do not own this coin" }, 403);
    }

    // Serve Content
    const storage = getStorage(c);
    const object = await storage.get(drop.exclusiveContentPath);
    if (!object) return c.json({ error: "File lost" }, 404);

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set('etag', object.httpEtag);
    
    return new Response(object.body, { headers });

  } catch (e: any) {
    return c.json({ error: "Server error" }, 500);
  }
});

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
