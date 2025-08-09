#!/usr/bin/env python3
"""
Interactive database query tool for the trading system
"""

import sqlite3
import sys
from pathlib import Path
from tabulate import tabulate

def query_database():
    """Interactive database query tool"""
    db_path = Path('data/trading_data.db')
    
    if not db_path.exists():
        print("❌ Database file not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        cursor = conn.cursor()
        
        print("🔍 Interactive Trading Database Query Tool")
        print("=" * 50)
        print("Available tables: orders, trades, positions, market_data, daily_performance, strategy_performance, risk_events")
        print("Type 'quit' to exit")
        print()
        
        # Some predefined useful queries
        quick_queries = {
            '1': ("Show all tables", "SELECT name FROM sqlite_master WHERE type='table'"),
            '2': ("Count records in all tables", """
                SELECT 
                    'orders' as table_name, COUNT(*) as count FROM orders
                UNION ALL SELECT 'trades', COUNT(*) FROM trades
                UNION ALL SELECT 'positions', COUNT(*) FROM positions  
                UNION ALL SELECT 'market_data', COUNT(*) FROM market_data
                UNION ALL SELECT 'daily_performance', COUNT(*) FROM daily_performance
                UNION ALL SELECT 'strategy_performance', COUNT(*) FROM strategy_performance
                UNION ALL SELECT 'risk_events', COUNT(*) FROM risk_events
            """),
            '3': ("Recent orders (if any)", "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10"),
            '4': ("Recent trades (if any)", "SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10"),
            '5': ("Current positions (if any)", "SELECT * FROM positions ORDER BY updated_at DESC"),
            '6': ("Today's performance (if any)", "SELECT * FROM daily_performance WHERE date = date('now')"),
        }
        
        while True:
            print("\n🚀 Quick Queries:")
            for key, (desc, _) in quick_queries.items():
                print(f"  {key}. {desc}")
            print("  Or type your own SQL query:")
            
            user_input = input("\n> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                # Check if it's a quick query
                if user_input in quick_queries:
                    query = quick_queries[user_input][1]
                    print(f"\nExecuting: {quick_queries[user_input][0]}")
                else:
                    query = user_input
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                if results:
                    # Convert sqlite3.Row objects to dictionaries for better display
                    rows = [dict(row) for row in results]
                    print(f"\n📊 Results ({len(results)} rows):")
                    print(tabulate(rows, headers="keys", tablefmt="grid"))
                else:
                    print("\n📭 No results found.")
                    
            except sqlite3.Error as e:
                print(f"❌ SQL Error: {e}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        conn.close()
        print("\n👋 Goodbye!")
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    # Check if tabulate is available, if not provide fallback
    try:
        from tabulate import tabulate
    except ImportError:
        print("📦 Installing tabulate for better table formatting...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tabulate"])
        from tabulate import tabulate
    
    query_database()
