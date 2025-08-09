"""
Example configuration and usage script for the Nifty options trader
"""

import asyncio
import os
from datetime import datetime

# Import trading components
from src.api.dhan_client import DhanClient
from src.data.data_manager import DataManager
from src.risk_management.position_manager import PositionManager
from src.orders.order_manager import OrderManager
from src.strategies.scalping import ScalpingStrategy
from src.strategies.momentum import MomentumStrategy
from src.data.database import DatabaseManager
from src.utils.logger import setup_logger
from dashboard.app import create_dashboard

class NiftyOptionsTrader:
    """Simple example of using the trading system"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        
        # Core components
        self.dhan_client = None
        self.data_manager = None
        self.position_manager = None
        self.order_manager = None
        self.db_manager = None
        
        # Strategies
        self.strategies = {}
        
        # Dashboard
        self.dashboard = None
        
        # Control flags
        self.running = False
    
    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("Initializing Nifty Options Trader...")
            
            # Initialize database
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Initialize API client
            self.dhan_client = DhanClient()
            authenticated = await self.dhan_client.authenticate()
            
            if not authenticated:
                self.logger.error("Failed to authenticate with Dhan. Please check your credentials.")
                return False
            
            # Initialize data manager
            self.data_manager = DataManager(self.dhan_client)
            await self.data_manager.initialize()
            
            # Initialize risk and order managers
            self.position_manager = PositionManager(self.dhan_client)
            await self.position_manager.initialize()
            
            self.order_manager = OrderManager(self.dhan_client, self.position_manager)
            
            # Initialize strategies
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
            
            # Initialize strategies
            for strategy in self.strategies.values():
                await strategy.initialize()
            
            # Create dashboard
            self.dashboard = create_dashboard(self)
            
            self.logger.info("Nifty Options Trader initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing trader: {e}")
            return False
    
    async def start_trading(self):
        """Start automated trading"""
        if not await self.initialize():
            return
        
        self.running = True
        self.logger.info("Starting automated trading...")
        
        try:
            # Start monitoring tasks
            tasks = []
            
            # Start position monitoring
            tasks.append(asyncio.create_task(self.position_manager.monitor_positions()))
            
            # Start order monitoring
            tasks.append(asyncio.create_task(self.order_manager.monitor_orders()))
            
            # Start enabled strategies
            for name, strategy in self.strategies.items():
                if strategy.is_enabled():
                    self.logger.info(f"Starting {name} strategy")
                    tasks.append(asyncio.create_task(strategy.run()))
            
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            self.logger.info("Cleaning up resources...")
            
            # Stop strategies
            for strategy in self.strategies.values():
                await strategy.stop()
            
            # Stop monitoring
            await self.position_manager.stop_monitoring()
            await self.order_manager.stop_monitoring()
            
            # Stop data feeds
            await self.data_manager.stop_market_data_feed()
            
            # Close API client
            await self.dhan_client.close()
            
            # Close database
            await self.db_manager.close()
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}")
    
    def run_dashboard(self):
        """Run the web dashboard"""
        if self.dashboard:
            self.dashboard.run(
                host='localhost',
                port=8050,
                debug=False
            )
        else:
            print("Dashboard not available. Please install dash and plotly:")
            print("pip install dash plotly")
    
    def get_status(self):
        """Get current trading status"""
        if not self.position_manager or not self.data_manager:
            return {"status": "Not initialized"}
        
        return {
            "status": "Running" if self.running else "Stopped",
            "market_open": self.data_manager.market_data.is_connected,
            "positions": len(self.position_manager.get_positions()),
            "nifty_price": self.data_manager.get_nifty_price(),
            "daily_pnl": self.position_manager.daily_pnl,
            "total_pnl": self.position_manager.get_total_pnl(),
            "strategies": {
                name: strategy.get_performance_summary()
                for name, strategy in self.strategies.items()
            }
        }

async def main():
    """Main function for running the trader"""
    
    print("=== Nifty 50 Options Automated Trader ===")
    print("Make sure you have configured your .env file with Dhan API credentials")
    print()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and configure your settings")
        return
    
    # Create trader instance
    trader = NiftyOptionsTrader()
    
    try:
        # Start trading
        await trader.start_trading()
        
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down trader...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

def run_dashboard_only():
    """Run only the dashboard for monitoring"""
    print("Starting dashboard...")
    print("Open http://localhost:8050 in your browser")
    
    # Create a minimal trader for dashboard
    trader = NiftyOptionsTrader()
    trader.dashboard = create_dashboard()
    trader.run_dashboard()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        run_dashboard_only()
    else:
        asyncio.run(main())
