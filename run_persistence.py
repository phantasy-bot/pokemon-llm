"""
Run Persistence System for Pokemon LLM Agent

Provides SQLite-backed persistence for run state including:
- Token counts, action counts, elapsed time
- Goals (primary, secondary, tertiary)
- Chat history for LLM context
- Per-action logging with screenshots and analysis

Run detection: Uses save state file hash to determine if continuing 
an existing run or starting fresh.
"""

import sqlite3
import json
import hashlib
import os
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

log = logging.getLogger("run_persistence")

# Database file location
DB_PATH = "pokemon_runs.db"


@dataclass
class RunState:
    """Represents the persisted state of a run."""
    run_id: int
    created_at: str
    last_active: str
    save_state_hash: Optional[str]
    action_count: int = 0
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    goals: Dict[str, str] = field(default_factory=lambda: {
        "primary": "Initializing...",
        "secondary": "Initializing...",
        "tertiary": "Initializing..."
    })
    other_goals: str = "Initializing..."
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    latest_memory: str = ""
    recent_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: dict, chat_history: List = None, recent_actions: List = None) -> 'RunState':
        """Create RunState from database row."""
        goals = {"primary": "Initializing...", "secondary": "Initializing...", "tertiary": "Initializing..."}
        if row.get("goals_json"):
            try:
                goals = json.loads(row["goals_json"])
            except:
                pass
        
        return cls(
            run_id=row["run_id"],
            created_at=row.get("created_at", ""),
            last_active=row.get("last_active", ""),
            save_state_hash=row.get("save_state_hash"),
            action_count=row.get("action_count", 0) or 0,
            tokens_used=row.get("tokens_used", 0) or 0,
            elapsed_seconds=row.get("elapsed_seconds", 0.0) or 0.0,
            goals=goals,
            other_goals=row.get("other_goals", "") or "",
            chat_history=chat_history or [],
            latest_memory=row.get("latest_memory", "") or "",
            recent_actions=recent_actions or []
        )


