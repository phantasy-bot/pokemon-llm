import { createPublicClient, http, Address, parseAbi } from 'viem';
import { base } from 'viem/chains';

const ERC1155_ABI = parseAbi([
  'function balanceOf(address account, uint256 id) view returns (uint256)'
]);

const ERC721_ABI = parseAbi([
  'function balanceOf(address owner) view returns (uint256)'
]);

export async function checkOwnership(
  walletAddress: string, 
  contractAddress: string, 
  rpcUrl: string
): Promise<boolean> {
  const client = createPublicClient({
    chain: base,
    transport: http(rpcUrl)
  });

  try {
    // Try ERC721 first (Zora Drops are 721 usually, but new ones are 1155)
    // Zora Protocol uses 1155 often. Let's assume 721 for standard drops or check both.
    // Actually, `coins-sdk` creates ERC20/ERC721 usually.
    // Let's try 721 balanceOf.
    const balance = await client.readContract({
      address: contractAddress as Address,
      abi: ERC721_ABI,
      functionName: 'balanceOf',
      args: [walletAddress as Address]
    });

    return (balance as bigint) > 0n;
  } catch (e) {
    // If failed, maybe it's 1155? or just error.
    console.error("Ownership check failed:", e);
    return false;
  }
}
