"""
Database manager for storing trading data, orders, and performance metrics
"""

import asyncio
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from pathlib import Path
import logging

from src.utils.logger import TradingLogger

class DatabaseManager:
    """Database manager for trading data storage"""
    
    def __init__(self, db_path: str = "data/trading_data.db"):
        self.logger = TradingLogger(__name__)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.connection = None
    
    async def initialize(self) -> bool:
        """
        Initialize database and create tables
        
        Returns:
            True if initialization successful
        """
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            
            await self._create_tables()
            
            self.logger.logger.info(f"Database initialized: {self.db_path}")
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def _create_tables(self):
        """Create all required database tables"""
        cursor = self.connection.cursor()
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,  -- BUY/SELL
                order_type TEXT NOT NULL,  -- MARKET/LIMIT
                quantity INTEGER NOT NULL,
                price REAL,
                status TEXT NOT NULL,  -- PENDING/OPEN/FILLED/CANCELLED
                strategy TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filled_price REAL,
                filled_quantity INTEGER DEFAULT 0,
                metadata TEXT  -- JSON string for additional data
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                strategy TEXT,
                pnl REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                order_id TEXT,
                metadata TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )
        """)
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                market_price REAL,
                pnl REAL DEFAULT 0,
                unrealized_pnl REAL DEFAULT 0,
                strategy TEXT,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Market data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bid REAL,
                ask REAL,
                open_interest INTEGER,
                metadata TEXT
            )
        """)
        
        # Daily performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                total_pnl REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                unrealized_pnl REAL DEFAULT 0,
                trades_count INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                portfolio_value REAL DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Strategy performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                date DATE,
                pnl REAL DEFAULT 0,
                trades_count INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_win REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                metadata TEXT,
                UNIQUE(strategy_name, date)
            )
        """)
        
        # Risk events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,  -- POSITION_LIMIT/LOSS_LIMIT/VOLATILITY etc.
                symbol TEXT,
                description TEXT,
                severity TEXT,  -- LOW/MEDIUM/HIGH/CRITICAL
                action_taken TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        self.connection.commit()
        self.logger.logger.info("Database tables created/verified")
    
    async def insert_order(self, order_data: Dict[str, Any]) -> bool:
        """
        Insert order record
        
        Args:
            order_data: Order information
            
        Returns:
            True if insertion successful
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO orders (
                    order_id, symbol, side, order_type, quantity, price, 
                    status, strategy, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data.get('order_id'),
                order_data.get('symbol'),
                order_data.get('side'),
                order_data.get('order_type'),
                order_data.get('quantity'),
                order_data.get('price'),
                order_data.get('status', 'PENDING'),
                order_data.get('strategy'),
                json.dumps(order_data.get('metadata', {}))
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error inserting order: {e}")
            return False
    
    async def update_order(self, order_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update order record
        
        Args:
            order_id: Order ID to update
            update_data: Updated fields
            
        Returns:
            True if update successful
        """
        try:
            cursor = self.connection.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for field, value in update_data.items():
                if field == 'metadata':
                    value = json.dumps(value)
                set_clauses.append(f"{field} = ?")
                values.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(order_id)
            
            query = f"UPDATE orders SET {', '.join(set_clauses)} WHERE order_id = ?"
            cursor.execute(query, values)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error updating order {order_id}: {e}")
            return False
    
    async def insert_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Insert trade record
        
        Args:
            trade_data: Trade information
            
        Returns:
            True if insertion successful
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO trades (
                    trade_id, symbol, side, quantity, price, value,
                    strategy, pnl, commission, order_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('trade_id'),
                trade_data.get('symbol'),
                trade_data.get('side'),
                trade_data.get('quantity'),
                trade_data.get('price'),
                trade_data.get('value'),
                trade_data.get('strategy'),
                trade_data.get('pnl', 0),
                trade_data.get('commission', 0),
                trade_data.get('order_id'),
                json.dumps(trade_data.get('metadata', {}))
            ))
            
            self.connection.commit()
            self.logger.log_trade(trade_data)
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error inserting trade: {e}")
            return False
    
    async def upsert_position(self, position_data: Dict[str, Any]) -> bool:
        """
        Insert or update position record
        
        Args:
            position_data: Position information
            
        Returns:
            True if operation successful
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO positions (
                    symbol, quantity, avg_price, market_price, pnl,
                    unrealized_pnl, strategy, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data.get('symbol'),
                position_data.get('quantity'),
                position_data.get('avg_price'),
                position_data.get('market_price'),
                position_data.get('pnl', 0),
                position_data.get('unrealized_pnl', 0),
                position_data.get('strategy'),
                json.dumps(position_data.get('metadata', {}))
            ))
            
            self.connection.commit()
            self.logger.log_position_update(position_data)
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error upserting position: {e}")
            return False
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all current positions
        
        Returns:
            List of position records
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM positions WHERE quantity != 0")
            
            positions = []
            for row in cursor.fetchall():
                position = dict(row)
                if position['metadata']:
                    position['metadata'] = json.loads(position['metadata'])
                positions.append(position)
            
            return positions
            
        except Exception as e:
            self.logger.logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_orders(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get orders with optional status filter
        
        Args:
            status: Optional status filter
            limit: Maximum number of records
            
        Returns:
            List of order records
        """
        try:
            cursor = self.connection.cursor()
            
            if status:
                cursor.execute(
                    "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            
            orders = []
            for row in cursor.fetchall():
                order = dict(row)
                if order['metadata']:
                    order['metadata'] = json.loads(order['metadata'])
                orders.append(order)
            
            return orders
            
        except Exception as e:
            self.logger.logger.error(f"Error getting orders: {e}")
            return []
    
    async def get_daily_pnl(self, date_str: str = None) -> Dict[str, Any]:
        """
        Get daily PnL for a specific date
        
        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Daily PnL data
        """
        try:
            if not date_str:
                date_str = date.today().strftime('%Y-%m-%d')
            
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM daily_performance WHERE date = ?",
                (date_str,)
            )
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            else:
                return {
                    'date': date_str,
                    'total_pnl': 0,
                    'realized_pnl': 0,
                    'unrealized_pnl': 0,
                    'trades_count': 0
                }
                
        except Exception as e:
            self.logger.logger.error(f"Error getting daily PnL: {e}")
            return {}
    
    async def update_daily_performance(self, date_str: str, performance_data: Dict[str, Any]) -> bool:
        """
        Update daily performance record
        
        Args:
            date_str: Date string
            performance_data: Performance metrics
            
        Returns:
            True if update successful
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO daily_performance (
                    date, total_pnl, realized_pnl, unrealized_pnl,
                    trades_count, winning_trades, losing_trades,
                    max_drawdown, portfolio_value, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str,
                performance_data.get('total_pnl', 0),
                performance_data.get('realized_pnl', 0),
                performance_data.get('unrealized_pnl', 0),
                performance_data.get('trades_count', 0),
                performance_data.get('winning_trades', 0),
                performance_data.get('losing_trades', 0),
                performance_data.get('max_drawdown', 0),
                performance_data.get('portfolio_value', 0),
                json.dumps(performance_data.get('metadata', {}))
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error updating daily performance: {e}")
            return False
    
    async def log_risk_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Log risk management event
        
        Args:
            event_data: Risk event information
            
        Returns:
            True if logging successful
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO risk_events (
                    event_type, symbol, description, severity,
                    action_taken, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_data.get('event_type'),
                event_data.get('symbol'),
                event_data.get('description'),
                event_data.get('severity', 'MEDIUM'),
                event_data.get('action_taken'),
                json.dumps(event_data.get('metadata', {}))
            ))
            
            self.connection.commit()
            self.logger.log_risk_event(event_data)
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error logging risk event: {e}")
            return False
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Clean up old market data to prevent database bloat
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        try:
            cursor = self.connection.cursor()
            
            # Clean up old market data
            cursor.execute("""
                DELETE FROM market_data 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days_to_keep))
            
            deleted_count = cursor.rowcount
            self.connection.commit()
            
            if deleted_count > 0:
                self.logger.logger.info(f"Cleaned up {deleted_count} old market data records")
                
        except Exception as e:
            self.logger.logger.error(f"Error cleaning up old data: {e}")
    
    async def close(self):
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                self.logger.logger.info("Database connection closed")
                
        except Exception as e:
            self.logger.logger.error(f"Error closing database: {e}")