class RunPersistence:
    """
    Manages SQLite-based persistence for Pokemon LLM runs.
    
    Usage:
        persistence = RunPersistence()
        run_state = persistence.get_or_create_run(save_state_exists=True, save_state_path="roms/red.ss1")
        
        # During gameplay:
        persistence.save_run_state(run_state)
        persistence.log_action(run_state.run_id, "U;U;A", screenshot_b64, llm_analysis, vision_analysis)
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            
            # Runs table - one row per unique run
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    save_state_hash TEXT
                )
            """)
            
            # Run state table - cumulative state for each run
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_state (
                    run_id INTEGER PRIMARY KEY,
                    action_count INTEGER DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    elapsed_seconds REAL DEFAULT 0.0,
                    goals_json TEXT,
                    other_goals TEXT,
                    chat_history_json TEXT,
                    latest_memory TEXT,
                    recent_actions_json TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
            """)
            
            # Action log table - per-action logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT,
                    screenshot_b64 TEXT,
                    llm_analysis TEXT,
                    vision_analysis TEXT,
                    position_json TEXT,
                    map_name TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_log_run ON action_log(run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_hash ON runs(save_state_hash)")
            
            conn.commit()
            log.info(f"📁 Database initialized: {self.db_path}")
        finally:
            conn.close()
    
    def _hash_save_state(self, save_state_path: str) -> Optional[str]:
        """Generate hash of save state file for run identification."""
        if not save_state_path or not os.path.exists(save_state_path):
            return None
        
        try:
            with open(save_state_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception as e:
            log.warning(f"Could not hash save state: {e}")
            return None
    
    def get_or_create_run(
        self, 
        save_state_exists: bool, 
        save_state_path: Optional[str] = None
    ) -> RunState:
        """
        Get existing run or create new one based on save state.
        
        Logic:
        1. If save state exists, hash it and look for matching run
        2. If found, continue that run
        3. If not found or no save state, create new run
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            save_hash = None
            if save_state_exists and save_state_path:
                save_hash = self._hash_save_state(save_state_path)
                
                if save_hash:
                    # Look for existing run with this save state hash
                    cursor.execute("""
                        SELECT r.id as run_id, r.created_at, r.last_active, r.save_state_hash,
                               s.action_count, s.tokens_used, s.elapsed_seconds,
                               s.goals_json, s.other_goals, s.chat_history_json,
                               s.latest_memory, s.recent_actions_json
                        FROM runs r
                        LEFT JOIN run_state s ON r.id = s.run_id
                        WHERE r.save_state_hash = ?
                        ORDER BY r.last_active DESC
                        LIMIT 1
                    """, (save_hash,))
                    
                    row = cursor.fetchone()
                    if row:
                        # Found existing run - restore it
                        row_dict = dict(row)
                        
                        # Parse chat history
                        chat_history = []
                        if row_dict.get("chat_history_json"):
                            try:
                                chat_history = json.loads(row_dict["chat_history_json"])
                            except:
                                pass
                        
                        # Parse recent actions
                        recent_actions = []
                        if row_dict.get("recent_actions_json"):
                            try:
                                recent_actions = json.loads(row_dict["recent_actions_json"])
                            except:
                                pass
                        
                        # Update last_active
                        cursor.execute(
                            "UPDATE runs SET last_active = ? WHERE id = ?",
                            (now, row_dict["run_id"])
                        )
                        conn.commit()
                        
                        run_state = RunState.from_row(row_dict, chat_history, recent_actions)
                        log.info(f"🔄 Continuing run #{run_state.run_id} (actions: {run_state.action_count}, tokens: {run_state.tokens_used})")
                        return run_state
            
            # Create new run
            cursor.execute(
                "INSERT INTO runs (created_at, last_active, save_state_hash) VALUES (?, ?, ?)",
                (now, now, save_hash)
            )
            run_id = cursor.lastrowid
            
            # Initialize run_state row
            cursor.execute(
                "INSERT INTO run_state (run_id) VALUES (?)",
                (run_id,)
            )
            
            conn.commit()
            
            run_state = RunState(
                run_id=run_id,
                created_at=now,
                last_active=now,
                save_state_hash=save_hash
            )
            log.info(f"🆕 Created new run #{run_id}")
            return run_state
            
        finally:
            conn.close()
    
    def save_run_state(self, run_state: RunState):
        """Save current run state to database."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Update runs table
            cursor.execute(
                "UPDATE runs SET last_active = ?, save_state_hash = ? WHERE id = ?",
                (now, run_state.save_state_hash, run_state.run_id)
            )
            
            # Update run_state table
            cursor.execute("""
                UPDATE run_state SET
                    action_count = ?,
                    tokens_used = ?,
                    elapsed_seconds = ?,
                    goals_json = ?,
                    other_goals = ?,
                    chat_history_json = ?,
                    latest_memory = ?,
                    recent_actions_json = ?
                WHERE run_id = ?
            """, (
                run_state.action_count,
                run_state.tokens_used,
                run_state.elapsed_seconds,
                json.dumps(run_state.goals),
                run_state.other_goals,
                json.dumps(run_state.chat_history[-20:]),  # Keep last 20 messages
                run_state.latest_memory,
                json.dumps(run_state.recent_actions[-50:]),  # Keep last 50 actions
                run_state.run_id
            ))
            
            conn.commit()
            log.debug(f"💾 Saved run state: actions={run_state.action_count}, tokens={run_state.tokens_used}")
            
        finally:
            conn.close()
    
    def log_action(
        self,
        run_id: int,
        action: str,
        screenshot_b64: Optional[str] = None,
        llm_analysis: Optional[str] = None,
        vision_analysis: Optional[str] = None,
        position: Optional[List[int]] = None,
        map_name: Optional[str] = None
    ):
        """Log a single action with associated data."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO action_log 
                (run_id, timestamp, action, screenshot_b64, llm_analysis, vision_analysis, position_json, map_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                datetime.now().isoformat(),
                action,
                screenshot_b64,
                llm_analysis,
                vision_analysis,
                json.dumps(position) if position else None,
                map_name
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_action_count(self, run_id: int) -> int:
        """Get total action count for a run."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT action_count FROM run_state WHERE run_id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            return row["action_count"] if row else 0
        finally:
            conn.close()
    
    def get_recent_actions(self, run_id: int, limit: int = 10) -> List[Dict]:
        """Get recent actions for a run."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT action, map_name, position_json, timestamp
                FROM action_log
                WHERE run_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (run_id, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
        finally:
            conn.close()
    
    def update_save_state_hash(self, run_id: int, save_state_path: str):
        """Update the save state hash after saving."""
        new_hash = self._hash_save_state(save_state_path)
        if new_hash:
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE runs SET save_state_hash = ? WHERE id = ?",
                    (new_hash, run_id)
                )
                conn.commit()
                log.debug(f"Updated save state hash for run #{run_id}")
            finally:
                conn.close()


# Convenience function for testing
def get_run_summary(db_path: str = DB_PATH) -> str:
    """Get a summary of all runs in the database."""
    if not os.path.exists(db_path):
        return "No database found."
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.created_at, r.last_active, 
                   s.action_count, s.tokens_used, s.elapsed_seconds
            FROM runs r
            LEFT JOIN run_state s ON r.id = s.run_id
            ORDER BY r.last_active DESC
        """)
        
        rows = cursor.fetchall()
        if not rows:
            return "No runs recorded."
        
        lines = ["=== Pokemon LLM Runs ==="]
        for row in rows:
            elapsed_mins = (row["elapsed_seconds"] or 0) / 60
            lines.append(
                f"Run #{row['id']}: {row['action_count'] or 0} actions, "
                f"{row['tokens_used'] or 0} tokens, {elapsed_mins:.1f} mins"
            )
        return "\n".join(lines)
    finally:
        conn.close()


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    print(get_run_summary())
