#!/usr/bin/env python3
"""
Nifty 50 Options Automated Trader
Main application entry point
"""

import asyncio
import signal
import sys
from typing import Dict, Any
import logging

# Import core modules
from src.utils.logger import setup_logger
from src.api.dhan_client import DhanClient
from src.strategies.scalping import ScalpingStrategy
from src.strategies.momentum import MomentumStrategy
from src.risk_management.position_manager import PositionManager
from src.orders.order_manager import OrderManager
from src.data.data_manager import DataManager
from src.data.database import DatabaseManager
from config.settings import settings

class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.running = False
        self.dhan_client = None
        self.data_manager = None
        self.position_manager = None
        self.order_manager = None
        self.strategies = {}
        self.db_manager = None
        
    async def initialize(self) -> bool:
        """Initialize all trading components"""
        try:
            self.logger.info("Initializing Nifty 50 Options Trading Bot...")
            
            # Initialize database
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Initialize Dhan API client
            self.dhan_client = DhanClient()
            if not await self.dhan_client.authenticate():
                self.logger.error("Failed to authenticate with Dhan API")
                return False
            
            # Initialize data manager
            self.data_manager = DataManager(self.dhan_client)
            
            # Initialize position and order managers
            self.position_manager = PositionManager(self.dhan_client)
            self.order_manager = OrderManager(self.dhan_client, self.position_manager)
            
            # Initialize trading strategies
            self.strategies = {
                'scalping': ScalpingStrategy(
                    self.dhan_client,
                    self.data_manager,
                    self.position_manager,
                    self.order_manager
                ),
                'momentum': MomentumStrategy(
                    self.dhan_client,
                    self.data_manager,
                    self.position_manager,
                    self.order_manager
                )
            }
            
            # Start data feeds
            await self.data_manager.start_market_data_feed()
            
            self.logger.info("Trading bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize trading bot: {e}")
            return False
    
    async def start_trading(self):
        """Start the automated trading process"""
        if not self.running:
            self.running = True
            self.logger.info("Starting automated trading...")
            
            # Start all active strategies
            tasks = []
            for name, strategy in self.strategies.items():
                if strategy.is_enabled():
                    self.logger.info(f"Starting {name} strategy")
                    tasks.append(asyncio.create_task(strategy.run()))
            
            # Start position monitoring
            tasks.append(asyncio.create_task(self.position_manager.monitor_positions()))
            
            # Start order monitoring
            tasks.append(asyncio.create_task(self.order_manager.monitor_orders()))
            
            # Wait for all tasks
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                self.logger.error(f"Error in trading tasks: {e}")
    
    async def stop_trading(self):
        """Stop all trading activities"""
        self.logger.info("Stopping automated trading...")
        self.running = False
        
        # Stop all strategies
        for strategy in self.strategies.values():
            await strategy.stop()
        
        # Close all positions if configured to do so
        if hasattr(settings, 'close_positions_on_shutdown') and settings.close_positions_on_shutdown:
            await self.position_manager.close_all_positions()
        
        # Stop data feeds
        if self.data_manager:
            await self.data_manager.stop_market_data_feed()
        
        # Close database connections
        if self.db_manager:
            await self.db_manager.close()
        
        self.logger.info("Trading bot stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop_trading())

async def main():
    """Main application entry point"""
    bot = TradingBot()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, bot.signal_handler)
    signal.signal(signal.SIGTERM, bot.signal_handler)
    
    try:
        # Initialize the bot
        if not await bot.initialize():
            sys.exit(1)
        
        # Start trading
        await bot.start_trading()
        
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}")
    finally:
        await bot.stop_trading()

if __name__ == "__main__":
    print("=== Nifty 50 Options Automated Trader ===")
    print("Press Ctrl+C to stop the bot")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown completed.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
