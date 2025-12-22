import { useState } from 'react'
import { useAccount, useWaitForTransactionReceipt, useWalletClient, usePublicClient } from 'wagmi'
import { tradeCoin } from '@zoralabs/coins-sdk'
import { parseEther } from 'viem'
import { Loader2, ShoppingCart, ExternalLink } from 'lucide-react'
import { Polaroid } from './PolaroidStack'

export interface Coin {
  id: string
  name?: string
  symbol?: string
  description?: string
  imageUrl?: string
  marketCap?: string
  volume24h?: string
  priceChange24h?: number
  address: string
  contractAddress?: string
  timestamp?: number
  hasExclusiveContent?: boolean
}

interface CoinCardProps {
  coin: Coin
}

export function CoinCard({ coin }: CoinCardProps) {
  const { address } = useAccount()
  const { data: walletClient } = useWalletClient()
  const publicClient = usePublicClient()
  
  const [buyAmount, setBuyAmount] = useState('0.001')
  const [purchasing, setPurchasing] = useState(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [hash, setHash] = useState<`0x${string}` | undefined>()

  const { isLoading: isConfirming } = useWaitForTransactionReceipt({
    hash,
  })

  // Format helper
  const formatNumber = (num: string | undefined) => {
    if (!num) return 'N/A'
    const numValue = parseFloat(num) / 1e18
    if (numValue >= 1000) return `${(numValue / 1000).toFixed(1)}K ETH`
    if (numValue >= 1) return `${numValue.toFixed(2)} ETH`
    return `${numValue.toFixed(4)} ETH`
  }

  const handleBuyCoin = async () => {
    const targetAddress = coin.address || coin.contractAddress;
    
    if (!address || !targetAddress || !walletClient || !publicClient) {
      setError('Wallet not connected')
      return
    }

    if (!buyAmount || parseFloat(buyAmount) <= 0) {
      setError('Invalid amount')
      return
    }

    setPurchasing(true)
    setError('')
    
    try {
      const tradeParameters = {
        sell: { type: "eth" as const },
        buy: {
          type: "erc20" as const,
          address: targetAddress as `0x${string}`,
        },
        amountIn: parseEther(buyAmount),
        slippage: 0.05,
        sender: address,
      }

      const receipt = await tradeCoin({
        tradeParameters,
        walletClient,
        publicClient,
        account: address,
      })

      setHash(receipt.transactionHash)
      setSuccess('Submitted')
    } catch (err: any) {
      console.error('Error buying coin:', err)
      setError('Failed')
    } finally {
      setPurchasing(false)
    }
  }

  const isLoading = purchasing || isConfirming

  return (
    <div className="w-full px-4 py-2">
      {/* Content Card with Explicit Tape Elements */}
      <div className="relative bg-white text-zinc-900 shadow-md p-6 md:p-8">
        
        {/* Black Tape Corners */}
        <div className="absolute -top-3 -left-3 w-16 h-5 bg-black -rotate-45 shadow-sm z-20 pointer-events-none opacity-90" />
        <div className="absolute -top-3 -right-3 w-16 h-5 bg-black rotate-45 shadow-sm z-20 pointer-events-none opacity-90" />
        <div className="absolute -bottom-3 -left-3 w-16 h-5 bg-black rotate-45 shadow-sm z-20 pointer-events-none opacity-90" />
        <div className="absolute -bottom-3 -right-3 w-16 h-5 bg-black -rotate-45 shadow-sm z-20 pointer-events-none opacity-90" />

        <div className="flex flex-col md:flex-row gap-8 relative z-10">
           {/* Image (Polaroid Style) */}
           <div className="w-full md:w-64 flex-shrink-0">
             <Polaroid 
                src={coin.imageUrl || ''} 
                alt={coin.name || 'Drop'} 
                isStack={coin.hasExclusiveContent}
                timestamp={coin.timestamp}
                className="w-full"
             />
           </div>

           {/* Info */}
           <div className="flex-1 flex flex-col min-w-0">
              <div className="flex justify-between items-start gap-4 mb-2 md:mb-4">
                <h3 className="text-xl md:text-3xl font-bold font-display uppercase tracking-tight leading-tight truncate">
                  {coin.name || 'Unknown Drop'}
                </h3>
              </div>
              
              {/* Description - hidden on mobile */}
              <p className="hidden md:block font-mono text-sm text-ink-light mb-8 line-clamp-4 leading-relaxed">
                {coin.description}
              </p>
              
              {/* Actions & Stats */}
              <div className="mt-auto pt-6 border-t-2 border-black/5 flex flex-wrap items-end justify-between gap-4">
                 
                 {/* Metadata Column */}
                 <div className="flex flex-col gap-1 text-xs font-mono text-ink-light">
                     <div className="flex gap-4">
                       <span>MC: <b className="text-black">{formatNumber(coin.marketCap)}</b></span>
                       <span>Vol: <b className="text-black">{formatNumber(coin.volume24h)}</b></span>
                       {coin.priceChange24h !== undefined && (
                         <span>24h: <b className={coin.priceChange24h >= 0 ? 'text-green-600' : 'text-red-600'}>
                           {coin.priceChange24h >= 0 ? '+' : ''}{coin.priceChange24h.toFixed(2)}%
                         </b></span>
                       )}
                     </div>
                 </div>

                 {/* Action Column */}
                 <div className="flex flex-col items-end gap-2">
                    {error && <span className="text-[10px] text-red-600 font-mono bg-red-50 px-1">{error}</span>}
                    {success && <span className="text-[10px] text-green-600 font-mono bg-green-50 px-1">{success}</span>}
                    
                     <div className="flex items-center gap-2">
                       {/* Modern pill-style input group */}
                       <div className="flex items-center bg-zinc-100 rounded-full overflow-hidden border border-zinc-200 hover:border-zinc-300 transition-colors">
                         <div className="flex items-center px-3 py-2">
                           <span className="text-[10px] font-bold text-zinc-500 mr-1.5">Ξ</span>
                           <input 
                             type="number"
                             step="0.001"
                             min="0"
                             value={buyAmount}
                             onChange={(e) => setBuyAmount(e.target.value)}
                             className="w-14 text-right font-mono text-sm outline-none bg-transparent font-semibold text-zinc-800"
                           />
                         </div>
                         <button
                           onClick={handleBuyCoin}
                           disabled={isLoading || !address}
                           className="flex items-center gap-1.5 px-4 py-2 bg-black text-white rounded-full disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-800 active:scale-95 transition-all font-mono text-xs uppercase tracking-wide font-bold"
                         >
                           {isLoading ? <Loader2 size={12} className="animate-spin" /> : <ShoppingCart size={12} />}
                           {isLoading ? '...' : 'Buy'}
                         </button>
                       </div>
                       
                       <a 
                         href={`https://zora.co/collect/base:${coin.address}`}
                         target="_blank"
                         rel="noopener noreferrer"
                         className="h-9 w-9 flex items-center justify-center bg-zinc-100 hover:bg-zinc-200 border border-zinc-200 rounded-full transition-all hover:scale-105 active:scale-95"
                         title="View on Zora"
                       >
                         <ExternalLink size={14} className="text-zinc-600" />
                       </a>
                     </div>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}
