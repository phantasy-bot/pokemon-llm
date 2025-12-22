import { createCoin, CreateConstants } from "@zoralabs/coins-sdk";
import { createWalletClient, createPublicClient, http, Address, Hex } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

export async function createNewCoin(
  privateKey: Hex,
  creatorAddress: Address,
  name: string,
  symbol: string,
  metadataUri: string,
  chainId: number = 8453
) {
  const account = privateKeyToAccount(privateKey);
  
  // Use RPC URL from env if available, otherwise default public
  const transport = process.env.BASE_RPC_URL ? http(process.env.BASE_RPC_URL) : http();

  const publicClient = createPublicClient({
    chain: base,
    transport
  });

  const walletClient = createWalletClient({
    account,
    chain: base,
    transport
  });

  console.log(`Creating coin: ${name} (${symbol}) for creator ${creatorAddress}`);

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
      chainId: chainId,
      startingMarketCap: CreateConstants.StartingMarketCaps.LOW
    }
  });

  return result;
}
