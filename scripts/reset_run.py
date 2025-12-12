import os
import shutil
import sys
# Remove dependencies to allowing running in any env
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_rom_path_local():
    """Standalone version of get_rom_path to avoid imports."""
    # Check env var first
    if "POKEMON_ROM" in os.environ:
        return os.environ["POKEMON_ROM"]
    
    # Check common locations
    candidates = [
        "roms/red-patched.gb",
        "roms/Pokemon - Red Version (UE) [S][!].gb",
        "roms/red.gb"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
            
    return "roms/red-patched.gb" # Default fallback

def reset_all():
    print("\n🔴  DANGER: This script will DELETE all Pokemon Run Data (Database, Save States, Memories, Snapshots).")
    print("    This action cannot be undone.\n")
    
    rom_path = get_rom_path_local()

    rom_dir = os.path.dirname(rom_path)
    rom_name = os.path.splitext(os.path.basename(rom_path))[0]
    
    files_to_delete = [
        "pokemon_runs.db",
        # Data directory files
        "data/pokemon_memories.json",
        "data/coordinate_history.json",
        "data/exploration_data.json",
        "data/game_goals.json",
        os.path.join(rom_dir, f"{rom_name}.ss1"),
        os.path.join(rom_dir, f"{rom_name}-backup.ss1"),
        # Also clean up minimap cache files from root
        "minimap.png",
        "latest.png",
        "latest_with_minimap.png"
    ]
    
    dirs_to_clean = [
        "snapshots"
    ]
    
    # List what will be deleted
    found_items = []
    for f in files_to_delete:
        if os.path.exists(f):
            found_items.append(f"[FILE] {f}")
            
    for d in dirs_to_clean:
        if os.path.exists(d) and os.listdir(d):
             count = len(os.listdir(d))
             found_items.append(f"[DIR ] {d}/ ({count} files)")
             
    if not found_items:
        print("✨ No data files found. Environment is already clean.")
        return

    print("The following items will be DELETED:")
    for item in found_items:
        print(f"  {item}")

    confirm = input("\nType 'delete' to confirm: ").strip().lower()
    if confirm != 'delete':
        print("Aborted.")
        return

    print("\nStarting reset...")
    for f in files_to_delete:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"  ✅ Deleted {f}")
            except Exception as e:
                print(f"  ❌ Failed to delete {f}: {e}")
                
    for d in dirs_to_clean:
        if os.path.exists(d):
            try:
                # Remove all files in dir but keep dir
                for filename in os.listdir(d):
                    file_path = os.path.join(d, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")
                print(f"  ✅ Cleaned {d}/")
            except Exception as e:
                print(f"  ❌ Failed to clean {d}: {e}")

    print("\n✨ Reset Complete! You can now start a fresh run with 'python run.py --auto'")

if __name__ == "__main__":
    reset_all()
