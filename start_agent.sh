#!/bin/bash

# Cleanup function to kill background processes on exit
cleanup() {
    echo "🛑 Shutting down..."
    if [ -n "$NPM_PID" ]; then
        echo "Killing UI server (PID: $NPM_PID)..."
        kill $NPM_PID
    fi
    exit
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

echo "🚀 Pokemon LLM Agent Launcher"
echo "============================="

# 0. Ensure dependencies are installed in the correct conda environment
CONDA_ENV="/opt/homebrew/Caskroom/miniconda/base/envs/pokemon-llm"
CONDA_PIP="$CONDA_ENV/bin/pip"

if [ -f "$CONDA_PIP" ]; then
    echo "📦 Checking Python dependencies..."
    # Install/update critical dependencies quietly
    $CONDA_PIP install -q --upgrade mutagen >/dev/null 2>&1
    echo "✅ Python dependencies ready"
else
    echo "⚠️ Conda environment not found at $CONDA_ENV"
    echo "   Please create it with: conda create -n pokemon-llm python=3.10"
fi

# 1. Start Frontend (in background)
echo "🎨 Starting Pokemon UI (npm run dev)..."
cd pokemon-ui
# Quick npm install if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "   Installing npm dependencies..."
    npm install --silent
fi
# Run npm in background, redirecting logs to a file to keep terminal clean
npm run dev > ../ui.log 2>&1 &
NPM_PID=$!
cd ..
echo "   PID: $NPM_PID"
echo "   Logs: ui.log"

# 2. Wait for Frontend to be ready
echo "⏳ Waiting for UI to be ready at http://localhost:5173..."
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:5173 > /dev/null; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Frontend failed to start in 30 seconds. Check ui.log."
        cleanup
    fi
done
echo "✅ UI is ready!"

# 3. Open Browser
echo "🌍 Opening Browser..."
open http://localhost:5173

# 4. Start Backend
echo "🤖 Starting Agent Backend..."
python run.py --auto

# Cleanup when backend exits
cleanup
