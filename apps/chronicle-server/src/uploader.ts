import { createMetadataBuilder, createZoraUploaderForCreator } from "@zoralabs/coins-sdk";
import { Address } from "viem";
import fs from "fs/promises";

export async function uploadMetadata(
  creator: Address,
  name: string,
  symbol: string,
  description: string,
  imagePath: string,
  attributes: any[] = []
) {
  // Read image file asynchronously
  const imageBuffer = await fs.readFile(imagePath);
  const imageFile = new File([new Uint8Array(imageBuffer)], "image.png", { type: "image/png" });

  const builder = createMetadataBuilder()
    .withName(name)
    .withSymbol(symbol)
    .withDescription(description)
    .withImage(imageFile);

  // Add attributes if any
  if (attributes && attributes.length > 0) {
    // Currently relying on SDK builder defaults for simplicity
  }

  const uploader = createZoraUploaderForCreator(creator);
  const { createMetadataParameters } = await builder.upload(uploader);
  
  return createMetadataParameters;
}
