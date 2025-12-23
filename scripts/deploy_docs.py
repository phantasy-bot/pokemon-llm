#!/usr/bin/env python3
"""
Deployment script for Lass Pokemon Agent Documentation.
Builds the site and deploys to Cloudflare using Wrangler.
"""

import subprocess
import sys
import os
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_docs.py"
DOCS_SITE_DIR = PROJECT_ROOT / "apps" / "docs-site"
PYTHON_EXE = sys.executable


def run_build():
    """Run the documentation build pipeline."""
    print("--- Building Documentation ---")
    try:
        subprocess.run([PYTHON_EXE, str(BUILD_SCRIPT)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        return False


def deploy_to_cloudflare():
    """Deploy the built site to Cloudflare using Wrangler."""
    print("--- Deploying to Cloudflare ---")
    try:
        # Check if wrangler is available
        subprocess.run(
            ["npx", "wrangler", "--version"], check=True, capture_output=True
        )

        # Run deploy
        subprocess.run(["npx", "wrangler", "deploy"], cwd=DOCS_SITE_DIR, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e}")
        return False
    except FileNotFoundError:
        print("Error: 'npx' or 'wrangler' not found. Please install node/npm.")
        return False


def main():
    # 1. Ensure the site is built
    if not run_build():
        sys.exit(1)

    # 2. Deploy to Cloudflare
    if deploy_to_cloudflare():
        print("\nDocumentation successfully deployed!")
    else:
        print("\nDocumentation deployment failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
