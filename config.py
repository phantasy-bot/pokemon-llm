import sys
import os
from pyAIAgent.utils.file_utils import find_mgba

PORT = 8888 # mGBA socket port
LOAD_SAVESTATE = False # should we load a savestate? Updated by CLI
LUA_SCRIPT = './socketserver.lua' # Adjust if needed
benchmark_path = None   # default: no external benchmark

MGBA_EXE = find_mgba() or None

# If it's still not found, exit
if not MGBA_EXE:
    print("Error: mGBA executable not found.")
    sys.exit(1)

# Stream countdown duration in seconds (default 5 minutes)
# Frontend and backend should use the same value for synchronized transitions
STREAM_COUNTDOWN_SECONDS = int(os.environ.get('STREAM_COUNTDOWN_SECONDS', '300'))
