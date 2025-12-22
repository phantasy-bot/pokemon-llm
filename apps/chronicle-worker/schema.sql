CREATE TABLE IF NOT EXISTS drops (
    id TEXT PRIMARY KEY,
    coinAddress TEXT,
    name TEXT,
    symbol TEXT,
    description TEXT,
    publicImageUrl TEXT,
    metadataUri TEXT,
    exclusiveContentPath TEXT,
    marketCap TEXT,
    volume24h TEXT,
    priceChange24h REAL,
    status TEXT,
    images TEXT,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
