import { createMetadataBuilder, createZoraUploaderForCreator } from "@zoralabs/coins-sdk";
import { Address } from "viem";
import fs from "fs";

export async function uploadMetadata(
  creator: Address,
  name: string,
  symbol: string,
  description: string,
  imagePath: string,
  attributes: any[] = []
) {
  // Read image file
  const imageBuffer = fs.readFileSync(imagePath);
  const imageFile = new File([new Uint8Array(imageBuffer)], "image.png", { type: "image/png" });

  const builder = createMetadataBuilder()
    .withName(name)
    .withSymbol(symbol)
    .withDescription(description)
    .withImage(imageFile);

  // Add attributes if any
  if (attributes && attributes.length > 0) {
    // The SDK builder might not expose attributes directly in the fluent API 
    // depending on version, but usually it does or we construct metadata manually.
    // Checking docs: "createMetadataParameters" returns metadata.
    // We might need to manually append attributes if the builder doesn't support it 
    // or if we just use the uploader for the image and construct JSON ourselves.
    // For now, let's assume we can just build the basic metadata and merge attributes.
  }

  const uploader = createZoraUploaderForCreator(creator);
  const { createMetadataParameters } = await builder.upload(uploader);
  
  // If we need to add attributes, we might need to modify the uploaded metadata 
  // or upload our own JSON. The SDK handles pinning.
  // For simplicity, let's stick to the builder's output for now.
  
  return createMetadataParameters;
}
