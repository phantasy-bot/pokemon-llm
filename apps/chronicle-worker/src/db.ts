export class Database {
  constructor(private db: D1Database) {}

  async getAllDrops() {
    const { results } = await this.db.prepare(`
      SELECT 
        id, coinAddress, name, symbol, description, publicImageUrl, metadataUri, 
        marketCap, volume24h, priceChange24h, status, images,
        CASE WHEN exclusiveContentPath IS NOT NULL THEN 1 ELSE 0 END as hasExclusiveContent,
        createdAt
      FROM drops
      WHERE status = 'published'
      ORDER BY createdAt DESC
    `).all();
    return results;
  }

  async getDrafts() {
    const { results } = await this.db.prepare(`
      SELECT * FROM drops WHERE status = 'draft' ORDER BY createdAt DESC
    `).all();
    return results;
  }

  async getDrop(id: string) {
    return this.db.prepare('SELECT * FROM drops WHERE id = ?').bind(id).first();
  }

  async getDropByAddress(address: string) {
    return this.db.prepare('SELECT * FROM drops WHERE coinAddress = ?').bind(address).first();
  }

  async insertDrop(drop: any) {
    return this.db.prepare(`
      INSERT INTO drops (
        id, coinAddress, name, symbol, description, publicImageUrl, 
        metadataUri, exclusiveContentPath, marketCap, volume24h, priceChange24h, status, images
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      drop.id, drop.coinAddress, drop.name, drop.symbol, drop.description, drop.publicImageUrl,
      drop.metadataUri, drop.exclusiveContentPath, drop.marketCap, drop.volume24h, 
      drop.priceChange24h, drop.status, drop.images
    ).run();
  }

  async updateDrop(drop: any) {
    return this.db.prepare(`
      UPDATE drops 
      SET name = ?, description = ?, publicImageUrl = ?, 
          metadataUri = ?, status = ?, coinAddress = ?, images = ?
      WHERE id = ?
    `).bind(
      drop.name, drop.description, drop.publicImageUrl,
      drop.metadataUri, drop.status, drop.coinAddress, drop.images,
      drop.id
    ).run();
  }
}
