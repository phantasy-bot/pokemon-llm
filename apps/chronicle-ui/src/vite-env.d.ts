/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WALLETCONNECT_PROJECT_ID: string
  readonly VITE_ZORA_CREATOR_ADDRESS: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
