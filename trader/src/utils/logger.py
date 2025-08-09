"""
Logging configuration and utilities for the trading bot
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import sys
from pathlib import Path

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with both file and console handlers
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler with rotation
    log_file = log_dir / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class TradingLogger:
    """Specialized logger for trading operations"""
    
    def __init__(self, name: str):
        self.logger = setup_logger(name)
        self.trade_log_file = Path("logs") / "trades.log"
    
    def log_trade(self, trade_data: dict):
        """Log trade execution details"""
        trade_msg = (
            f"TRADE - Symbol: {trade_data.get('symbol', 'N/A')}, "
            f"Action: {trade_data.get('action', 'N/A')}, "
            f"Quantity: {trade_data.get('quantity', 'N/A')}, "
            f"Price: {trade_data.get('price', 'N/A')}, "
            f"Strategy: {trade_data.get('strategy', 'N/A')}"
        )
        self.logger.info(trade_msg)
        
        # Also log to dedicated trades file
        self._log_to_trades_file(trade_msg)
    
    def log_order(self, order_data: dict):
        """Log order placement details"""
        order_msg = (
            f"ORDER - ID: {order_data.get('order_id', 'N/A')}, "
            f"Symbol: {order_data.get('symbol', 'N/A')}, "
            f"Side: {order_data.get('side', 'N/A')}, "
            f"Quantity: {order_data.get('quantity', 'N/A')}, "
            f"Price: {order_data.get('price', 'N/A')}, "
            f"Status: {order_data.get('status', 'N/A')}"
        )
        self.logger.info(order_msg)
    
    def log_position_update(self, position_data: dict):
        """Log position changes"""
        position_msg = (
            f"POSITION - Symbol: {position_data.get('symbol', 'N/A')}, "
            f"Quantity: {position_data.get('quantity', 'N/A')}, "
            f"Avg Price: {position_data.get('avg_price', 'N/A')}, "
            f"PnL: {position_data.get('pnl', 'N/A')}"
        )
        self.logger.info(position_msg)
    
    def log_risk_event(self, risk_data: dict):
        """Log risk management events"""
        risk_msg = (
            f"RISK - Event: {risk_data.get('event', 'N/A')}, "
            f"Symbol: {risk_data.get('symbol', 'N/A')}, "
            f"Current Risk: {risk_data.get('current_risk', 'N/A')}, "
            f"Max Risk: {risk_data.get('max_risk', 'N/A')}, "
            f"Action: {risk_data.get('action', 'N/A')}"
        )
        self.logger.warning(risk_msg)
    
    def _log_to_trades_file(self, message: str):
        """Write trade log to dedicated file"""
        try:
            with open(self.trade_log_file, 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp} - {message}\n")
        except Exception as e:
            self.logger.error(f"Failed to write to trades log: {e}")

# Global logger instance
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return setup_logger(name)
