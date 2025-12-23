import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

# Load env from root
load_dotenv()


async def test_chronicle_connection():
    print("🧪 Chronicle Integration Test")
    print("===========================")

    url = os.getenv("ZORA_SIDECAR_URL")
    key = os.getenv("CHRONICLE_SECRET_KEY")

    print(f"URL: {url}")
    print(f"Key: {key[:4]}...{key[-4:] if key else 'None'}")

    if not url or not key:
        print("❌ Missing ZORA_SIDECAR_URL or CHRONICLE_SECRET_KEY in .env")
        return

    # Prepare dummy data
    data = {
        "name": "Integration Test Draft",
        "symbol": "TEST-001",
        "description": "This is a test draft sent from the python agent integration script.",
        "attributes": json.dumps([{"trait_type": "Test", "value": "True"}]),
        "status": "draft",
    }

    # Dummy image (1x1 pixel transparent png)
    dummy_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    files = {"image": ("test_image.png", dummy_image, "image/png")}

    print("\n🚀 Sending request...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}/api/drop", data=data, files=files, headers={"x-api-key": key}
            )

            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code == 200:
                print("\n✅ SUCCESS: Draft created!")
                print("Go to the Admin UI to verify it appears.")
            else:
                print("\n❌ FAILED: Server rejected request.")

    except Exception as e:
        print(f"\n❌ ERROR: Connection failed - {e}")


if __name__ == "__main__":
    asyncio.run(test_chronicle_connection())
