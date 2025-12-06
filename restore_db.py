import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = "pokemon_runs.db"
SAVE_PATH = "roms/red-patched.ss1"

def compute_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]

def restore_db():
    # 1. Delete empty DB if exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Deleted empty {DB_PATH}")

    # 2. Init DB Schema
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP NOT NULL,
        last_active TIMESTAMP NOT NULL,
        save_state_hash TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS run_state (
        run_id INTEGER PRIMARY KEY,
        action_count INTEGER DEFAULT 0,
        tokens_used INTEGER DEFAULT 0,
        elapsed_seconds REAL DEFAULT 0.0,
        goals_json TEXT DEFAULT '{}',
        other_goals TEXT DEFAULT '',
        chat_history_json TEXT DEFAULT '[]',
        latest_memory TEXT DEFAULT '',
        recent_actions_json TEXT DEFAULT '[]',
        cycle_count INTEGER DEFAULT 0,
        FOREIGN KEY(run_id) REFERENCES runs(id)
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS action_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        timestamp TIMESTAMP NOT NULL,
        action TEXT,
        screenshot_base64 TEXT,
        llm_analysis TEXT,
        vision_analysis TEXT,
        position_json TEXT,
        map_name TEXT,
        FOREIGN KEY(run_id) REFERENCES runs(id)
    )""")
    
    # 3. Insert Run #1
    save_hash = compute_hash(SAVE_PATH)
    print(f"Save Hash: {save_hash}")
    
    now = datetime.now()
    c.execute("INSERT INTO runs (created_at, last_active, save_state_hash) VALUES (?, ?, ?)",
              (now, now, save_hash))
    run_id = c.lastrowid
    print(f"Created Run #{run_id}")
    
    # 4. Insert State (Restoring Cycle 20)
    c.execute("""INSERT INTO run_state (run_id, action_count, cycle_count) 
                 VALUES (?, ?, ?)""", (run_id, 20, 20))
    print("Restored counters: Action=20, Cycle=20")
    
    conn.commit()
    conn.close()
    print("✅ Database restored successfully!")

if __name__ == "__main__":
    restore_db()
