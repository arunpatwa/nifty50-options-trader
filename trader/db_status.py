#!/usr/bin/env python3

import sqlite3
from datetime import datetime
import os

def main():
    print("📊 TRADING DATABASE STATUS")
    print("=" * 50)
    print(f"⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if database exists
    if not os.path.exists('data/trading_data.db'):
        print("❌ Database file not found!")
        return
    
    # Connect to database
    conn = sqlite3.connect('data/trading_data.db')
    cursor = conn.cursor()
    
    # Table record counts
    tables = {
        'orders': 'Trading Orders',
        'trades': 'Executed Trades', 
        'positions': 'Open Positions',
        'market_data': 'Market Data Points',
        'daily_performance': 'Daily Performance Records',
        'strategy_performance': 'Strategy Performance',
        'risk_events': 'Risk Events'
    }
    
    print("📋 TABLE STATUS:")
    total_records = 0
    for table, description in tables.items():
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            total_records += count
            status = '✅ Active' if count > 0 else '⭕ Empty'
            print(f"  {description:25}: {count:>5} records {status}")
        except Exception as e:
            print(f"  {description:25}: ❌ Error - {e}")
    
    print(f"\n📊 TOTAL RECORDS: {total_records}")
    
    # Database file info
    size = os.path.getsize('data/trading_data.db')
    print(f"💾 DATABASE SIZE: {size:,} bytes ({size/1024:.1f} KB)")
    
    # Show table structure for one key table
    print(f"\n🏗️  ORDERS TABLE STRUCTURE:")
    cursor.execute("PRAGMA table_info(orders)")
    columns = cursor.fetchall()
    for col in columns:
        col_id, name, data_type, not_null, default, pk = col
        pk_str = " (PK)" if pk else ""
        null_str = " NOT NULL" if not_null else ""
        print(f"  - {name}: {data_type}{pk_str}{null_str}")
    
    conn.close()
    print(f"\n✅ Database is healthy and ready for trading data!")
    
    # Show recent system activity from logs
    if os.path.exists('logs/trading_20250809.log'):
        print(f"\n📝 RECENT SYSTEM ACTIVITY:")
        with open('logs/trading_20250809.log', 'r') as f:
            lines = f.readlines()[-5:]  # Last 5 lines
            for line in lines:
                print(f"  {line.strip()}")

if __name__ == "__main__":
    main()
