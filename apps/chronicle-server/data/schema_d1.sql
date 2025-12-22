-- D1 Migration Schema for Chronicle
DROP TABLE IF EXISTS drops;
CREATE TABLE drops (
    id TEXT PRIMARY KEY,
    coinAddress TEXT NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    description TEXT,
    publicImageUrl TEXT,
    metadataUri TEXT,
    exclusiveContentPath TEXT,
    createdAt INTEGER DEFAULT (unixepoch()),
    marketCap TEXT DEFAULT '0',
    volume24h TEXT DEFAULT '0',
    priceChange24h REAL DEFAULT 0,
    status TEXT DEFAULT 'published',
    images TEXT DEFAULT '[]'
);
