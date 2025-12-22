#!/bin/bash

# Start Chronicle Server and UI
echo "🚀 Starting Chronicle Ecosystem..."

# Function to kill all background processes on exit
cleanup() {
    echo "🛑 Shutting down..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

# 1. Start Chronicle Server
echo "📦 Starting Chronicle Server (Port 3001)..."
cd apps/chronicle-server
if [ ! -d "node_modules" ]; then
    echo "Installing server dependencies..."
    npm install
fi
npm run dev &
SERVER_PID=$!
cd ../..

# Wait for server to start
sleep 2

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
echo "   - Server: http://localhost:3001"
echo "   - UI:     http://localhost:5173"
echo "   - Agent:  Run 'python run.py' in a separate terminal"
echo ""
echo "Press Ctrl+C to stop."

# Wait for both processes
wait
