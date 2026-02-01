"""Database connection and session management."""

import sqlite3
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional
from pathlib import Path
from decimal import Decimal

from app.core.config import get_settings

# Register adapter for Decimal
sqlite3.register_adapter(Decimal, lambda d: str(d))
sqlite3.register_converter("DECIMAL", lambda s: Decimal(s.decode()))


class Database:
    """SQLite database wrapper with dict-style rows."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Initialize connection with proper settings."""
        pass  # SQLite doesn't need pooling, connections are cheap
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection as context manager."""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
    
    def _convert_params(self, params: tuple) -> tuple:
        """Convert parameters for SQLite compatibility."""
        converted = []
        for p in params:
            if isinstance(p, Decimal):
                converted.append(float(p))
            else:
                converted.append(p)
        return tuple(converted)
    
    def execute(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Execute a query and return results."""
        params = self._convert_params(params)
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            if fetch_one:
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                return [dict(row) for row in cursor.fetchall()]
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT and return the new row ID."""
        params = self._convert_params(params)
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute UPDATE/DELETE and return affected row count."""
        params = self._convert_params(params)
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute many inserts/updates."""
        params_list = [self._convert_params(p) for p in params_list]
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount


# Global database instance
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        settings = get_settings()
        # Convert relative path to absolute
        db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
        if not db_path.is_absolute():
            db_path = Path(__file__).parent.parent / db_path
        _db_instance = Database(str(db_path.resolve()))
    return _db_instance


def init_db():
    """Initialize database connection on startup."""
    db = get_db()
    
    # Load schema if tables don't exist
    with db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='listing'"
        )
        if not cursor.fetchone():
            # Load schema
            schema_path = Path(__file__).parent.parent.parent.parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    conn.executescript(f.read())
                print(f"✓ Database schema loaded from {schema_path}")
        
        # Test connection
        cursor = conn.execute("SELECT 1")
        cursor.fetchone()
    
    print(f"✓ Database connected: {db.db_path}")
