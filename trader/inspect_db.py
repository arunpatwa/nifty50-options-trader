#!/usr/bin/env python3
"""
Database inspection script for the trading system
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def inspect_database():
    """Inspect the trading database"""
    db_path = Path('data/trading_data.db')
    
    if not db_path.exists():
        print("❌ Database file not found!")
        return
    
    print("🔍 Inspecting Trading Database")
    print("=" * 50)
    print(f"📁 Database: {db_path}")
    print(f"📏 Size: {db_path.stat().st_size:,} bytes")
    print(f"⏰ Modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}")
    print()
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"📊 Found {len(tables)} tables:")
        print("-" * 30)
        
        for table_name, in tables:
            print(f"\n📋 Table: {table_name}")
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print(f"   Columns ({len(columns)}):")
            for col in columns:
                col_id, name, data_type, not_null, default, pk = col
                pk_str = " (PRIMARY KEY)" if pk else ""
                null_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default}" if default else ""
                print(f"     - {name}: {data_type}{pk_str}{null_str}{default_str}")
            
            # Count records
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   Records: {count}")
            
            # Show sample data if any
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]
                
                print(f"   Sample data:")
                for i, row in enumerate(rows, 1):
                    print(f"     Record {i}:")
                    for col_name, value in zip(col_names, row):
                        print(f"       {col_name}: {value}")
                
                if count > 3:
                    print(f"       ... and {count - 3} more records")
        
        conn.close()
        print("\n✅ Database inspection complete!")
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")

if __name__ == "__main__":
    inspect_database()
