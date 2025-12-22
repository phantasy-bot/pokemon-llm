import { useAccount, useConnect, useDisconnect } from 'wagmi'
import { LogOut, Wallet } from 'lucide-react'
import { useState } from 'react'

const getWalletIcon = (name: string) => {
  const n = name.toLowerCase()
  if (n.includes('metamask')) return 'https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg'
  if (n.includes('coinbase')) return 'https://avatars.githubusercontent.com/u/18060234?s=200&v=4'
  if (n.includes('walletconnect')) return 'https://raw.githubusercontent.com/WalletConnect/walletconnect-assets/master/Logo/Blue%20(Default)/Logo.svg'
  if (n.includes('phantom')) return 'https://phantom.app/img/phantom-logo.svg'
  if (n.includes('brave')) return 'https://upload.wikimedia.org/wikipedia/commons/5/51/Brave_icon_lionface.png'
  return null
}

export function WalletConnection() {
  const { address, isConnected } = useAccount()
  const { connect, connectors } = useConnect()
  const { disconnect } = useDisconnect()
  const [showConnectors, setShowConnectors] = useState(false)

  if (isConnected) {
    return (
      <div className="group relative">
        <button className="flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2 bg-white border border-black shadow-brutal-sm hover:shadow-brutal transition-all font-mono text-sm rounded-full">
          <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <span className="hidden md:inline">{address?.slice(0, 6)}...{address?.slice(-4)}</span>
        </button>
        
        <div className="absolute right-0 top-full mt-2 w-full opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
          <button 
            onClick={() => disconnect()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-500 border border-black shadow-brutal-sm hover:bg-red-600 text-black font-mono text-xs font-bold rounded-lg transition-colors"
          >
            <LogOut size={12} />
            <span className="hidden md:inline">Disconnect</span>
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      <button 
        onClick={() => setShowConnectors(!showConnectors)}
        className="flex items-center gap-2 px-3 md:px-6 py-2 bg-[#FDFBF7] text-black shadow-brutal-sm hover:shadow-brutal border border-black hover:-translate-y-0.5 active:translate-y-0 active:shadow-none transition-all font-mono text-sm uppercase tracking-wide rounded-full"
      >
        <Wallet size={14} />
        <span className="hidden md:inline">Connect Wallet</span>
      </button>

      {showConnectors && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-black shadow-brutal p-2 z-50 flex flex-col gap-1 rounded-xl">
          {connectors.map((connector) => {
            const icon = getWalletIcon(connector.name)
            return (
              <button
                key={connector.uid}
                onClick={() => {
                  connect({ connector })
                  setShowConnectors(false)
                }}
                className="w-full text-left px-3 py-2 hover:bg-zinc-100 font-mono text-xs border border-transparent hover:border-black transition-all flex items-center gap-3 rounded-lg"
              >
                {icon ? (
                  <img src={icon} alt={connector.name} className="w-5 h-5 object-contain" />
                ) : (
                  <div className="w-5 h-5 bg-zinc-200 rounded-full" />
                )}
                {connector.name}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
