import Database from 'better-sqlite3';
import fs from 'fs-extra';
import path from 'path';

const DB_PATH = process.env.DB_PATH || 'data/chronicle.db';

// Ensure directory exists
fs.ensureDirSync(path.dirname(DB_PATH));

const db = new Database(DB_PATH);

// Initialize schema
db.exec(`
  CREATE TABLE IF NOT EXISTS drops (
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
    priceChange24h REAL DEFAULT 0
  );
`);

// Migration for existing tables (safe to run)
try { db.exec('ALTER TABLE drops ADD COLUMN marketCap TEXT DEFAULT "0"'); } catch (e) {}
try { db.exec('ALTER TABLE drops ADD COLUMN volume24h TEXT DEFAULT "0"'); } catch (e) {}
try { db.exec('ALTER TABLE drops ADD COLUMN priceChange24h REAL DEFAULT 0'); } catch (e) {}

export const insertDrop = db.prepare(`
  INSERT INTO drops (
    id, coinAddress, name, symbol, description, publicImageUrl, 
    metadataUri, exclusiveContentPath, marketCap, volume24h, priceChange24h
  )
  VALUES (
    @id, @coinAddress, @name, @symbol, @description, @publicImageUrl, 
    @metadataUri, @exclusiveContentPath, @marketCap, @volume24h, @priceChange24h
  )
`);

export const getDropByAddress = db.prepare(`
  SELECT * FROM drops WHERE coinAddress = ?
`);

export const getAllDrops = db.prepare(`
  SELECT 
    id, coinAddress, name, symbol, description, publicImageUrl, metadataUri, 
    marketCap, volume24h, priceChange24h,
    CASE WHEN exclusiveContentPath IS NOT NULL THEN 1 ELSE 0 END as hasExclusiveContent,
    createdAt
  FROM drops
  ORDER BY createdAt DESC
`);

export default db;
