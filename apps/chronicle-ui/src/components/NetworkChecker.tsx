import { useAccount, useSwitchChain } from 'wagmi'
import { base } from 'wagmi/chains'
import { AlertTriangle } from 'lucide-react'

export function NetworkChecker() {
  const { chainId, isConnected } = useAccount()
  const { switchChain } = useSwitchChain()

  if (!isConnected || chainId === base.id) return null

  return (
    <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 p-4 rounded-xl mb-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle size={20} />
        <span className="font-medium">Wrong network. Please switch to Base.</span>
      </div>
      <button
        onClick={() => switchChain({ chainId: base.id })}
        className="px-4 py-1.5 bg-yellow-500 text-black font-medium rounded-lg text-sm hover:bg-yellow-400 transition-colors"
      >
        Switch Network
      </button>
    </div>
  )
}
