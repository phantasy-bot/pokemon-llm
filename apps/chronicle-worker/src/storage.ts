export class Storage {
  constructor(private bucket: R2Bucket) {}

  async upload(key: string, body: ReadableStream | Blob | string) {
    await this.bucket.put(key, body);
    return key;
  }

  async get(key: string) {
    const object = await this.bucket.get(key);
    if (!object) return null;
    return object;
  }
  
  async delete(key: string) {
    await this.bucket.delete(key);
  }
}
