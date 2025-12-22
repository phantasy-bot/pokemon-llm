import { useAccount, useSignMessage } from 'wagmi'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { CoinCard, type Coin } from '../components/CoinCard'
import { BookmarkFlag } from '../components/BookmarkFlag'
import { type Drop } from '../lib/api'
import { useState, useEffect } from 'react'

// Extended Coin type for App usage
type AppCoin = Coin & { hasExclusiveContent: boolean }

interface TimelineContext {
  drops: Drop[];
  currentIndex: number;
  setCurrentIndex: React.Dispatch<React.SetStateAction<number>>;
}

export function Timeline() {
  const { address } = useAccount()
  const { signMessageAsync } = useSignMessage()
  const { drops, currentIndex } = useOutletContext<TimelineContext>();
  const navigate = useNavigate()
  const [dots, setDots] = useState('.')

  useEffect(() => {
    const interval = setInterval(() => {
        setDots(prev => prev.length < 3 ? prev + '.' : '.')
    }, 500)
    return () => clearInterval(interval)
  }, [])
  
  const coins: AppCoin[] = drops.map(drop => ({
    id: drop.id,
    name: drop.name,
    symbol: drop.symbol,
    description: drop.description,
    imageUrl: drop.publicImageUrl,
    address: drop.coinAddress,
    timestamp: drop.createdAt * 1000, 
    hasExclusiveContent: drop.hasExclusiveContent,
    marketCap: (drop as any).marketCap, 
    volume24h: (drop as any).volume24h,
    priceChange24h: (drop as any).priceChange24h,
    images: (drop as any).images
  }))

  const handleUnlock = async (coinAddress: string) => {
    const coin = coins.find(c => c.address === coinAddress);
    const isTeaser = coin?.symbol === "LLP-001" || coin?.address === "0x5555555555555555555555555555555555555555";

    if (isTeaser) {
        navigate(`/content/${coinAddress}`);
        return;
    }

    if (!address) return;
    try {
      const timestamp = Date.now().toString();
      const message = `Authenticate Chronicle Access: ${coinAddress} ${timestamp}`;
      await signMessageAsync({ message });
      navigate(`/content/${coinAddress}`);
    } catch (e) {
      console.error("Unlock failed", e);
      alert("Verification failed. Ensure you own this coin.");
    }
  }

  const currentCoin = coins[currentIndex]

  return (
    <div className="flex-1 flex items-center justify-center relative w-full h-full">
      {/* Content Area - Centered vertically */}
      {coins.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-ink-light gap-4">
          <div className="h-8" /> {/* Spacer to maintain position without loader */}
          <p className="text-sm uppercase tracking-widest font-mono">
            Retrieving logs<span className="inline-block w-4 text-left">{dots}</span>
          </p>
        </div>
      ) : currentCoin ? (
        <CoinCard coin={currentCoin} />
      ) : null}

      {/* Unlockable Content Button - Fixed at bottom */}
      {currentCoin?.hasExclusiveContent ? (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30">
           <BookmarkFlag 
             type={(currentCoin.symbol === "LLP-001" || currentCoin.address === "0x5555555555555555555555555555555555555555") ? 'teaser' : 'locked'}
             onClick={() => handleUnlock(currentCoin.address)}
           />
        </div>
      ) : null}
    </div>
  )
}
