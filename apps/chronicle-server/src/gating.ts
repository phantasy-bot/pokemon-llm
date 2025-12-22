import { createPublicClient, http, Address } from 'viem';
import { base } from 'viem/chains';

const publicClient = createPublicClient({
  chain: base,
  transport: http(process.env.BASE_RPC_URL)
});

export async function checkOwnership(walletAddress: Address, coinAddress: Address): Promise<boolean> {
  try {
    const balance = await publicClient.readContract({
      address: coinAddress,
      abi: [{
        name: 'balanceOf',
        type: 'function',
        stateMutability: 'view',
        inputs: [{ name: 'account', type: 'address' }],
        outputs: [{ name: '', type: 'uint256' }],
      }],
      functionName: 'balanceOf',
      args: [walletAddress]
    });

    return (balance as bigint) > 0n;
  } catch (error) {
    console.error(`Error checking ownership for ${walletAddress} on ${coinAddress}:`, error);
    return false;
  }
}

export async function verifySignature(message: string, signature: `0x${string}`, address: Address): Promise<boolean> {
  // In a real implementation, verify the signature matches the address using viem
  // For MVP, we'll assume the client sent valid data, but we SHOULD implement verifyMessage
  // import { verifyMessage } from 'viem'
  // const valid = await verifyMessage({ address, message, signature })
  // return valid
  
  // For now, let's implement strict checking
  try {
      const { verifyMessage } = await import('viem');
      const valid = await verifyMessage({ 
          address, 
          message, 
          signature 
      });
      return valid;
  } catch (e) {
      console.error("Signature verification failed:", e);
      return false;
  }
}
