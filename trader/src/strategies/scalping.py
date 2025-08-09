"""
Scalping strategy for Nifty 50 options
Fast-paced trading strategy for quick profits on small price movements
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from src.strategies.base_strategy import BaseStrategy
from src.utils.helpers import get_nearest_strikes, round_to_tick_size
from config.settings import SCALPING_TIMEFRAME

class ScalpingStrategy(BaseStrategy):
    """
    Scalping strategy for Nifty 50 options
    
    Strategy Logic:
    - Monitor ATM and nearby strikes for quick price movements
    - Enter positions on momentum with tight stop losses
    - Exit quickly with small profits (15-30 points)
    - High frequency, low risk per trade
    """
    
    def __init__(self, dhan_client, data_manager, position_manager, order_manager):
        super().__init__(dhan_client, data_manager, position_manager, order_manager)
        
        # Strategy-specific parameters
        self.name = "ScalpingStrategy"
        self.max_positions = 2  # Lower for scalping
        self.position_size = 25  # Single lot for quick moves
        self.stop_loss_percentage = 0.15  # 15% stop loss (tight)
        self.target_percentage = 0.25     # 25% target (quick)
        
        # Scalping parameters
        self.min_premium = 20      # Minimum option premium to trade
        self.max_premium = 200     # Maximum option premium to trade
        self.momentum_threshold = 5 # Points movement to trigger entry
        self.quick_exit_profit = 15 # Quick exit at 15 points profit
        
        # Technical indicators
        self.price_history = []
        self.momentum_periods = 5  # Look back periods for momentum
        self.volatility_threshold = 0.02  # 2% volatility threshold
        
        # Trade tracking
        self.last_trade_time = None
        self.min_trade_interval = 60  # Minimum 60 seconds between trades
        
        # Monitored symbols
        self.monitored_options = {}
        self.current_expiry = None
    
    async def initialize(self):
        """Initialize scalping strategy"""
        try:
            self.logger.logger.info("Initializing scalping strategy")
            
            # Set current expiry
            from src.utils.helpers import get_expiry_dates
            expiry_dates = get_expiry_dates()
            if expiry_dates:
                self.current_expiry = expiry_dates[0]
            
            # Subscribe to Nifty price updates
            self.data_manager.market_data.add_price_callback("NIFTY 50", self._on_nifty_price_update)
            
            # Setup option monitoring
            await self._setup_option_monitoring()
            
            self.logger.logger.info("Scalping strategy initialized")
            
        except Exception as e:
            self.logger.logger.error(f"Error initializing scalping strategy: {e}")
    
    async def execute(self):
        """Execute scalping strategy logic"""
        try:
            # Check if we can trade
            if not await self._can_trade():
                return
            
            # Update market analysis
            await self._update_market_analysis()
            
            # Check for scalping opportunities
            await self._check_scalping_opportunities()
            
            # Manage existing positions
            await self._manage_positions()
            
        except Exception as e:
            self.logger.logger.error(f"Error in scalping strategy execution: {e}")
    
    def get_execution_interval(self) -> int:
        """Get execution interval (fast for scalping)"""
        return 5  # Execute every 5 seconds
    
    async def _can_trade(self) -> bool:
        """Check if we can place new trades"""
        # Check market hours
        if not self.is_market_hours():
            return False
        
        # Check position limits
        if self.position_manager.get_position_count() >= self.max_positions:
            return False
        
        # Check minimum interval between trades
        if self.last_trade_time:
            time_since_last = (datetime.now() - self.last_trade_time).total_seconds()
            if time_since_last < self.min_trade_interval:
                return False
        
        # Check daily limits
        if not self._check_risk_limits():
            return False
        
        return True
    
    async def _setup_option_monitoring(self):
        """Setup option chain monitoring for scalping"""
        try:
            # Get current Nifty price
            nifty_price = self.data_manager.get_nifty_price()
            if not nifty_price:
                return
            
            # Get nearby strikes (ATM +/- 3 strikes)
            strikes = get_nearest_strikes(nifty_price, 3)
            
            # Get option chain for current expiry
            option_chain = await self.data_manager.market_data.get_option_chain("NIFTY", self.current_expiry)
            if not option_chain:
                return
            
            # Setup monitoring for relevant options
            for option in option_chain.get('options', []):
                strike = option.get('strike_price', 0)
                
                if strike in strikes:
                    call_symbol = option.get('call_symbol')
                    put_symbol = option.get('put_symbol')
                    
                    if call_symbol:
                        await self.data_manager.market_data.subscribe_symbol(call_symbol, "NSE_FNO")
                        self.monitored_options[call_symbol] = {
                            'type': 'CALL',
                            'strike': strike,
                            'symbol': call_symbol
                        }
                    
                    if put_symbol:
                        await self.data_manager.market_data.subscribe_symbol(put_symbol, "NSE_FNO")
                        self.monitored_options[put_symbol] = {
                            'type': 'PUT',
                            'strike': strike,
                            'symbol': put_symbol
                        }
            
            self.logger.logger.info(f"Monitoring {len(self.monitored_options)} options for scalping")
            
        except Exception as e:
            self.logger.logger.error(f"Error setting up option monitoring: {e}")
    
    async def _update_market_analysis(self):
        """Update market analysis for scalping decisions"""
        try:
            # Get recent Nifty data
            nifty_data = self.data_manager.get_nifty_data(20)
            if len(nifty_data) < 10:
                return
            
            current_price = nifty_data[-1]['ltp']
            if not current_price:
                return
            
            # Calculate momentum
            past_price = nifty_data[-self.momentum_periods]['ltp'] if len(nifty_data) >= self.momentum_periods else current_price
            momentum = current_price - past_price
            
            # Calculate short-term volatility
            prices = [tick['ltp'] for tick in nifty_data[-10:] if tick.get('ltp')]
            if len(prices) >= 5:
                volatility = self._calculate_volatility(prices)
            else:
                volatility = 0.01
            
            # Store analysis
            self.market_analysis = {
                'current_price': current_price,
                'momentum': momentum,
                'volatility': volatility,
                'trend': 'bullish' if momentum > 0 else 'bearish' if momentum < 0 else 'neutral'
            }
            
        except Exception as e:
            self.logger.logger.error(f"Error updating market analysis: {e}")
    
    async def _check_scalping_opportunities(self):
        """Check for scalping opportunities"""
        try:
            if not hasattr(self, 'market_analysis'):
                return
            
            momentum = self.market_analysis.get('momentum', 0)
            volatility = self.market_analysis.get('volatility', 0)
            
            # Need sufficient momentum for scalping
            if abs(momentum) < self.momentum_threshold:
                return
            
            # Need sufficient volatility
            if volatility < self.volatility_threshold:
                return
            
            # Look for options to scalp
            for symbol, option_info in self.monitored_options.items():
                await self._check_option_scalp_opportunity(symbol, option_info)
                
        except Exception as e:
            self.logger.logger.error(f"Error checking scalping opportunities: {e}")
    
    async def _check_option_scalp_opportunity(self, symbol: str, option_info: Dict[str, Any]):
        """Check specific option for scalping opportunity"""
        try:
            # Get current option price
            option_price = self.data_manager.get_option_price(symbol)
            if not option_price:
                return
            
            # Check premium range
            if option_price < self.min_premium or option_price > self.max_premium:
                return
            
            # Check if we already have position in this option
            if self.position_manager.get_position(symbol):
                return
            
            # Determine trade direction based on momentum and option type
            momentum = self.market_analysis.get('momentum', 0)
            option_type = option_info['type']
            
            should_buy = False
            
            if option_type == 'CALL' and momentum > self.momentum_threshold:
                should_buy = True  # Buy calls on upward momentum
            elif option_type == 'PUT' and momentum < -self.momentum_threshold:
                should_buy = True  # Buy puts on downward momentum
            
            if should_buy:
                await self._place_scalp_trade(symbol, option_price, option_info)
                
        except Exception as e:
            self.logger.logger.error(f"Error checking option scalp opportunity for {symbol}: {e}")
    
    async def _place_scalp_trade(self, symbol: str, price: float, option_info: Dict[str, Any]):
        """Place a scalping trade"""
        try:
            # Calculate entry parameters
            entry_price = round_to_tick_size(price)
            stop_loss_price = round_to_tick_size(entry_price * (1 - self.stop_loss_percentage))
            target_price = round_to_tick_size(entry_price * (1 + self.target_percentage))
            
            # Place buy order
            trade_params = {
                'symbol': symbol,
                'side': 'BUY',
                'quantity': self.position_size,
                'order_type': 'LIMIT',
                'price': entry_price,
                'strategy': self.name,
                'metadata': {
                    'stop_loss': stop_loss_price,
                    'target': target_price,
                    'option_type': option_info['type'],
                    'strike': option_info['strike'],
                    'trade_type': 'scalp_entry'
                }
            }
            
            order_id = await self.place_trade(trade_params)
            
            if order_id:
                self.last_trade_time = datetime.now()
                self.logger.logger.info(f"Scalp trade placed: {symbol} BUY {self.position_size} @ {entry_price}")
                
                # Store trade for monitoring
                self.active_scalp_trades = getattr(self, 'active_scalp_trades', {})
                self.active_scalp_trades[symbol] = {
                    'order_id': order_id,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss_price,
                    'target': target_price,
                    'entry_time': datetime.now()
                }
            
        except Exception as e:
            self.logger.logger.error(f"Error placing scalp trade for {symbol}: {e}")
    
    async def _manage_positions(self):
        """Manage existing scalping positions"""
        try:
            positions = self.position_manager.get_positions()
            
            for symbol, position in positions.items():
                if position.strategy == self.name:
                    await self._manage_scalp_position(symbol, position)
                    
        except Exception as e:
            self.logger.logger.error(f"Error managing scalping positions: {e}")
    
    async def _manage_scalp_position(self, symbol: str, position):
        """Manage individual scalping position"""
        try:
            current_price = self.data_manager.get_option_price(symbol)
            if not current_price:
                return
            
            # Update position market price
            position.update_market_price(current_price)
            
            # Check for quick exit opportunity
            unrealized_pnl = position.unrealized_pnl
            entry_price = position.avg_price
            
            # Quick exit if we hit our quick profit target
            profit_points = current_price - entry_price
            if profit_points >= self.quick_exit_profit:
                await self._exit_scalp_position(symbol, position, current_price, "QUICK_PROFIT")
                return
            
            # Check stop loss
            if hasattr(position, 'stop_loss') and current_price <= position.stop_loss:
                await self._exit_scalp_position(symbol, position, current_price, "STOP_LOSS")
                return
            
            # Check target
            if hasattr(position, 'target') and current_price >= position.target:
                await self._exit_scalp_position(symbol, position, current_price, "TARGET_HIT")
                return
            
            # Time-based exit (hold for maximum 15 minutes for scalping)
            position_age = (datetime.now() - position.opened_at).total_seconds() / 60
            if position_age > 15:  # 15 minutes
                await self._exit_scalp_position(symbol, position, current_price, "TIME_EXIT")
                return
                
        except Exception as e:
            self.logger.logger.error(f"Error managing scalp position for {symbol}: {e}")
    
    async def _exit_scalp_position(self, symbol: str, position, exit_price: float, reason: str):
        """Exit scalping position"""
        try:
            # Place sell order
            exit_params = {
                'symbol': symbol,
                'side': 'SELL',
                'quantity': abs(position.quantity),
                'order_type': 'MARKET',  # Market order for quick exit
                'strategy': self.name,
                'metadata': {
                    'exit_reason': reason,
                    'trade_type': 'scalp_exit'
                }
            }
            
            order_id = await self.place_trade(exit_params)
            
            if order_id:
                # Calculate and log PnL
                pnl = (exit_price - position.avg_price) * abs(position.quantity)
                is_winning = pnl > 0
                
                self.logger.logger.info(f"Scalp position exited: {symbol} {reason} PnL: {pnl:.2f}")
                
                # Update performance
                await self.update_performance(pnl, is_winning)
                
                # Clean up tracking
                if hasattr(self, 'active_scalp_trades') and symbol in self.active_scalp_trades:
                    del self.active_scalp_trades[symbol]
            
        except Exception as e:
            self.logger.logger.error(f"Error exiting scalp position for {symbol}: {e}")
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate simple volatility from price list"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        
        return variance ** 0.5
    
    async def _on_nifty_price_update(self, price_data: Dict[str, Any]):
        """Handle Nifty price updates for scalping signals"""
        try:
            # Store price data for momentum calculation
            self.price_history.append({
                'price': price_data.get('ltp'),
                'timestamp': datetime.now()
            })
            
            # Keep only recent data
            if len(self.price_history) > 50:
                self.price_history = self.price_history[-30:]
                
        except Exception as e:
            self.logger.logger.error(f"Error processing Nifty price update: {e}")
    
    async def cleanup(self):
        """Cleanup scalping strategy"""
        try:
            # Close any open scalping positions
            positions = self.position_manager.get_positions()
            
            for symbol, position in positions.items():
                if position.strategy == self.name:
                    current_price = self.data_manager.get_option_price(symbol)
                    if current_price:
                        await self._exit_scalp_position(symbol, position, current_price, "STRATEGY_SHUTDOWN")
            
            self.logger.logger.info("Scalping strategy cleanup completed")
            
        except Exception as e:
            self.logger.logger.error(f"Error in scalping strategy cleanup: {e}")
