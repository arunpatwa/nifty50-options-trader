"""
Position manager for tracking and managing trading positions
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

from src.utils.logger import TradingLogger
from src.api.dhan_client import DhanClient
from config.settings import settings

class Position:
    """Represents a trading position"""
    
    def __init__(self, symbol: str, quantity: int, avg_price: float, strategy: str = None):
        self.symbol = symbol
        self.quantity = quantity  # Positive for long, negative for short
        self.avg_price = avg_price
        self.strategy = strategy
        self.opened_at = datetime.now()
        self.updated_at = datetime.now()
        
        # PnL tracking
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.market_price = avg_price
        
        # Risk management
        self.stop_loss = None
        self.target = None
        self.max_loss = None
    
    def update_market_price(self, new_price: float):
        """Update market price and calculate unrealized PnL"""
        self.market_price = new_price
        self.updated_at = datetime.now()
        
        if self.quantity != 0:
            self.unrealized_pnl = (new_price - self.avg_price) * abs(self.quantity)
            if self.quantity < 0:  # Short position
                self.unrealized_pnl = -self.unrealized_pnl
    
    def add_quantity(self, quantity: int, price: float):
        """Add quantity to position and update average price"""
        if self.quantity == 0:
            self.quantity = quantity
            self.avg_price = price
        else:
            # Calculate new average price
            total_value = (self.avg_price * abs(self.quantity)) + (price * abs(quantity))
            total_quantity = abs(self.quantity) + abs(quantity)
            
            if total_quantity > 0:
                self.avg_price = total_value / total_quantity
                self.quantity += quantity
        
        self.updated_at = datetime.now()
    
    def close_partial(self, quantity: int, price: float) -> float:
        """Close partial position and return realized PnL"""
        if abs(quantity) > abs(self.quantity):
            quantity = self.quantity
        
        # Calculate realized PnL for closed portion
        pnl = (price - self.avg_price) * abs(quantity)
        if self.quantity < 0:  # Short position
            pnl = -pnl
        
        self.quantity -= quantity
        self.realized_pnl += pnl
        self.updated_at = datetime.now()
        
        return pnl
    
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0
    
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0
    
    def is_flat(self) -> bool:
        """Check if position is flat (no quantity)"""
        return self.quantity == 0
    
    def get_total_pnl(self) -> float:
        """Get total PnL (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'market_price': self.market_price,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'total_pnl': self.get_total_pnl(),
            'strategy': self.strategy,
            'opened_at': self.opened_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'stop_loss': self.stop_loss,
            'target': self.target
        }

