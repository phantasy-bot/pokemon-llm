#!/bin/bash

# Cleanup function to kill background processes on exit
cleanup() {
    echo "🛑 Shutting down..."
    if [ -n "$NPM_PID" ]; then
        echo "Killing UI server (PID: $NPM_PID)..."
        kill $NPM_PID
    fi
    if [ -n "$OPENCODE_PID" ]; then
        echo "Killing OpenCode server (PID: $OPENCODE_PID)..."
        kill $OPENCODE_PID
    fi
    exit
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

echo "🚀 Pokemon LLM Agent Launcher"
echo "============================="

# 0. Ensure dependencies are installed in the correct conda environment
# Detect Conda environment path dynamically
CONDA_ENV_NAME="pokemon-llm"
# Try to find conda base path
if command -v conda >/dev/null 2>&1; then
    CONDA_BASE=$(conda info --base)
    CONDA_ENV="$CONDA_BASE/envs/$CONDA_ENV_NAME"
else
    # Fallback to standard locations if conda command not found (rare but possible in scripts)
    if [ -d "/opt/homebrew/Caskroom/miniconda/base/envs/$CONDA_ENV_NAME" ]; then
        CONDA_ENV="/opt/homebrew/Caskroom/miniconda/base/envs/$CONDA_ENV_NAME"
    elif [ -d "$HOME/miniconda3/envs/$CONDA_ENV_NAME" ]; then
        CONDA_ENV="$HOME/miniconda3/envs/$CONDA_ENV_NAME"
    elif [ -d "$HOME/anaconda3/envs/$CONDA_ENV_NAME" ]; then
        CONDA_ENV="$HOME/anaconda3/envs/$CONDA_ENV_NAME"
    else
        echo "⚠️ Could not auto-detect conda environment '$CONDA_ENV_NAME'."
        CONDA_ENV=""
    fi
fi

if [ -n "$CONDA_ENV" ] && [ -f "$CONDA_ENV/bin/pip" ]; then
    CONDA_PIP="$CONDA_ENV/bin/pip"
    echo "📦 Checking Python dependencies (Environment: $CONDA_ENV)..."
    # Install/update critical dependencies quietly
    $CONDA_PIP install -q --upgrade mutagen >/dev/null 2>&1
    echo "✅ Python dependencies ready"
else
    echo "⚠️ Conda environment '$CONDA_ENV_NAME' not found or pip missing."
    echo "   Please create it with: conda create -n $CONDA_ENV_NAME python=3.10"
fi

# 1. Start Frontend (in background)
echo "🎨 Starting Pokemon UI (npm run dev)..."
cd apps/livestream
# Quick npm install if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "   Installing npm dependencies..."
    npm install --silent
fi
# Run npm in background, redirecting logs to a file to keep terminal clean
npm run dev > ../../ui.log 2>&1 &
NPM_PID=$!
cd ../..
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

# 3.5 Check and Start OpenCode (if needed)
LLM_PROVIDER=""
if [ -f .env ]; then
    # Safely extract variables by grepping
    LLM_PROVIDER=$(grep "^LLM_PROVIDER=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
fi

# Check either LLM_PROVIDER or MODE
if [ "$LLM_PROVIDER" = "OPENCODE" ]; then
    echo "🔍 Checking OpenCode Server (Port 4096)..."
    echo "🔍 Checking OpenCode Server (Port 4096)..."
    if ! nc -z localhost 4096; then
        echo "⚠️  OpenCode server not found at port 4096."
        echo "🚀 Starting OpenCode server..."
        
        # Try to find opencode executable
        OPENCODE_BIN="opencode"
        if [ -f "$CONDA_ENV/bin/opencode" ]; then
            OPENCODE_BIN="$CONDA_ENV/bin/opencode"
        fi
        
        $OPENCODE_BIN --port 4096 > opencode.log 2>&1 &
        OPENCODE_PID=$!
        echo "   PID: $OPENCODE_PID"
        
        # Wait for it to be ready
        echo "⏳ Waiting for OpenCode..."
        RETRY=0
        while ! nc -z localhost 4096; do
            sleep 1
            RETRY=$((RETRY+1))
            if [ $RETRY -ge 10 ]; then
                echo "❌ Failed to start OpenCode. Check opencode.log."
                cleanup
            fi
        done
        echo "✅ OpenCode is ready!"
    else
        echo "✅ OpenCode is already running."
    fi
fi

# 4. Start Backend
echo "🤖 Starting Agent Backend..."
python run.py --auto

# Cleanup when backend exits
cleanup
