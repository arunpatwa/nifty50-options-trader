"""
Data manager for handling market data, storage, and analysis
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import json

from src.utils.logger import TradingLogger
from src.api.dhan_client import DhanClient
from src.api.market_data import MarketDataManager
from src.utils.helpers import get_nearest_strikes, get_expiry_dates

class DataManager:
    """Central data management system"""
    
    def __init__(self, dhan_client: DhanClient):
        self.logger = TradingLogger(__name__)
        self.dhan_client = dhan_client
        self.market_data = MarketDataManager(dhan_client)
        
        # Data storage
        self.price_history = {}  # Symbol -> deque of price data
        self.option_data = {}    # Strike -> option data
        self.nifty_data = deque(maxlen=1000)  # Last 1000 Nifty ticks
        
        # Configuration
        self.history_length = 500  # Number of ticks to keep
        self.current_expiry = None
        self.monitored_strikes = []
        
        # Analysis data
        self.technical_indicators = {}
        self.volatility_data = {}
    
    async def initialize(self) -> bool:
        """
        Initialize data manager and start data feeds
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.logger.info("Initializing data manager...")
            
            # Connect to market data feed
            if not await self.market_data.connect():
                return False
            
            # Get current expiry dates
            expiry_dates = get_expiry_dates()
            if expiry_dates:
                self.current_expiry = expiry_dates[0]
                self.logger.logger.info(f"Using expiry: {self.current_expiry}")
            
            # Subscribe to Nifty index
            await self.market_data.subscribe_symbol("NIFTY 50", "NSE_EQ")
            
            # Add price callback for Nifty
            self.market_data.add_price_callback("NIFTY 50", self._on_nifty_tick)
            
            # Subscribe to option chain
            await self._setup_option_monitoring()
            
            self.logger.logger.info("Data manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Failed to initialize data manager: {e}")
            return False
    
    async def start_market_data_feed(self):
        """Start real-time market data feed"""
        try:
            if not await self.market_data.connect():
                self.logger.logger.error("Failed to start market data feed")
                return
            
            self.logger.logger.info("Market data feed started")
            
        except Exception as e:
            self.logger.logger.error(f"Error starting market data feed: {e}")
    
    async def stop_market_data_feed(self):
        """Stop market data feed"""
        try:
            await self.market_data.disconnect()
            self.logger.logger.info("Market data feed stopped")
            
        except Exception as e:
            self.logger.logger.error(f"Error stopping market data feed: {e}")
    
    def get_nifty_price(self) -> Optional[float]:
        """
        Get current Nifty price
        
        Returns:
            Current Nifty price or None
        """
        if self.nifty_data:
            return self.nifty_data[-1].get('ltp')
        return None
    
    def get_nifty_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent Nifty price data
        
        Args:
            count: Number of recent ticks to return
            
        Returns:
            List of price data
        """
        if not self.nifty_data:
            return []
        
        return list(self.nifty_data)[-count:]
    
    def get_option_price(self, symbol: str) -> Optional[float]:
        """
        Get current option price
        
        Args:
            symbol: Option symbol
            
        Returns:
            Current option price or None
        """
        return self.market_data.get_ltp(symbol)
    
    def get_option_data(self, strike: float, option_type: str) -> Optional[Dict[str, Any]]:
        """
        Get option data for a specific strike and type
        
        Args:
            strike: Strike price
            option_type: 'call' or 'put'
            
        Returns:
            Option data or None
        """
        key = f"{strike}_{option_type.upper()}"
        return self.option_data.get(key)
    
    def get_atm_options(self) -> Dict[str, Any]:
        """
        Get at-the-money call and put option data
        
        Returns:
            Dictionary with ATM call and put data
        """
        nifty_price = self.get_nifty_price()
        if not nifty_price:
            return {}
        
        # Find nearest strike
        atm_strike = round(nifty_price / 50) * 50
        
        return {
            'strike': atm_strike,
            'call': self.get_option_data(atm_strike, 'call'),
            'put': self.get_option_data(atm_strike, 'put')
        }
    
    def get_option_chain_summary(self, strikes_range: int = 5) -> Dict[str, Any]:
        """
        Get option chain summary around current price
        
        Args:
            strikes_range: Number of strikes on each side
            
        Returns:
            Option chain summary
        """
        nifty_price = self.get_nifty_price()
        if not nifty_price:
            return {}
        
        strikes = get_nearest_strikes(nifty_price, strikes_range)
        chain_data = {
            'underlying_price': nifty_price,
            'strikes': []
        }
        
        for strike in strikes:
            call_data = self.get_option_data(strike, 'call')
            put_data = self.get_option_data(strike, 'put')
            
            strike_info = {
                'strike': strike,
                'call': {
                    'ltp': call_data.get('ltp') if call_data else None,
                    'volume': call_data.get('volume') if call_data else None,
                    'oi': call_data.get('oi') if call_data else None
                },
                'put': {
                    'ltp': put_data.get('ltp') if put_data else None,
                    'volume': put_data.get('volume') if put_data else None,
                    'oi': put_data.get('oi') if put_data else None
                }
            }
            
            chain_data['strikes'].append(strike_info)
        
        return chain_data
    
    def calculate_simple_moving_average(self, period: int = 20) -> Optional[float]:
        """
        Calculate simple moving average for Nifty
        
        Args:
            period: Period for moving average
            
        Returns:
            SMA value or None
        """
        if len(self.nifty_data) < period:
            return None
        
        prices = [tick['ltp'] for tick in list(self.nifty_data)[-period:] if tick.get('ltp')]
        if len(prices) < period:
            return None
        
        return sum(prices) / len(prices)
    
    def calculate_price_change(self, period: int = 10) -> Optional[float]:
        """
        Calculate price change over period
        
        Args:
            period: Number of ticks to look back
            
        Returns:
            Price change or None
        """
        if len(self.nifty_data) < period + 1:
            return None
        
        current_price = self.nifty_data[-1].get('ltp')
        past_price = self.nifty_data[-period-1].get('ltp')
        
        if current_price and past_price:
            return current_price - past_price
        
        return None
    
    def calculate_volatility(self, period: int = 20) -> Optional[float]:
        """
        Calculate price volatility
        
        Args:
            period: Period for volatility calculation
            
        Returns:
            Volatility value or None
        """
        if len(self.nifty_data) < period + 1:
            return None
        
        prices = [tick['ltp'] for tick in list(self.nifty_data)[-period:] if tick.get('ltp')]
        if len(prices) < period:
            return None
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if len(returns) < 2:
            return None
        
        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        
        return variance ** 0.5
    
    def get_market_trend(self) -> str:
        """
        Determine current market trend
        
        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if len(self.nifty_data) < 20:
            return 'neutral'
        
        sma_short = self.calculate_simple_moving_average(5)
        sma_long = self.calculate_simple_moving_average(20)
        price_change = self.calculate_price_change(10)
        
        if not sma_short or not sma_long or price_change is None:
            return 'neutral'
        
        # Determine trend based on moving averages and price change
        if sma_short > sma_long and price_change > 0:
            return 'bullish'
        elif sma_short < sma_long and price_change < 0:
            return 'bearish'
        else:
            return 'neutral'
    
    async def _setup_option_monitoring(self):
        """Setup option chain monitoring"""
        try:
            if not self.current_expiry:
                return
            
            # Get current Nifty price to determine strikes to monitor
            spot_quote = await self.dhan_client.get_market_quote("NIFTY 50", "NSE_EQ")
            if not spot_quote:
                return
            
            spot_price = spot_quote.get('ltp', 20000)  # Default if no price
            strikes = get_nearest_strikes(spot_price, 10)  # Monitor 10 strikes on each side
            
            self.monitored_strikes = strikes
            
            # Subscribe to option chain
            await self.market_data.subscribe_option_chain("NIFTY", self.current_expiry, 10)
            
        except Exception as e:
            self.logger.logger.error(f"Error setting up option monitoring: {e}")
    
    async def _on_nifty_tick(self, price_data: Dict[str, Any]):
        """Handle Nifty price updates"""
        try:
            self.nifty_data.append(price_data)
            
            # Update technical indicators periodically
            if len(self.nifty_data) % 10 == 0:  # Every 10 ticks
                self._update_technical_indicators()
                
        except Exception as e:
            self.logger.logger.error(f"Error processing Nifty tick: {e}")
    
    def _update_technical_indicators(self):
        """Update technical indicators"""
        try:
            self.technical_indicators.update({
                'sma_5': self.calculate_simple_moving_average(5),
                'sma_20': self.calculate_simple_moving_average(20),
                'price_change_10': self.calculate_price_change(10),
                'volatility_20': self.calculate_volatility(20),
                'trend': self.get_market_trend()
            })
            
        except Exception as e:
            self.logger.logger.error(f"Error updating technical indicators: {e}")
    
    def get_technical_indicators(self) -> Dict[str, Any]:
        """Get current technical indicators"""
        return self.technical_indicators.copy()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data state"""
        return {
            'nifty_ticks': len(self.nifty_data),
            'nifty_price': self.get_nifty_price(),
            'monitored_strikes': len(self.monitored_strikes),
            'current_expiry': self.current_expiry,
            'market_data_connected': self.market_data.is_connected,
            'technical_indicators': self.technical_indicators
        }
