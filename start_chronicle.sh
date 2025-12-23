#!/bin/bash

# Start Chronicle Ecosystem (Worker + UI)
echo "🚀 Starting Chronicle Ecosystem..."

# Function to kill all background processes on exit
cleanup() {
    echo "🛑 Shutting down..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

# 1. Start Chronicle Worker (API)
echo "📦 Starting Chronicle Worker API (Port 8787)..."
cd apps/chronicle-worker
if [ ! -d "node_modules" ]; then
    echo "Installing worker dependencies..."
    npm install
fi
# Use npx wrangler dev to start the worker locally
npx wrangler dev &
WORKER_PID=$!
cd ../..

# Wait for worker to start
sleep 5

# 2. Start Chronicle UI
echo "💻 Starting Chronicle UI (Port 5173)..."
cd apps/chronicle-ui
if [ ! -d "node_modules" ]; then
    echo "Installing UI dependencies..."
    npm install
fi
npm run dev &
UI_PID=$!
cd ../..

echo "✅ Chronicle is running!"
echo "   - API (Worker): http://localhost:8787"
echo "   - UI:           http://localhost:5173"
echo "   - Agent Config: Ensure ZORA_SIDECAR_URL=http://localhost:8787 in .env"
echo ""
echo "Press Ctrl+C to stop."

# Wait for both processes
wait
