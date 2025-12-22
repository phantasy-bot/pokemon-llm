export interface Drop {
  id: string;
  coinAddress: string;
  name: string;
  symbol: string;
  description: string;
  publicImageUrl: string;
  hasExclusiveContent: boolean;
  createdAt: number;
}

const API_BASE = import.meta.env.VITE_CHRONICLE_API_URL || 'http://localhost:3001';

export async function getFeed(): Promise<Drop[]> {
  const res = await fetch(`${API_BASE}/api/feed`);
  if (!res.ok) throw new Error('Failed to fetch feed');
  const data = await res.json();
  return data.drops;
}

export async function getExclusiveContentUrl(
  coinAddress: string, 
  walletAddress: string, 
  signature: string, 
  timestamp: string
): Promise<string> {
  // Construct the URL with query params
  const params = new URLSearchParams({
    walletAddress,
    signature,
    timestamp
  });
  
  return `${API_BASE}/api/content/${coinAddress}?${params.toString()}`;
}
