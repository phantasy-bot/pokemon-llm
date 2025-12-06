import argparse
import subprocess
import socket
import time
import os
import sys
import asyncio
import logging
import signal
import shutil
# Environment detection and validation
def ensure_python_environment():
    """Ensure we're running with correct Python environment and dependencies."""

    # Try to import critical dependencies to verify environment
    missing_deps = []
    try:
        from PIL import Image
    except ImportError:
        missing_deps.append("PIL (Pillow)")

    try:
        import openai
    except ImportError:
        missing_deps.append("openai")

    try:
        import websockets
    except ImportError:
        missing_deps.append("websockets")

    try:
        import dotenv
    except ImportError:
        missing_deps.append("python-dotenv")

    # If all dependencies are available, we're good
    if not missing_deps:
        print("✅ Python environment validated successfully")
        return True

    # Dependencies missing, try to find and use conda environment
    print(f"⚠️ Missing dependencies: {', '.join(missing_deps)}")

    # Check if we're already in conda environment
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env:
        print(f"Current conda environment: {conda_env}")
        print("Dependencies may not be installed. Run: pip install -r requirements.txt")
    else:
        print("Not in a conda environment, searching for pokemon-llm environment...")

    # Common conda installation paths
    conda_paths = [
        "/opt/homebrew/Caskroom/miniconda/base/envs/pokemon-llm/bin/python",
        "/opt/miniconda3/envs/pokemon-llm/bin/python",
        "/usr/local/miniconda3/envs/pokemon-llm/bin/python",
        os.path.expanduser("~/miniconda3/envs/pokemon-llm/bin/python"),
        os.path.expanduser("~/anaconda3/envs/pokemon-llm/bin/python"),
    ]

    for conda_python in conda_paths:
        if os.path.exists(conda_python):
            print(f"🔄 Found conda environment, switching to: {conda_python}")
            # Re-exec this script with the correct python
            os.execv(conda_python, [conda_python] + sys.argv)

    # No conda environment found
    print("❌ No suitable Python environment found.")
    print("\nTo fix this issue:")
    print("1. Create conda environment:")
    print("   conda create -n pokemon-llm python=3.10")
    print("   conda activate pokemon-llm")
    print("2. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("3. Run again: python run.py --auto")
    return False

# Ensure correct environment before importing other modules
if not ensure_python_environment():
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

from pyAIAgent.utils.misc import parse_max_loops_fn
from pyAIAgent.utils.socket_utils import send_command
from pyAIAgent.game.state import DEFAULT_ROM, get_rom_path
from websocket_service import broadcast_message, run_server_forever as start_websocket_service
from benchmark import load
from interactive import interactive_console
from llmdriver import run_auto_loop, MODEL
from run_persistence import RunPersistence

# --- Configuration (excluding WebSocket specific) ---
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
log = logging.getLogger("main")

# Global reference for graceful shutdown
_global_socket = None
_global_persistence = None
_global_run_state = None

def auto_detect_savestate() -> tuple[str | None, str | None]:
    """Check if save state files exist and return (type, path).
    Priority: .ss1 (primary) > -backup.ss1 (backup)
    Returns (type, path) if found, (None, None) otherwise.
    """
    rom_path = get_rom_path()
    rom_dir = os.path.dirname(rom_path)
    rom_name = os.path.splitext(os.path.basename(rom_path))[0]
    
    primary_save = os.path.join(rom_dir, f"{rom_name}.ss1")
    backup_save = os.path.join(rom_dir, f"{rom_name}-backup.ss1")
    
    if os.path.exists(primary_save):
        log.info(f"🎮 Found save state: {primary_save}")
        return ("primary", primary_save)
    elif os.path.exists(backup_save):
        log.info(f"🎮 Found backup save state: {backup_save} (restoring from backup)")
        # Copy backup to primary slot for mGBA to load
        try:
            shutil.copy2(backup_save, primary_save)
            log.info(f"📦 Restored backup to primary slot")
            return ("backup", primary_save)
        except Exception as e:
            log.warning(f"Failed to restore backup: {e}")
            return (None, None)
    else:
        log.info("🆕 No save state found - starting fresh game")
        return (None, None)


def graceful_save_and_exit(sock, signum=None, frame=None):
    """Save game state before exiting."""
    global _global_persistence, _global_run_state
    log.info("\n🛑 Graceful shutdown initiated...")
    if sock:
        try:
            log.info("💾 Saving game state before exit...")
            response = send_command(sock, "SAVESTATE 1")
            if response and "OK" in response:
                log.info("✅ Game saved successfully!")
                # Update persistence with final state
                if _global_persistence and _global_run_state:
                    rom_path = get_rom_path()
                    rom_dir = os.path.dirname(rom_path)
                    rom_name = os.path.splitext(os.path.basename(rom_path))[0]
                    save_path = os.path.join(rom_dir, f"{rom_name}.ss1")
                    _global_persistence.update_save_state_hash(_global_run_state.run_id, save_path)
                    _global_persistence.save_run_state(_global_run_state)
                    log.info("✅ Run state persisted to database!")
            else:
                log.warning(f"Save may have failed: {response}")
        except Exception as e:
            log.error(f"Error during graceful save: {e}")


# Initialize state - llmdriver will update this
state = {
    "actions": 0,
    "badges": [],
    "gameStatus": "0h 0m 0s",
    "processingStatus": "",  # Detailed status: "SENDING VISION...", "RETRYING VISION (2/5)...", "THINKING..."
    "goals": { "primary": 'Initializing...', "secondary": 'Initializing...', "tertiary": 'Initializing...' },
    "otherGoals": 'Initializing...',
    "currentTeam": [],
    "modelName": MODEL,
    "tokensUsed": 0,
    "minimapLocation": "Unknown",
    "minimapTimestamp": 0,  # Timestamp for minimap image cache-busting
    "log_entries": []
}

def start_mgba_with_scripting(rom_path=None, port=config.PORT):
    rom_path = rom_path or os.path.join(os.path.dirname(__file__), get_rom_path())
    if not os.path.exists(rom_path):
        log.error(f"ROM file not found: {rom_path}")
        sys.exit(1)
    if not os.path.exists(config.MGBA_EXE):
         log.error(f"mGBA executable not found: {config.MGBA_EXE}")
         sys.exit(1)
    if not os.path.exists(config.LUA_SCRIPT):
        log.error(f"Lua script not found: {config.LUA_SCRIPT}")
        sys.exit(1)

    # FIX: Clean up stale minimap file on startup to prevent cached display in UI
    minimap_files = ["minimap.png", "latest.png", "latest_with_minimap.png"]
    for mf in minimap_files:
        if os.path.exists(mf):
            try:
                os.remove(mf)
                log.info(f"🧹 Cleaned up stale file: {mf}")
            except Exception as e:
                log.warning(f"Could not remove {mf}: {e}")

    cmd = [config.MGBA_EXE, '--script', config.LUA_SCRIPT, rom_path]
    log.info(f"Starting mGBA: {' '.join(cmd)}")
    try:
        # Redirect stdout to DEVNULL, capture stderr
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        log.error(f"Failed to start mGBA. Ensure '{config.MGBA_EXE}' is correct and executable.")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error starting mGBA: {e}", exc_info=True)
        sys.exit(1)

    # Wait a bit for mGBA and Lua script to initialize the socket server
    time.sleep(3) # Might need adjustment based on system speed

    # Check if mGBA exited prematurely
    if proc.poll() is not None:
        stderr_output = proc.stderr.read() # Read captured stderr
        log.error(f"mGBA process terminated unexpectedly shortly after start. Exit code: {proc.returncode}")
        if stderr_output:
            log.error(f"mGBA stderr:\n{stderr_output.strip()}")
        else:
            log.error("mGBA stderr is empty.")
        sys.exit(1)

    # Attempt to connect to the mGBA socket
    sock = None
    retries = 5
    for attempt in range(retries):
        try:
            # create_connection handles both IPv4/IPv6
            sock = socket.create_connection(('localhost', port), timeout=2)
            # Keep blocking for simplicity in current setup (console/llmdriver manage reads)
            sock.setblocking(True)
            log.info(f"Connected to mGBA scripting server on port {port}")
            
            # Store global reference for graceful shutdown
            global _global_socket
            _global_socket = sock
            
            # Auto-detect and load save state
            if config.LOAD_SAVESTATE:
                log.info("config.LOAD_SAVESTATE is True, attempting to load savestate 1.")
                send_command(sock, "LOADSTATE 1")
            else:
                # Auto-detect save state files
                save_type = auto_detect_savestate()
                if save_type:
                    log.info(f"Auto-loading save state (type: {save_type})...")
                    send_command(sock, "LOADSTATE 1")
            
            return proc, sock # Success
        except ConnectionRefusedError:
            log.warning(f"Connection to mGBA refused (attempt {attempt+1}/{retries}). Is mGBA running and script loaded?")
            if proc.poll() is not None: # Check again if mGBA died while waiting
                 stderr_output = proc.stderr.read()
                 log.error(f"mGBA process terminated while attempting to connect. Exit code: {proc.returncode}")
                 if stderr_output:
                     log.error(f"mGBA stderr:\n{stderr_output.strip()}")
                 sys.exit(1)
            time.sleep(1.5) # Wait longer between retries
        except socket.timeout:
            log.warning(f"Connection to mGBA timed out (attempt {attempt+1}/{retries}).")
            time.sleep(1)
        except Exception as e:
            # Catch other potential socket errors
            log.error(f"Unexpected error connecting to mGBA socket: {e}", exc_info=True)
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait()
            sys.exit(1)

    # If loop finishes without returning, connection failed
    log.error(f"Failed to connect to mGBA scripting server at localhost:{port} after {retries} attempts.")
    if proc and proc.poll() is None:
        log.info("Terminating mGBA process due to connection failure.")
        proc.terminate()
        proc.wait()
    sys.exit(1)


# helper functions to reduce redundant code


async def shutdown_socket(sock, is_async):
  if sock:
      try:
          log.info("Sending quit command to mGBA script...")
          try:
              sock.sendall(b"quit\n")
              
              if is_async:
                await asyncio.sleep(0.2)
              else:
                time.sleep(0.2) 
              
          except OSError as send_err:
              log.warning(f"Could not send quit command to mGBA (socket likely closed): {send_err}")
          sock.close()
          log.info("mGBA socket closed.")
      except Exception as e:
          log.error(f"Error closing mGBA socket: {e}")
          
async def terminate_process(proc, is_async):
  if proc and proc.poll() is None:
      log.info("Terminating mGBA process...")
      proc.terminate()
      try:
        if is_async:
            await asyncio.to_thread(proc.wait, timeout=5)
        else:
            proc.wait(timeout=5)
            
        log.info("mGBA process terminated.")
      except subprocess.TimeoutExpired:
         log.warning("mGBA process did not terminate gracefully, killing.")
         proc.kill()
         if is_async: 
            try:
               await asyncio.to_thread(proc.wait) 
            except Exception as wait_err:
               log.error(f"Error waiting for mGBA process after kill: {wait_err}")
         else:
            proc.wait() 
               
      except Exception as e:
            log.error(f"Error terminating mGBA process: {e}")


# --- Main Execution Logic ---
async def main_async(auto, max_loops_arg=None, selected_mode=None, persistence=None, run_state=None):
    """Asynchronous main function to run mGBA, WebSocket server, and optionally the LLM loop."""
    global _global_run_state
    _global_run_state = run_state
    
    proc = sock = None
    websocket_task = None
    llm_task = None
    tasks_to_await = []

    try:
        # config.LOAD_SAVESTATE global will be used by start_mgba_with_scripting
        proc, sock = start_mgba_with_scripting()

        if auto:
            log.info("Auto mode enabled. Starting WebSocket server and LLM driver.")
            # Start the WebSocket server (passing the shared 'state' dictionary)
            websocket_task = asyncio.create_task(start_websocket_service(state), name="WebSocketService")
            tasks_to_await.append(websocket_task)

            benchmark = None
            if config.benchmark_path is not None:
                try:
                    benchmark = load(config.benchmark_path)
                    log.info("Loaded custom benchmark from %s → %s", config.benchmark_path, type(benchmark).__name__)
                    max_loops_arg = benchmark.max_loops
                except Exception as e:
                    log.critical("Failed to load benchmark file: %s", e, exc_info=True)
                    sys.exit(1)

            # Start the LLM driver loop (passing the imported broadcast_message function)
            if max_loops_arg is not None:
                send_command(sock, "INPUT_DISPLAY_ON")
                log.info(f"Starting LLM driver loop (max_loops: {max_loops_arg})...")
                llm_task = asyncio.create_task(
                    run_auto_loop(sock, state, broadcast_message, interval=13.0, max_loops=max_loops_arg, benchmark=benchmark, persistence=persistence, run_state=run_state),
                    name="LLMDriverLoop"
                )
            else:
                log.info("Starting LLM driver loop...")
                llm_task = asyncio.create_task(
                    run_auto_loop(sock, state, broadcast_message, interval=13.0, persistence=persistence, run_state=run_state),
                    name="LLMDriverLoop"
                )
            tasks_to_await.append(llm_task)


            # Wait for either task to complete (which usually indicates an error or shutdown)
            if tasks_to_await:
                done, pending = await asyncio.wait(
                    tasks_to_await,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Log results or exceptions from completed tasks
                for task in done:
                    try:
                        result = task.result()
                        log.info(f"Task {task.get_name()} finished unexpectedly with result: {result}")
                    except asyncio.CancelledError:
                         log.info(f"Task {task.get_name()} was cancelled.")
                    except Exception as e:
                        log.error(f"Task {task.get_name()} raised an exception: {e}", exc_info=True)

                # Cancel any remaining pending tasks
                for task in pending:
                    log.info(f"Cancelling pending task: {task.get_name()}")
                    task.cancel()
                # Await the cancellation to complete
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)


        else:
            log.error("main_async should only be called with auto=True. Handling non-auto mode elsewhere.")
            # This path shouldn't be reached with the current __main__ structure.

    except Exception as e:
        log.error(f"An error occurred in main_async: {e}", exc_info=True)
    finally:
        log.info("Cleaning up async resources...")
        # Cancel tasks if they are still running (e.g., if main_async exits due to an error)
        for task in tasks_to_await:
             if task and not task.done():
                 log.info(f"Cancelling task {task.get_name()} during final cleanup.")
                 task.cancel()
        
        pending_cancellations = [t for t in tasks_to_await if t and t.cancelled()] 
        for t in tasks_to_await: 
            if t and not t.done() and t not in pending_cancellations: 
                pending_cancellations.append(t)
        
        if pending_cancellations:
            await asyncio.gather(*pending_cancellations, return_exceptions=True)

        await shutdown_socket(sock, is_async = True)
        await terminate_process(proc, is_async = True)
        log.info("Async cleanup complete.")


if __name__ == '__main__':
    def max_loops_type(value_str):
        """Custom type for argparse to validate max_loops."""
        value, success, message = parse_max_loops_fn(value_str)
        if not success:
            raise argparse.ArgumentTypeError(message)
        log.info(message)
        return value

    parser = argparse.ArgumentParser(description="Run the pyAIAgent.")
    parser.add_argument('--auto', action='store_true', help='Enable auto mode, starting the LLM driver.')
    parser.add_argument('--load_savestate', action='store_true', help='Load savestate 1 on mGBA start.')
    parser.add_argument('--benchmark', type=str, metavar='PATH', help='Path to a benchmark file to run.')
    parser.add_argument('--max_loops', type=max_loops_type, metavar='N', help='Maximum number of loops for the LLM driver to run.')

    args = parser.parse_args()

    # Select LLM mode first (before any mGBA startup)
    from client_setup import parse_mode_arg, MODES
    from llmdriver import set_current_mode
    selected_mode = parse_mode_arg(MODES, default_mode="ZAI")

    # Set the mode in llmdriver
    set_current_mode(selected_mode)

    # Set global config based on parsed arguments
    if args.load_savestate:
        config.LOAD_SAVESTATE = True
        log.info("Command line argument: --load_savestate detected. config.LOAD_SAVESTATE set to True.")
    if args.benchmark:
        config.benchmark_path = args.benchmark

    if args.auto:
        # Initialize run persistence
        persistence = RunPersistence()
        _global_persistence = persistence
        
        # Detect save state and get/create run
        save_type, save_path = auto_detect_savestate()
        save_exists = save_type is not None
        run_state = persistence.get_or_create_run(save_state_exists=save_exists, save_state_path=save_path)
        
        # Initialize shared state from persisted run state
        if run_state.action_count > 0:
            state['actions'] = run_state.action_count
            state['tokensUsed'] = run_state.tokens_used
            state['goals'] = run_state.goals
            state['otherGoals'] = run_state.other_goals
            log.info(f"📊 Restored state: {run_state.action_count} actions, {run_state.tokens_used} tokens")
        
        try:
            asyncio.run(main_async(auto=True, max_loops_arg=args.max_loops, selected_mode=selected_mode, persistence=persistence, run_state=run_state))
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt received, stopping async tasks...")
            # Graceful save on Ctrl+C
            graceful_save_and_exit(_global_socket)
        except Exception as e:
            log.critical(f"Critical error in async execution: {e}", exc_info=True)
        finally:
            log.info("--- Async run finished ---")
    else:
        # --- Synchronous/Interactive Mode ---
        log.info("Interactive mode enabled. WebSocket server and LLM driver will NOT run.")
        proc = sock = None
        try:
            # config.LOAD_SAVESTATE is respected by start_mgba_with_scripting
            proc, sock = start_mgba_with_scripting()
            interactive_console(sock)
        except KeyboardInterrupt:
             log.info("KeyboardInterrupt received, stopping interactive console...")
        except SystemExit:
             log.info("SystemExit called, likely during mGBA startup. Exiting.")
        except Exception as e:
            log.critical(f"Critical error in synchronous execution: {e}", exc_info=True)
        finally:
            log.info("Cleaning up synchronous resources...")
            # Use asyncio.run for these async cleanup functions even in sync mode
            asyncio.run(shutdown_socket(sock, is_async=False))
            asyncio.run(terminate_process(proc, is_async=False))
            log.info("--- Interactive run finished ---")
            
            

