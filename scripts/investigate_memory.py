#!/usr/bin/env python3
"""
Interactive Memory Inspector for Pokemon Red (mGBA)
===================================================

This script helps debug game state detection issues by allowing real-time
inspection of memory values directly from the running emulator.

Usage:
    python scripts/investigate_memory.py

It will attempt to connect to a running mGBA instance.
"""

import sys
import os
import time
import socket
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyAIAgent.utils.socket_utils import _flush_socket, readrange

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("mem_inspector")

# Constants
HOST = "127.0.0.1"
PORT = 2061


def connect_to_mgba():
    """Attempt to connect to mGBA socket."""
    log.info(f"Connecting to mGBA at {HOST}:{PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        sock.settimeout(2.0)
        return sock
    except ConnectionRefusedError:
        log.error("❌ Could not connect to mGBA!")
        log.info("\nPlease ensure mGBA is running and the scripting socket is enabled.")
        log.info("If you haven't started mGBA yet, please run:")
        log.info("  ./start_agent.sh (and stop the agent script if it's running)")
        return None


def print_cursor_state(sock):
    """Read and print the current cursor and menu state."""
    _flush_socket(sock)

    # Read CC24-CC28 (5 bytes)
    # CC24: Cursor Y
    # CC25: Cursor X
    # CC26: Selected Item Index (0-based)
    # CC27: Top Item Index (scroll position)
    # CC28: Max Item Index (Menu Size - 1)

    try:
        data = readrange(sock, "0xCC24", "5")
        if not data:
            log.error("Failed to read memory.")
            return

        cursor_y = data[0]
        cursor_x = data[1]
        selected = data[2]
        top_item = data[3]
        last_item = data[4]

        menu_item_count = last_item + 1

        print("\n📊 MENU & CURSOR STATE (0xCC24 - 0xCC28)")
        print(f"----------------------------------------")
        print(f"Cursor Y (0xCC24):      {cursor_y} (Row on screen)")
        print(f"Cursor X (0xCC25):      {cursor_x} (Column on screen)")
        print(f"Selected Item (0xCC26): {selected} (Index)")
        print(f"Top Item (0xCC27):      {top_item} (Scroll offset)")
        print(f"Last Item (0xCC28):     {last_item} (Total Items = {menu_item_count})")
        print(f"----------------------------------------")

        # Preset Menu Heuristic Check
        is_preset = (3 <= last_item <= 5) and cursor_y < 3
        print(f"Preset Menu Detection:  {'✅ YES' if is_preset else '❌ NO'}")
        print(f"  Condition: (3 <= last_item <= 5) AND (cursor_y < 3)")

    except Exception as e:
        log.error(f"Error reading memory: {e}")


def main():
    print("\n🔍 mGBA Memory Investigator 🔍")
    print("==============================")

    sock = connect_to_mgba()
    if not sock:
        sys.exit(1)

    print("\n✅ Connected to mGBA!")
    print("\nINSTRUCTIONS:")
    print("1. Navigate the game manually to the screen you want to inspect.")
    print("   (e.g., The Rival Name selection menu)")
    print("2. Press ENTER in this terminal to capture the current state.")
    print("3. Type 'q' and ENTER to quit.")

    while True:
        try:
            cmd = input("\n[Press ENTER to read state, 'q' to quit] > ").strip().lower()
            if cmd == "q":
                break

            print_cursor_state(sock)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Error: {e}")
            # Try to reconnect
            sock.close()
            sock = connect_to_mgba()
            if not sock:
                break

    if sock:
        sock.close()
    print("\nGoodbye!")


if __name__ == "__main__":
    main()
