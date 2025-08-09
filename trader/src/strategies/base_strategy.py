"""
Base strategy class for all trading strategies
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, time
import pytz

from src.utils.logger import TradingLogger
from src.api.dhan_client import DhanClient
from src.data.data_manager import DataManager
from src.risk_management.position_manager import PositionManager
from src.orders.order_manager import OrderManager
from config.settings import settings

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, dhan_client: DhanClient, data_manager: DataManager,
                 position_manager: PositionManager, order_manager: OrderManager):
        self.logger = TradingLogger(self.__class__.__name__)
        self.dhan_client = dhan_client
        self.data_manager = data_manager
        self.position_manager = position_manager
        self.order_manager = order_manager
        
        # Strategy configuration
        self.name = self.__class__.__name__
        self.enabled = True
        self.running = False
        
        # Market timing
        self.ist = pytz.timezone('Asia/Kolkata')
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        # Strategy parameters (to be overridden by subclasses)
        self.max_positions = 3
        self.position_size = settings.default_quantity
        self.stop_loss_percentage = 0.20  # 20%
        self.target_percentage = 0.30     # 30%
        
        # Performance tracking
        self.trades_today = 0
        self.pnl_today = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Risk limits
        self.max_daily_loss = settings.daily_loss_limit
        self.max_trades_per_day = 10
        
    def is_enabled(self) -> bool:
        """Check if strategy is enabled"""
        return self.enabled
    
    def enable(self):
        """Enable the strategy"""
        self.enabled = True
        self.logger.logger.info(f"{self.name} strategy enabled")
    
    def disable(self):
        """Disable the strategy"""
        self.enabled = False
        self.logger.logger.info(f"{self.name} strategy disabled")
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        current_time = datetime.now(self.ist).time()
        current_day = datetime.now(self.ist).weekday()
        
        # Monday = 0, Sunday = 6
        is_weekday = current_day < 5
        
        return is_weekday and self.market_start <= current_time <= self.market_end
    
    async def run(self):
        """Main strategy execution loop"""
        self.logger.logger.info(f"Starting {self.name} strategy")
        self.running = True
        
        try:
            # Initialize strategy-specific components
            await self.initialize()
            
            # Main execution loop
            while self.running and self.enabled:
                try:
                    # Check if market is open
                    if not self.is_market_hours():
                        await asyncio.sleep(60)  # Check every minute
                        continue
                    
                    # Check risk limits
                    if not self._check_risk_limits():
                        self.logger.logger.warning(f"{self.name} strategy paused due to risk limits")
                        await asyncio.sleep(300)  # Wait 5 minutes
                        continue
                    
                    # Execute strategy logic
                    await self.execute()
                    
                    # Wait before next iteration
                    await asyncio.sleep(self.get_execution_interval())
                    
                except Exception as e:
                    self.logger.logger.error(f"Error in {self.name} strategy execution: {e}")
                    await asyncio.sleep(30)  # Wait 30 seconds on error
                    
        except Exception as e:
            self.logger.logger.error(f"Fatal error in {self.name} strategy: {e}")
        finally:
            await self.cleanup()
            self.logger.logger.info(f"{self.name} strategy stopped")
    
    async def stop(self):
        """Stop the strategy"""
        self.logger.logger.info(f"Stopping {self.name} strategy")
        self.running = False
    
    @abstractmethod
    async def initialize(self):
        """Initialize strategy-specific components"""
        pass
    
    @abstractmethod
    async def execute(self):
        """Execute strategy logic"""
        pass
    
    @abstractmethod
    def get_execution_interval(self) -> int:
        """Get interval between strategy executions in seconds"""
        pass
    
    async def cleanup(self):
        """Cleanup strategy resources"""
        pass
    
    def _check_risk_limits(self) -> bool:
        """Check if strategy should continue based on risk limits"""
        # Check daily loss limit
        if abs(self.pnl_today) >= self.max_daily_loss:
            self.logger.logger.warning(f"Daily loss limit reached: {self.pnl_today}")
            return False
        
        # Check maximum trades per day
        if self.trades_today >= self.max_trades_per_day:
            self.logger.logger.warning(f"Maximum trades per day reached: {self.trades_today}")
            return False
        
        # Check position limits
        current_positions = len(self.position_manager.get_positions())
        if current_positions >= self.max_positions:
            self.logger.logger.warning(f"Maximum positions reached: {current_positions}")
            return False
        
        return True
    
    async def place_trade(self, trade_params: Dict[str, Any]) -> Optional[str]:
        """
        Place a trade with proper risk management
        
        Args:
            trade_params: Trade parameters
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            # Validate trade parameters
            if not self._validate_trade_params(trade_params):
                return None
            
            # Calculate position size based on risk
            position_size = self._calculate_position_size(trade_params)
            if position_size <= 0:
                self.logger.logger.warning("Position size calculated as 0, skipping trade")
                return None
            
            # Update trade parameters with calculated position size
            trade_params['quantity'] = position_size
            trade_params['strategy'] = self.name
            
            # Place the order
            order_id = await self.order_manager.place_order(trade_params)
            
            if order_id:
                self.trades_today += 1
                self.logger.logger.info(f"Trade placed: {trade_params['symbol']} {trade_params['side']} {position_size}")
            
            return order_id
            
        except Exception as e:
            self.logger.logger.error(f"Error placing trade: {e}")
            return None
    
    def _validate_trade_params(self, trade_params: Dict[str, Any]) -> bool:
        """Validate trade parameters"""
        required_fields = ['symbol', 'side', 'price']
        
        for field in required_fields:
            if field not in trade_params:
                self.logger.logger.error(f"Missing required field: {field}")
                return False
        
        if trade_params['side'] not in ['BUY', 'SELL']:
            self.logger.logger.error(f"Invalid side: {trade_params['side']}")
            return False
        
        if trade_params['price'] <= 0:
            self.logger.logger.error(f"Invalid price: {trade_params['price']}")
            return False
        
        return True
    
    def _calculate_position_size(self, trade_params: Dict[str, Any]) -> int:
        """
        Calculate appropriate position size based on risk management
        
        Args:
            trade_params: Trade parameters
            
        Returns:
            Position size in lots
        """
        try:
            # Get account balance
            funds = self.dhan_client.get_funds()
            if not funds:
                return self.position_size  # Default size
            
            available_balance = funds.get('available_balance', 0)
            
            # Calculate stop loss price
            entry_price = trade_params['price']
            stop_loss_price = entry_price * (1 - self.stop_loss_percentage)
            if trade_params['side'] == 'SELL':
                stop_loss_price = entry_price * (1 + self.stop_loss_percentage)
            
            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss_price)
            
            # Calculate maximum risk amount (percentage of balance)
            max_risk_amount = available_balance * settings.risk_per_trade
            
            # Calculate position size
            if risk_per_unit > 0:
                max_units = max_risk_amount / risk_per_unit
                lots = int(max_units / settings.default_quantity)
                
                # Ensure minimum 1 lot and maximum configured size
                return max(1, min(lots, self.position_size // settings.default_quantity)) * settings.default_quantity
            
            return self.position_size
            
        except Exception as e:
            self.logger.logger.error(f"Error calculating position size: {e}")
            return self.position_size
    
    async def update_performance(self, pnl: float, is_winning_trade: bool):
        """Update strategy performance metrics"""
        self.pnl_today += pnl
        
        if is_winning_trade:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'strategy': self.name,
            'enabled': self.enabled,
            'running': self.running,
            'trades_today': self.trades_today,
            'pnl_today': self.pnl_today,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_trades': total_trades
        }
    
    def reset_daily_metrics(self):
        """Reset daily performance metrics"""
        self.trades_today = 0
        self.pnl_today = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        self.logger.logger.info(f"{self.name} daily metrics reset")
