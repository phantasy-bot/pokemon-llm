import { http, createConfig } from 'wagmi'
import { base, baseSepolia } from 'wagmi/chains'
import { coinbaseWallet, metaMask, walletConnect } from 'wagmi/connectors'

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'dummy_project_id'

export const config = createConfig({
  chains: [base, baseSepolia],
  connectors: [
    metaMask(),
    coinbaseWallet({ appName: 'Chronicle' }),
    walletConnect({ projectId }),
  ],
  transports: {
    [base.id]: http(),
    [baseSepolia.id]: http(),
  },
})
