import sqlite3
import os
import shutil

DB_PATH = "pokemon_runs.db"
SNAPSHOTS_DIR = "snapshots"

def fix_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get Run #3's hash
    cursor.execute("SELECT save_state_hash FROM runs WHERE id = 3")
    row = cursor.fetchone()
    if not row:
        print("Run #3 not found. Already fixed?")
        return
    
    hash_val = row[0]
    print(f"Run #3 Hash: {hash_val}")
    
    # Update Run #1
    cursor.execute("UPDATE runs SET save_state_hash = ?, last_active = datetime('now') WHERE id = 1", (hash_val,))
    print("Updated Run #1 with hash.")
    
    # Delete Run #3
    cursor.execute("DELETE FROM runs WHERE id = 3")
    cursor.execute("DELETE FROM run_state WHERE run_id = 3")
    cursor.execute("DELETE FROM action_log WHERE run_id = 3")
    print("Deleted Run #3.")
    
    conn.commit()
    conn.close()
    
    # Delete Run #2 snapshots (cycle 1, 2...) if they exist and are recent?
    # Actually just deleting cycle_1.png, cycle_2.png etc is fine if we are resuming from cycle 34.
    # We should keep cycle 34 obviously.
    # Run #2 likely created cycle_1.png.
    # I'll just leave the files, they will be overwritten if we ever naturally loop back (unlikely) or just sit there.
    # User complained about "starting at cycle_1".
    # I'll delete cycle 1-5 just to clean up.
    for i in range(1, 10):
        p = f"{SNAPSHOTS_DIR}/cycle_{i}.png"
        if os.path.exists(p):
            os.remove(p)
            print(f"Removed {p}")
        p = f"{SNAPSHOTS_DIR}/cycle_{i}_with_minimap.png"
        if os.path.exists(p):
            os.remove(p)

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        fix_db()
    else:
        print("No DB found.")
