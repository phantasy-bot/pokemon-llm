# Z.AI MCP Vision Server Setup

## Overview

Z.AI provides enhanced vision capabilities through a Model Context Protocol (MCP) server. This setup is optional - the system will work with direct API calls, but MCP provides better image understanding.

## Prerequisites

- Node.js >= v22.0.0
- Z.AI API key

## Installation

### Option 1: Automatic Setup (Recommended)

The system will automatically download and run the MCP server when needed:

```bash
# Set your environment variables
export ZAI_API_KEY=your_api_key_here
export ZAI_MODE=ZAI

# Run with ZAI mode
python run.py --mode ZAI
```

### Option 2: Manual Installation

Install the MCP server globally:

```bash
npm install -g @z_ai/mcp-server
```

## Usage

When using Z.AI mode, the system will:

1. **Try MCP First**: Automatically start the MCP server for enhanced vision processing
2. **Fallback Gracefully**: If MCP fails, fall back to direct API calls with base64 encoding
3. **Log Status**: Inform you which method is being used

## Troubleshooting

### MCP Server Not Starting

1. Ensure Node.js is installed: `node --version` (should be v22+)
2. Check if npm is available: `npm --version`
3. Verify API key is set: `echo $ZAI_API_KEY`

### Network Issues

If MCP server has connectivity issues:
1. Check internet connection
2. Verify Z.AI API key is valid
3. Check Z.AI service status

### Fallback Mode

The system will automatically fallback to direct API calls if:
- Node.js is not available
- MCP server fails to start
- Network connectivity issues
- API key problems

You'll see log messages indicating which mode is active.

## Environment Variables

```bash
ZAI_API_KEY=your_zai_api_key_here    # Required
ZAI_MODEL=glm-4v                      # Optional, default model
ZAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/  # Optional, custom endpoint
ZAI_MODE=ZAI                          # Required for MCP
```

## Supported Image Formats

- PNG (preferred for screenshots)
- JPEG
- WebP
- GIF

The MCP server automatically handles image transcoding and optimization.