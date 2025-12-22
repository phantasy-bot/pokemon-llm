export interface Drop {
  id: string;
  coinAddress: string;
  name: string;
  symbol: string;
  description: string;
  publicImageUrl: string;
  images?: string[];
  hasExclusiveContent: boolean;
  createdAt: number;
  status?: 'draft' | 'published';
}

const API_BASE = import.meta.env.VITE_CHRONICLE_API_URL || 'http://localhost:3001';

// Helper for Authenticated Requests
interface AuthHeaders {
    'x-wallet-address': string;
    'x-signature': string;
    'x-timestamp': string;
}

export async function getFeed(): Promise<Drop[]> {
  const res = await fetch(`${API_BASE}/api/feed`);
  if (!res.ok) throw new Error('Failed to fetch feed');
  const data = await res.json();
  return data.drops;
}

export async function getDrafts(auth: AuthHeaders): Promise<Drop[]> {
  const res = await fetch(`${API_BASE}/api/drafts`, {
    headers: { ...auth }
  });
  if (!res.ok) throw new Error('Failed to fetch drafts');
  const data = await res.json();
  return data.drafts;
}

export async function publishDrop(id: string, auth: AuthHeaders): Promise<{ success: boolean; coinAddress: string }> {
  const res = await fetch(`${API_BASE}/api/drop/${id}/publish`, { 
      method: 'POST',
      headers: { ...auth }
  });
  if (!res.ok) throw new Error('Failed to publish');
  return res.json();
}

export async function tweetDrop(id: string, auth: AuthHeaders): Promise<void> {
  const res = await fetch(`${API_BASE}/api/drop/${id}/tweet`, { 
      method: 'POST',
      headers: { ...auth }
  });
  if (!res.ok) throw new Error('Failed to post tweet');
}

export async function updateDraft(id: string, formData: FormData, auth: AuthHeaders): Promise<void> {
  const res = await fetch(`${API_BASE}/api/drop/${id}`, {
    method: 'PUT',
    body: formData,
    headers: { ...auth } // Note: Fetch automatically sets Content-Type for FormData
  });
  if (!res.ok) throw new Error('Failed to update draft');
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
