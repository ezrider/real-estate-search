#!/usr/bin/env python3
"""
Database initialization script for Real Estate Tracker.

Creates the SQLite database with schema and pre-populates Victoria neighborhoods.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Victoria neighborhoods to pre-populate
VICTORIA_NEIGHBORHOODS = [
    ("Downtown", "Victoria", "Central business district with high-rise condos, shopping, and entertainment"),
    ("Harris Green", "Victoria", "Dense residential area just north of downtown, highly walkable"),
    ("Chinatown", "Victoria", "Historic district with character buildings and mixed-use developments"),
    ("James Bay", "Victoria", "Waterfront neighborhood near Beacon Hill Park and the Inner Harbour"),
    ("Fairfield", "Victoria", "Residential neighborhood with Cook Street Village, family-friendly"),
    ("Fernwood", "Victoria", "Arts and culture district with character homes and community vibe"),
    ("Victoria West", "Victoria", "Formerly industrial area now converted to modern waterfront condos"),
    ("Songhees", "Victoria", "Upscale waterfront condo community with marina access"),
    ("Esquimalt", "Victoria", "West of downtown, more affordable options, naval base nearby"),
    ("Oak Bay", "Victoria", "Upscale residential area, distinct municipality with village center"),
    ("Saanich East", "Victoria", "Suburban area east of Victoria, family-oriented with good schools"),
    ("Saanich West", "Victoria", "Suburban area near University of Victoria, student housing"),
    ("View Royal", "Victoria", "Westshore area with newer developments and nature access"),
    ("Langford", "Victoria", "Fast-growing Westshore community with new condo developments"),
    ("Colwood", "Victoria", "Westshore area near Royal Roads University, mix of old and new"),
]


def create_database(db_path: str) -> sqlite3.Connection:
    """Create the database and return a connection."""
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def execute_schema(conn: sqlite3.Connection, schema_path: str) -> None:
    """Execute the schema SQL file."""
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    conn.executescript(schema)
    conn.commit()
    print(f"✓ Executed schema from {schema_path}")


def populate_neighborhoods(conn: sqlite3.Connection) -> int:
    """Pre-populate Victoria neighborhoods."""
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for name, city, description in VICTORIA_NEIGHBORHOODS:
        try:
            cursor.execute(
                "INSERT INTO neighborhood (name, city, description) VALUES (?, ?, ?)",
                (name, city, description)
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # Neighborhood already exists
            skipped += 1
    
    conn.commit()
    print(f"✓ Populated neighborhoods: {inserted} inserted, {skipped} already existed")
    return inserted


def create_photo_directories(base_dir: str) -> None:
    """Create the photo storage directory structure."""
    photos_dir = Path(base_dir) / "photos"
    
    subdirs = [
        "listings",
        "historical_sales",
    ]
    
    for subdir in subdirs:
        (photos_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    # Create .gitkeep files so directories are tracked
    for subdir in subdirs:
        gitkeep = photos_dir / subdir / ".gitkeep"
        gitkeep.touch(exist_ok=True)
    
    print(f"✓ Created photo directories at {photos_dir}")


def verify_database(conn: sqlite3.Connection) -> dict:
    """Verify database was created correctly."""
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Count neighborhoods
    cursor.execute("SELECT COUNT(*) FROM neighborhood")
    neighborhood_count = cursor.fetchone()[0]
    
    # Count views
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views = [row[0] for row in cursor.fetchall()]
    
    return {
        "tables": tables,
        "views": views,
        "neighborhood_count": neighborhood_count,
    }


def main():
    """Main entry point."""
    # Default paths
    base_dir = Path(__file__).parent
    db_path = base_dir / "real_estate.db"
    schema_path = base_dir / "schema.sql"
    
    print("=" * 60)
    print("Real Estate Tracker - Database Initialization")
    print("=" * 60)
    print()
    
    # Check if schema file exists
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}")
        sys.exit(1)
    
    # Check if database already exists
    if db_path.exists():
        print(f"Database already exists at {db_path}")
        response = input("Recreate database? This will delete all data. [y/N]: ")
        if response.lower() == 'y':
            os.remove(db_path)
            print("→ Deleted existing database")
        else:
            print("→ Exiting without changes")
            sys.exit(0)
    
    try:
        # Create database
        print(f"→ Creating database at {db_path}")
        conn = create_database(str(db_path))
        
        # Execute schema
        execute_schema(conn, str(schema_path))
        
        # Populate neighborhoods
        populate_neighborhoods(conn)
        
        # Create photo directories
        create_photo_directories(str(base_dir))
        
        # Verify
        stats = verify_database(conn)
        
        print()
        print("=" * 60)
        print("Database created successfully!")
        print("=" * 60)
        print(f"\nTables created: {len(stats['tables'])}")
        for table in stats['tables']:
            print(f"  • {table}")
        print(f"\nViews created: {len(stats['views'])}")
        for view in stats['views']:
            print(f"  • {view}")
        print(f"\nNeighborhoods: {stats['neighborhood_count']}")
        print(f"\nPhoto storage: {base_dir / 'photos'}")
        print()
        
    except sqlite3.Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