class PositionManager:
    """Manages all trading positions and risk"""
    
    def __init__(self, dhan_client: DhanClient):
        self.logger = TradingLogger(__name__)
        self.dhan_client = dhan_client
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.position_limits = {}
        
        # Risk parameters
        self.max_portfolio_value = settings.portfolio_limit
        self.max_positions = settings.max_positions
        self.max_risk_per_trade = settings.risk_per_trade
        self.daily_loss_limit = settings.daily_loss_limit
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_realized_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_portfolio_value = 0.0
        
        # Monitoring
        self.monitoring_active = False
    
    async def initialize(self):
        """Initialize position manager"""
        try:
            # Sync positions with broker
            await self.sync_positions()
            
            self.logger.logger.info("Position manager initialized")
            
        except Exception as e:
            self.logger.logger.error(f"Error initializing position manager: {e}")
    
    async def sync_positions(self):
        """Sync positions with broker"""
        try:
            broker_positions = await self.dhan_client.get_positions()
            if not broker_positions:
                return
            
            for pos_data in broker_positions:
                symbol = pos_data.get('trading_symbol')
                quantity = pos_data.get('net_quantity', 0)
                avg_price = pos_data.get('avg_price', 0)
                
                if symbol and quantity != 0:
                    position = Position(symbol, quantity, avg_price)
                    
                    # Update market price
                    market_price = pos_data.get('ltp', avg_price)
                    position.update_market_price(market_price)
                    
                    self.positions[symbol] = position
            
            self.logger.logger.info(f"Synced {len(self.positions)} positions from broker")
            
        except Exception as e:
            self.logger.logger.error(f"Error syncing positions: {e}")
    
    def add_position(self, symbol: str, quantity: int, price: float, strategy: str = None) -> bool:
        """
        Add or update a position
        
        Args:
            symbol: Trading symbol
            quantity: Quantity (positive for buy, negative for sell)
            price: Execution price
            strategy: Strategy name
            
        Returns:
            True if position added successfully
        """
        try:
            if symbol in self.positions:
                # Update existing position
                self.positions[symbol].add_quantity(quantity, price)
            else:
                # Create new position
                position = Position(symbol, quantity, price, strategy)
                self.positions[symbol] = position
            
            self.logger.log_position_update({
                'symbol': symbol,
                'quantity': self.positions[symbol].quantity,
                'avg_price': self.positions[symbol].avg_price,
                'pnl': self.positions[symbol].get_total_pnl()
            })
            
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error adding position for {symbol}: {e}")
            return False
    
    def close_position(self, symbol: str, quantity: int, price: float) -> Optional[float]:
        """
        Close position partially or fully
        
        Args:
            symbol: Trading symbol
            quantity: Quantity to close
            price: Closing price
            
        Returns:
            Realized PnL or None if error
        """
        try:
            if symbol not in self.positions:
                self.logger.logger.warning(f"No position found for {symbol}")
                return None
            
            position = self.positions[symbol]
            realized_pnl = position.close_partial(quantity, price)
            
            # Remove position if fully closed
            if position.is_flat():
                del self.positions[symbol]
                self.logger.logger.info(f"Position {symbol} fully closed with PnL: {realized_pnl}")
            
            # Update daily PnL
            self.daily_pnl += realized_pnl
            self.total_realized_pnl += realized_pnl
            
            return realized_pnl
            
        except Exception as e:
            self.logger.logger.error(f"Error closing position for {symbol}: {e}")
            return None
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol"""
        return self.positions.get(symbol)
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self.positions.copy()
    
    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.positions)
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        total_value = 0.0
        
        for position in self.positions.values():
            total_value += position.market_price * abs(position.quantity)
        
        return total_value
    
    def get_total_pnl(self) -> float:
        """Get total PnL across all positions"""
        total_pnl = 0.0
        
        for position in self.positions.values():
            total_pnl += position.get_total_pnl()
        
        return total_pnl
    
    def get_unrealized_pnl(self) -> float:
        """Get total unrealized PnL"""
        unrealized_pnl = 0.0
        
        for position in self.positions.values():
            unrealized_pnl += position.unrealized_pnl
        
        return unrealized_pnl
    
    def update_market_prices(self, price_updates: Dict[str, float]):
        """Update market prices for all positions"""
        for symbol, price in price_updates.items():
            if symbol in self.positions:
                self.positions[symbol].update_market_price(price)
    
    async def monitor_positions(self):
        """Monitor positions for risk management"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                await self._check_risk_limits()
                await self._update_drawdown()
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(30)
    
    async def stop_monitoring(self):
        """Stop position monitoring"""
        self.monitoring_active = False
    
    async def _check_risk_limits(self):
        """Check position-level risk limits"""
        # Check daily loss limit
        current_pnl = self.get_total_pnl()
        if current_pnl < -self.daily_loss_limit:
            self.logger.log_risk_event({
                'event': 'DAILY_LOSS_LIMIT_BREACH',
                'current_risk': current_pnl,
                'max_risk': -self.daily_loss_limit,
                'action': 'CLOSE_ALL_POSITIONS'
            })
            
            # Close all positions
            await self.close_all_positions()
        
        # Check portfolio value limit
        portfolio_value = self.get_portfolio_value()
        if portfolio_value > self.max_portfolio_value:
            self.logger.log_risk_event({
                'event': 'PORTFOLIO_LIMIT_BREACH',
                'current_risk': portfolio_value,
                'max_risk': self.max_portfolio_value,
                'action': 'REDUCE_POSITIONS'
            })
        
        # Check individual position limits
        for symbol, position in self.positions.items():
            if position.stop_loss and position.market_price <= position.stop_loss:
                self.logger.log_risk_event({
                    'event': 'STOP_LOSS_HIT',
                    'symbol': symbol,
                    'current_price': position.market_price,
                    'stop_loss': position.stop_loss,
                    'action': 'CLOSE_POSITION'
                })
                
                # TODO: Implement automatic position closing
    
    async def _update_drawdown(self):
        """Update maximum drawdown calculation"""
        current_portfolio_value = self.get_portfolio_value()
        
        if current_portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_portfolio_value
        
        if self.peak_portfolio_value > 0:
            drawdown = (self.peak_portfolio_value - current_portfolio_value) / self.peak_portfolio_value
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
    
    async def close_all_positions(self):
        """Close all open positions"""
        try:
            positions_to_close = list(self.positions.keys())
            
            for symbol in positions_to_close:
                position = self.positions[symbol]
                
                # Get current market price
                quote = await self.dhan_client.get_market_quote(symbol)
                if quote:
                    market_price = quote.get('ltp')
                    if market_price:
                        # Close the position
                        self.close_position(symbol, position.quantity, market_price)
            
            self.logger.logger.info(f"Closed {len(positions_to_close)} positions")
            
        except Exception as e:
            self.logger.logger.error(f"Error closing all positions: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk management summary"""
        return {
            'position_count': self.get_position_count(),
            'portfolio_value': self.get_portfolio_value(),
            'total_pnl': self.get_total_pnl(),
            'unrealized_pnl': self.get_unrealized_pnl(),
            'daily_pnl': self.daily_pnl,
            'max_drawdown': self.max_drawdown,
            'daily_loss_limit': self.daily_loss_limit,
            'portfolio_limit': self.max_portfolio_value,
            'monitoring_active': self.monitoring_active
        }
    
    def reset_daily_metrics(self):
        """Reset daily metrics"""
        self.daily_pnl = 0.0
        self.logger.logger.info("Daily metrics reset for position manager")
