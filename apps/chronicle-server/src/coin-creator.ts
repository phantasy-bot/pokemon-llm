import { createCoin, CreateConstants } from "@zoralabs/coins-sdk";
import { createWalletClient, createPublicClient, http, Address, Hex } from "viem";
import { base, baseSepolia } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

export async function createNewCoin(
  privateKey: Hex,
  creatorAddress: Address,
  name: string,
  symbol: string,
  metadataUri: string,
  chainIdOverride?: number
) {
  const account = privateKeyToAccount(privateKey);
  
  // Determine chain from env or override
  const envChainId = process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID) : 8453;
  const chainId = chainIdOverride || envChainId;
  
  // Select chain object
  const chain = chainId === 84532 ? baseSepolia : base;
  
  console.log(`Using chain: ${chain.name} (${chain.id})`);

  // Use RPC URL from env if available, otherwise default public
  const transport = process.env.BASE_RPC_URL ? http(process.env.BASE_RPC_URL) : http();

  const publicClient = createPublicClient({
    chain,
    transport
  });

  const walletClient = createWalletClient({
    account,
    chain,
    transport
  });

  console.log(`Creating coin: ${name} (${symbol}) for creator ${creatorAddress} on ${chain.name}`);

  const result = await createCoin({
    publicClient,
    walletClient,
    call: {
      creator: creatorAddress,
      name,
      symbol,
      metadata: {
        type: "RAW_URI",
        uri: metadataUri
      },
      currency: CreateConstants.ContentCoinCurrencies.ZORA,
      chainId: chain.id,
      startingMarketCap: CreateConstants.StartingMarketCaps.LOW
    }
  });

  return result;
}
