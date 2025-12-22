import { useState, useEffect } from 'react';
import { useAccount, useSignMessage } from 'wagmi';
import { Drop, getDrafts, publishDrop, updateDraft, tweetDrop } from '../lib/api';

const ADMIN_WALLET = import.meta.env.VITE_ADMIN_WALLET;

export function useAdmin() {
  const { address } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const [drafts, setDrafts] = useState<Drop[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState<string | null>(null);
  const [tweeting, setTweeting] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState(false);

  // Helper to get auth headers
  const getAuthHeaders = async () => {
    if (!address) throw new Error("Wallet not connected");
    
    const timestamp = Date.now().toString();
    const message = `Chronicle Admin Action: ${timestamp}`;
    const signature = await signMessageAsync({ message });
    
    return {
        'x-wallet-address': address,
        'x-signature': signature,
        'x-timestamp': timestamp
    };
  };

  useEffect(() => {
    const authorized = !!(address && ADMIN_WALLET && address.toLowerCase() === ADMIN_WALLET.toLowerCase());
    setIsAuthorized(authorized);
    
    if (authorized) {
      // For initial fetch, we might skip signature or require it once. 
      // For UX, let's require signature to view drafts too, to be safe.
      // But triggering a sign immediately on load is annoying.
      // Option: Just hide UI, but secure writes. 
      // Decision: Let's require auth to VIEW drafts too.
      // Actually, let's make a "Login" button or just sign once and store in session storage?
      // For simplicity/security in this strict mode: We will prompt sign on load.
      handleRefresh();
    } else {
      setLoading(false);
    }
  }, [address]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
        // We can cache the auth headers in memory/state if we want to avoid signing every refresh
        // For now, simple approach: Sign to view (high security)
        // Ideally we'd have a session token. 
        // Let's implement a simple "Session" state.
        const auth = await getAuthHeaders();
        getDrafts(auth)
          .then(setDrafts)
          .catch(console.error)
          .finally(() => setLoading(false));
    } catch (e) {
        console.error("Auth failed for fetching drafts", e);
        setLoading(false);
    }
  };

  const handlePublish = async (id: string) => {
    setPublishing(id);
    try {
      const auth = await getAuthHeaders();
      await publishDrop(id, auth);
      // Refresh without re-signing if possible, but our getDrafts requires signature.
      // We can reuse the auth header if it's within 5 mins.
      await getDrafts(auth).then(setDrafts);
      return true;
    } catch (e: any) {
      console.error(e);
      alert("Failed: " + e.message);
      throw e;
    } finally {
      setPublishing(null);
    }
  };

  const handleTweet = async (id: string) => {
    setTweeting(id);
    try {
        const auth = await getAuthHeaders();
        await tweetDrop(id, auth);
        return true;
    } catch (e: any) {
        console.error(e);
        alert("Failed: " + e.message);
        throw e;
    } finally {
        setTweeting(null);
    }
  };

  const handleUpdate = async (id: string, formData: FormData) => {
    try {
      const auth = await getAuthHeaders();
      await updateDraft(id, formData, auth);
      await getDrafts(auth).then(setDrafts);
      return true;
    } catch (e: any) {
      console.error(e);
      alert("Failed: " + e.message);
      throw e;
    }
  };

  return {
    drafts,
    loading,
    publishing,
    tweeting,
    isAuthorized,
    address,
    handlePublish,
    handleTweet,
    handleUpdate,
    refreshDrafts: handleRefresh
  };
}
