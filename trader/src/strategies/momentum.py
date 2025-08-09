"""
Momentum strategy for Nifty 50 options
Trend-following strategy that captures sustained price movements
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from src.strategies.base_strategy import BaseStrategy
from src.utils.helpers import get_nearest_strikes, round_to_tick_size, calculate_option_greeks
from config.settings import MOMENTUM_TIMEFRAME

class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy for Nifty 50 options
    
    Strategy Logic:
    - Identify strong directional moves in Nifty
    - Enter options positions in the direction of momentum
    - Use trend-following indicators for entry and exit
    - Hold positions longer than scalping (30 minutes to 2 hours)
    """
    
    def __init__(self, dhan_client, data_manager, position_manager, order_manager):
        super().__init__(dhan_client, data_manager, position_manager, order_manager)
        
        # Strategy-specific parameters
        self.name = "MomentumStrategy"
        self.max_positions = 3
        self.position_size = 50  # 2 lots for momentum trades
        self.stop_loss_percentage = 0.25  # 25% stop loss
        self.target_percentage = 0.50     # 50% target
        
        # Momentum parameters
        self.momentum_threshold = 10      # Points movement to confirm momentum
        self.trend_confirmation_period = 10  # Periods for trend confirmation
        self.min_volume_threshold = 100000   # Minimum volume for momentum confirmation
        
        # Technical indicators
        self.sma_short_period = 5    # Short SMA period
        self.sma_long_period = 20    # Long SMA period
        self.rsi_period = 14         # RSI period
        self.volatility_period = 20   # Volatility calculation period
        
        # Momentum tracking
        self.price_momentum_history = []
        self.volume_momentum_history = []
        self.last_momentum_signal = None
        self.momentum_signal_time = None
        
        # Greeks tracking for options selection
        self.option_greeks = {}
        
        # Monitored options
        self.momentum_options = {}
        self.current_expiry = None
    
    async def initialize(self):
        """Initialize momentum strategy"""
        try:
            self.logger.logger.info("Initializing momentum strategy")
            
            # Set current expiry
            from src.utils.helpers import get_expiry_dates
            expiry_dates = get_expiry_dates()
            if expiry_dates:
                self.current_expiry = expiry_dates[0]
            
            # Subscribe to Nifty price updates
            self.data_manager.market_data.add_price_callback("NIFTY 50", self._on_nifty_momentum_update)
            
            # Setup option monitoring for momentum
            await self._setup_momentum_option_monitoring()
            
            self.logger.logger.info("Momentum strategy initialized")
            
        except Exception as e:
            self.logger.logger.error(f"Error initializing momentum strategy: {e}")
    
    async def execute(self):
        """Execute momentum strategy logic"""
        try:
            # Update momentum analysis
            await self._update_momentum_analysis()
            
            # Check for momentum signals
            momentum_signal = await self._detect_momentum_signal()
            
            if momentum_signal:
                # Check for entry opportunities
                await self._check_momentum_entry_opportunities(momentum_signal)
            
            # Manage existing positions
            await self._manage_momentum_positions()
            
            # Update option Greeks periodically
            await self._update_option_greeks()
            
        except Exception as e:
            self.logger.logger.error(f"Error in momentum strategy execution: {e}")
    
    def get_execution_interval(self) -> int:
        """Get execution interval (moderate for momentum)"""
        return 15  # Execute every 15 seconds
    
    async def _setup_momentum_option_monitoring(self):
        """Setup option monitoring for momentum trading"""
        try:
            # Get current Nifty price
            nifty_price = self.data_manager.get_nifty_price()
            if not nifty_price:
                return
            
            # Get wider range of strikes for momentum (ATM +/- 5 strikes)
            strikes = get_nearest_strikes(nifty_price, 5)
            
            # Get option chain
            option_chain = await self.data_manager.market_data.get_option_chain("NIFTY", self.current_expiry)
            if not option_chain:
                return
            
            # Setup monitoring for momentum options
            for option in option_chain.get('options', []):
                strike = option.get('strike_price', 0)
                
                if strike in strikes:
                    call_symbol = option.get('call_symbol')
                    put_symbol = option.get('put_symbol')
                    
                    if call_symbol:
                        await self.data_manager.market_data.subscribe_symbol(call_symbol, "NSE_FNO")
                        self.momentum_options[call_symbol] = {
                            'type': 'CALL',
                            'strike': strike,
                            'symbol': call_symbol,
                            'moneyness': 'ATM' if abs(strike - nifty_price) < 25 else 'OTM' if strike > nifty_price else 'ITM'
                        }
                    
                    if put_symbol:
                        await self.data_manager.market_data.subscribe_symbol(put_symbol, "NSE_FNO")
                        self.momentum_options[put_symbol] = {
                            'type': 'PUT',
                            'strike': strike,
                            'symbol': put_symbol,
                            'moneyness': 'ATM' if abs(strike - nifty_price) < 25 else 'OTM' if strike < nifty_price else 'ITM'
                        }
            
            self.logger.logger.info(f"Monitoring {len(self.momentum_options)} options for momentum trading")
            
        except Exception as e:
            self.logger.logger.error(f"Error setting up momentum option monitoring: {e}")
    
    async def _update_momentum_analysis(self):
        """Update momentum analysis"""
        try:
            # Get Nifty data
            nifty_data = self.data_manager.get_nifty_data(50)
            if len(nifty_data) < 30:
                return
            
            current_price = nifty_data[-1]['ltp']
            if not current_price:
                return
            
            # Calculate moving averages
            sma_short = self._calculate_sma(nifty_data, self.sma_short_period)
            sma_long = self._calculate_sma(nifty_data, self.sma_long_period)
            
            # Calculate momentum
            momentum_5 = current_price - nifty_data[-5]['ltp'] if len(nifty_data) >= 5 else 0
            momentum_10 = current_price - nifty_data[-10]['ltp'] if len(nifty_data) >= 10 else 0
            momentum_20 = current_price - nifty_data[-20]['ltp'] if len(nifty_data) >= 20 else 0
            
            # Calculate RSI
            rsi = self._calculate_rsi(nifty_data, self.rsi_period)
            
            # Calculate volatility
            prices = [tick['ltp'] for tick in nifty_data[-self.volatility_period:] if tick.get('ltp')]
            volatility = self._calculate_volatility(prices) if len(prices) >= 10 else 0
            
            # Store momentum analysis
            self.momentum_analysis = {
                'current_price': current_price,
                'sma_short': sma_short,
                'sma_long': sma_long,
                'momentum_5': momentum_5,
                'momentum_10': momentum_10,
                'momentum_20': momentum_20,
                'rsi': rsi,
                'volatility': volatility,
                'trend_strength': abs(momentum_10) / current_price * 100 if current_price > 0 else 0,
                'trend_direction': 'bullish' if momentum_10 > 0 else 'bearish' if momentum_10 < 0 else 'neutral'
            }
            
        except Exception as e:
            self.logger.logger.error(f"Error updating momentum analysis: {e}")
    
    async def _detect_momentum_signal(self) -> Optional[Dict[str, Any]]:
        """Detect momentum trading signals"""
        try:
            if not hasattr(self, 'momentum_analysis'):
                return None
            
            analysis = self.momentum_analysis
            
            # Check for strong momentum conditions
            strong_momentum = (
                abs(analysis['momentum_10']) > self.momentum_threshold and
                analysis['trend_strength'] > 0.5  # At least 0.5% move
            )
            
            if not strong_momentum:
                return None
            
            # Check moving average alignment for trend confirmation
            sma_alignment = (
                analysis['sma_short'] > analysis['sma_long'] if analysis['momentum_10'] > 0
                else analysis['sma_short'] < analysis['sma_long']
            )
            
            # Check RSI for overbought/oversold conditions
            rsi_ok = 30 < analysis['rsi'] < 70  # Avoid extreme RSI levels
            
            # Check volatility (need sufficient volatility for momentum)
            volatility_ok = analysis['volatility'] > 0.01  # At least 1% volatility
            
            if sma_alignment and rsi_ok and volatility_ok:
                signal = {
                    'direction': 'bullish' if analysis['momentum_10'] > 0 else 'bearish',
                    'strength': analysis['trend_strength'],
                    'momentum': analysis['momentum_10'],
                    'timestamp': datetime.now(),
                    'rsi': analysis['rsi'],
                    'volatility': analysis['volatility']
                }
                
                # Avoid duplicate signals (wait at least 5 minutes)
                if (not self.momentum_signal_time or 
                    (datetime.now() - self.momentum_signal_time).total_seconds() > 300):
                    
                    self.last_momentum_signal = signal
                    self.momentum_signal_time = datetime.now()
                    
                    self.logger.logger.info(f"Momentum signal detected: {signal['direction']} (strength: {signal['strength']:.2f}%)")
                    return signal
            
            return None
            
        except Exception as e:
            self.logger.logger.error(f"Error detecting momentum signal: {e}")
            return None
    
    async def _check_momentum_entry_opportunities(self, signal: Dict[str, Any]):
        """Check for momentum entry opportunities"""
        try:
            # Don't enter if we already have maximum positions
            if self.position_manager.get_position_count() >= self.max_positions:
                return
            
            signal_direction = signal['direction']
            
            # Find best option to trade based on momentum direction
            best_option = await self._find_best_momentum_option(signal_direction)
            
            if best_option:
                await self._place_momentum_trade(best_option, signal)
                
        except Exception as e:
            self.logger.logger.error(f"Error checking momentum entry opportunities: {e}")
    
    async def _find_best_momentum_option(self, direction: str) -> Optional[Dict[str, Any]]:
        """Find the best option for momentum trading"""
        try:
            candidates = []
            
            # Get current Nifty price for delta calculations
            nifty_price = self.data_manager.get_nifty_price()
            if not nifty_price:
                return None
            
            for symbol, option_info in self.momentum_options.items():
                # Skip if we already have a position
                if self.position_manager.get_position(symbol):
                    continue
                
                option_price = self.data_manager.get_option_price(symbol)
                if not option_price or option_price < 10:  # Minimum premium
                    continue
                
                # Select calls for bullish momentum, puts for bearish
                if (direction == 'bullish' and option_info['type'] == 'CALL') or \
                   (direction == 'bearish' and option_info['type'] == 'PUT'):
                    
                    # Prefer slightly OTM options for momentum trading
                    strike = option_info['strike']
                    moneyness_score = 0
                    
                    if option_info['type'] == 'CALL':
                        if strike > nifty_price and strike - nifty_price <= 100:  # OTM calls within 100 points
                            moneyness_score = 10 - abs(strike - nifty_price) / 10
                    else:  # PUT
                        if strike < nifty_price and nifty_price - strike <= 100:  # OTM puts within 100 points
                            moneyness_score = 10 - abs(strike - nifty_price) / 10
                    
                    # Calculate liquidity score (higher volume = better)
                    volume_data = self.data_manager.market_data.get_latest_price(symbol)
                    volume = volume_data.get('volume', 0) if volume_data else 0
                    liquidity_score = min(volume / 10000, 10)  # Cap at 10
                    
                    # Calculate premium efficiency (not too expensive, not too cheap)
                    premium_score = 10 - abs(option_price - 50) / 10  # Prefer around 50 premium
                    premium_score = max(0, min(premium_score, 10))
                    
                    total_score = moneyness_score + liquidity_score + premium_score
                    
                    candidates.append({
                        'symbol': symbol,
                        'option_info': option_info,
                        'price': option_price,
                        'score': total_score
                    })
            
            # Sort by score and return best candidate
            if candidates:
                best = max(candidates, key=lambda x: x['score'])
                return best
            
            return None
            
        except Exception as e:
            self.logger.logger.error(f"Error finding best momentum option: {e}")
            return None
    
    async def _place_momentum_trade(self, option_data: Dict[str, Any], signal: Dict[str, Any]):
        """Place momentum trade"""
        try:
            symbol = option_data['symbol']
            option_price = option_data['price']
            
            # Calculate entry parameters
            entry_price = round_to_tick_size(option_price)
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
                    'signal_direction': signal['direction'],
                    'signal_strength': signal['strength'],
                    'option_type': option_data['option_info']['type'],
                    'strike': option_data['option_info']['strike'],
                    'trade_type': 'momentum_entry'
                }
            }
            
            order_id = await self.place_trade(trade_params)
            
            if order_id:
                self.logger.logger.info(f"Momentum trade placed: {symbol} BUY {self.position_size} @ {entry_price} (Signal: {signal['direction']})")
                
                # Store trade for monitoring
                self.active_momentum_trades = getattr(self, 'active_momentum_trades', {})
                self.active_momentum_trades[symbol] = {
                    'order_id': order_id,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss_price,
                    'target': target_price,
                    'signal': signal,
                    'entry_time': datetime.now()
                }
            
        except Exception as e:
            self.logger.logger.error(f"Error placing momentum trade: {e}")
    
    async def _manage_momentum_positions(self):
        """Manage existing momentum positions"""
        try:
            positions = self.position_manager.get_positions()
            
            for symbol, position in positions.items():
                if position.strategy == self.name:
                    await self._manage_momentum_position(symbol, position)
                    
        except Exception as e:
            self.logger.logger.error(f"Error managing momentum positions: {e}")
    
    async def _manage_momentum_position(self, symbol: str, position):
        """Manage individual momentum position"""
        try:
            current_price = self.data_manager.get_option_price(symbol)
            if not current_price:
                return
            
            # Update position market price
            position.update_market_price(current_price)
            
            # Get momentum analysis for trend validation
            if hasattr(self, 'momentum_analysis'):
                current_momentum = self.momentum_analysis.get('momentum_10', 0)
                
                # Check if momentum has reversed (exit signal)
                if hasattr(self, 'active_momentum_trades') and symbol in self.active_momentum_trades:
                    original_signal = self.active_momentum_trades[symbol]['signal']
                    original_direction = original_signal['direction']
                    
                    # Exit if momentum has reversed significantly
                    if ((original_direction == 'bullish' and current_momentum < -self.momentum_threshold / 2) or
                        (original_direction == 'bearish' and current_momentum > self.momentum_threshold / 2)):
                        await self._exit_momentum_position(symbol, position, current_price, "MOMENTUM_REVERSAL")
                        return
            
            # Check stop loss
            if hasattr(position, 'stop_loss') and current_price <= position.stop_loss:
                await self._exit_momentum_position(symbol, position, current_price, "STOP_LOSS")
                return
            
            # Check target
            if hasattr(position, 'target') and current_price >= position.target:
                await self._exit_momentum_position(symbol, position, current_price, "TARGET_HIT")
                return
            
            # Time-based exit (hold for maximum 2 hours for momentum)
            position_age = (datetime.now() - position.opened_at).total_seconds() / 3600
            if position_age > 2:  # 2 hours
                await self._exit_momentum_position(symbol, position, current_price, "TIME_EXIT")
                return
            
            # Partial profit booking if position is very profitable
            unrealized_pnl = position.unrealized_pnl
            entry_value = position.avg_price * abs(position.quantity)
            if unrealized_pnl > entry_value * 0.75:  # 75% profit
                # Book partial profits (50% of position)
                partial_qty = abs(position.quantity) // 2
                if partial_qty > 0:
                    await self._partial_exit_momentum_position(symbol, position, current_price, partial_qty, "PARTIAL_PROFIT")
                
        except Exception as e:
            self.logger.logger.error(f"Error managing momentum position for {symbol}: {e}")
    
    async def _exit_momentum_position(self, symbol: str, position, exit_price: float, reason: str):
        """Exit momentum position"""
        try:
            # Place sell order
            exit_params = {
                'symbol': symbol,
                'side': 'SELL',
                'quantity': abs(position.quantity),
                'order_type': 'LIMIT',  # Use limit order with slight buffer
                'price': round_to_tick_size(exit_price * 0.995),  # 0.5% below market for quick fill
                'strategy': self.name,
                'metadata': {
                    'exit_reason': reason,
                    'trade_type': 'momentum_exit'
                }
            }
            
            order_id = await self.place_trade(exit_params)
            
            if order_id:
                # Calculate and log PnL
                pnl = (exit_price - position.avg_price) * abs(position.quantity)
                is_winning = pnl > 0
                
                self.logger.logger.info(f"Momentum position exited: {symbol} {reason} PnL: {pnl:.2f}")
                
                # Update performance
                await self.update_performance(pnl, is_winning)
                
                # Clean up tracking
                if hasattr(self, 'active_momentum_trades') and symbol in self.active_momentum_trades:
                    del self.active_momentum_trades[symbol]
            
        except Exception as e:
            self.logger.logger.error(f"Error exiting momentum position for {symbol}: {e}")
    
    async def _partial_exit_momentum_position(self, symbol: str, position, exit_price: float, quantity: int, reason: str):
        """Partial exit of momentum position"""
        try:
            # Place partial sell order
            exit_params = {
                'symbol': symbol,
                'side': 'SELL',
                'quantity': quantity,
                'order_type': 'LIMIT',
                'price': round_to_tick_size(exit_price * 0.995),
                'strategy': self.name,
                'metadata': {
                    'exit_reason': reason,
                    'trade_type': 'momentum_partial_exit'
                }
            }
            
            order_id = await self.place_trade(exit_params)
            
            if order_id:
                partial_pnl = (exit_price - position.avg_price) * quantity
                self.logger.logger.info(f"Momentum partial exit: {symbol} {quantity} units, {reason}, PnL: {partial_pnl:.2f}")
                
                # Update performance for partial exit
                await self.update_performance(partial_pnl, partial_pnl > 0)
            
        except Exception as e:
            self.logger.logger.error(f"Error in partial exit for {symbol}: {e}")
    
    async def _update_option_greeks(self):
        """Update option Greeks for better trade selection"""
        try:
            # This would require market data for Greeks calculation
            # For now, we'll skip detailed Greeks calculation
            pass
            
        except Exception as e:
            self.logger.logger.error(f"Error updating option Greeks: {e}")
    
    def _calculate_sma(self, data: List[Dict], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(data) < period:
            return None
        
        prices = [tick['ltp'] for tick in data[-period:] if tick.get('ltp')]
        if len(prices) < period:
            return None
        
        return sum(prices) / len(prices)
    
    def _calculate_rsi(self, data: List[Dict], period: int) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return None
        
        prices = [tick['ltp'] for tick in data[-(period + 1):] if tick.get('ltp')]
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility"""
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
    
    async def _on_nifty_momentum_update(self, price_data: Dict[str, Any]):
        """Handle Nifty price updates for momentum analysis"""
        try:
            # Store price and volume data for momentum calculation
            self.price_momentum_history.append({
                'price': price_data.get('ltp'),
                'volume': price_data.get('volume', 0),
                'timestamp': datetime.now()
            })
            
            # Keep only recent data
            if len(self.price_momentum_history) > 100:
                self.price_momentum_history = self.price_momentum_history[-50:]
                
        except Exception as e:
            self.logger.logger.error(f"Error processing Nifty momentum update: {e}")
    
    async def cleanup(self):
        """Cleanup momentum strategy"""
        try:
            # Close any open momentum positions
            positions = self.position_manager.get_positions()
            
            for symbol, position in positions.items():
                if position.strategy == self.name:
                    current_price = self.data_manager.get_option_price(symbol)
                    if current_price:
                        await self._exit_momentum_position(symbol, position, current_price, "STRATEGY_SHUTDOWN")
            
            self.logger.logger.info("Momentum strategy cleanup completed")
            
        except Exception as e:
            self.logger.logger.error(f"Error in momentum strategy cleanup: {e}")
