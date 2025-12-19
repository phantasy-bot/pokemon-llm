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
import subprocess

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from pyAIAgent.utils.socket_utils import _flush_socket, readrange
from pyAIAgent.game.state import get_rom_path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("mem_inspector")

# Constants
HOST = "127.0.0.1"
PORT = 2061


def start_mgba():
    """Start mGBA process with Lua script."""
    # Force string type to satisfy linter
    rom_path = str(get_rom_path() or "roms/red.gb")

    if not os.path.exists(rom_path):
        log.error(f"ROM file not found: {rom_path}")
        return None

    if not os.path.exists(config.MGBA_EXE):
        log.error(f"mGBA executable not found: {config.MGBA_EXE}")
        return None

    if not os.path.exists(config.LUA_SCRIPT):
        log.error(f"Lua script not found: {config.LUA_SCRIPT}")
        return None

    cmd = [config.MGBA_EXE, "--script", config.LUA_SCRIPT, rom_path]
    log.info(f"🚀 Launching mGBA: {' '.join(cmd)}")

    try:
        # Redirect stdout/stderr to devnull to keep terminal clean
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return proc
    except Exception as e:
        log.error(f"Error starting mGBA: {e}")
        return None


def connect_to_mgba(retries=5):
    """Attempt to connect to mGBA socket with retries."""
    log.info(f"Connecting to mGBA at {HOST}:{PORT}...")

    for i in range(retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            sock.settimeout(2.0)
            return sock
        except ConnectionRefusedError:
            if i < retries - 1:
                time.sleep(1)
                continue
            return None
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

    # Try connecting first
    sock = connect_to_mgba(retries=1)

    proc = None
    if not sock:
        print("\n❌ Could not connect to existing mGBA instance.")
        choice = input("👉 Launch mGBA automatically? (y/n) > ").strip().lower()
        if choice == "y":
            proc = start_mgba()
            if proc:
                print("⏳ Waiting for mGBA to start...")
                time.sleep(3)
                sock = connect_to_mgba(retries=10)

    if not sock:
        print("❌ Failed to connect. Exiting.")
        if proc:
            proc.terminate()
        sys.exit(1)

    print("\n✅ Connected to mGBA!")
    print("\nINSTRUCTIONS:")
    print("1. Navigate the game manually to the screen you want to inspect.")
    print("   (e.g., The Rival Name selection menu)")
    print("2. Press ENTER in this terminal to capture the current state.")
    print("3. Type 'q' and ENTER to quit.")

    try:
        while True:
            cmd = input("\n[Press ENTER to read state, 'q' to quit] > ").strip().lower()
            if cmd == "q":
                break

            print_cursor_state(sock)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.error(f"Error: {e}")
    finally:
        if sock:
            sock.close()
        if proc:
            print("🛑 Shutting down mGBA...")
            proc.terminate()
    print("\nGoodbye!")


if __name__ == "__main__":
    main()
