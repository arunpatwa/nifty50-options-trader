"""
Real-time market data management for Nifty options
"""

import asyncio
import json
import websockets
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import threading
from collections import defaultdict

from src.utils.logger import TradingLogger
from src.api.dhan_client import DhanClient
from config.settings import DHAN_FEED_URL

class MarketDataManager:
    """Manages real-time market data feeds"""
    
    def __init__(self, dhan_client: DhanClient):
        self.logger = TradingLogger(__name__)
        self.dhan_client = dhan_client
        self.feed_url = DHAN_FEED_URL
        
        # WebSocket connection
        self.ws_connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Subscriptions and callbacks
        self.subscribed_symbols = set()
        self.price_callbacks = defaultdict(list)
        self.tick_callbacks = []
        
        # Market data storage
        self.latest_prices = {}
        self.option_chain_data = {}
        self.market_depth = {}
        
        # Control flags
        self.running = False
    
    async def connect(self) -> bool:
        """
        Connect to market data feed
        
        Returns:
            True if connection successful
        """
        try:
            if self.is_connected:
                return True
            
            headers = {
                'clientid': self.dhan_client.client_id,
                'accesstoken': self.dhan_client.access_token
            }
            
            self.ws_connection = await websockets.connect(
                self.feed_url,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            self.logger.logger.info("Connected to market data feed")
            
            # Start listening for messages
            asyncio.create_task(self._message_handler())
            
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Failed to connect to market data feed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from market data feed"""
        try:
            self.running = False
            
            if self.ws_connection:
                await self.ws_connection.close()
                self.is_connected = False
                self.logger.logger.info("Disconnected from market data feed")
            
        except Exception as e:
            self.logger.logger.error(f"Error disconnecting from feed: {e}")
    
    async def subscribe_symbol(self, symbol: str, segment: str = "NSE_FNO") -> bool:
        """
        Subscribe to price updates for a symbol
        
        Args:
            symbol: Trading symbol to subscribe
            segment: Market segment
            
        Returns:
            True if subscription successful
        """
        try:
            if not self.is_connected:
                if not await self.connect():
                    return False
            
            subscription_msg = {
                'action': 'subscribe',
                'symbol': symbol,
                'segment': segment,
                'mode': 'full'  # full, quote, or ltp
            }
            
            await self.ws_connection.send(json.dumps(subscription_msg))
            self.subscribed_symbols.add(f"{segment}:{symbol}")
            
            self.logger.logger.info(f"Subscribed to {symbol} ({segment})")
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Failed to subscribe to {symbol}: {e}")
            return False
    
    async def unsubscribe_symbol(self, symbol: str, segment: str = "NSE_FNO") -> bool:
        """
        Unsubscribe from price updates for a symbol
        
        Args:
            symbol: Trading symbol to unsubscribe
            segment: Market segment
            
        Returns:
            True if unsubscription successful
        """
        try:
            if not self.is_connected:
                return True
            
            unsubscription_msg = {
                'action': 'unsubscribe',
                'symbol': symbol,
                'segment': segment
            }
            
            await self.ws_connection.send(json.dumps(unsubscription_msg))
            self.subscribed_symbols.discard(f"{segment}:{symbol}")
            
            self.logger.logger.info(f"Unsubscribed from {symbol} ({segment})")
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Failed to unsubscribe from {symbol}: {e}")
            return False
    
    def add_price_callback(self, symbol: str, callback: Callable):
        """
        Add callback for price updates of a specific symbol
        
        Args:
            symbol: Trading symbol
            callback: Function to call on price update
        """
        self.price_callbacks[symbol].append(callback)
    
    def add_tick_callback(self, callback: Callable):
        """
        Add callback for all market ticks
        
        Args:
            callback: Function to call on every tick
        """
        self.tick_callbacks.append(callback)
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest price data for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price data or None if not available
        """
        return self.latest_prices.get(symbol)
    
    def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get last traded price for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Last traded price or None if not available
        """
        price_data = self.latest_prices.get(symbol)
        if price_data:
            return price_data.get('ltp')
        return None
    
    async def get_option_chain(self, underlying: str = "NIFTY", 
                              expiry: str = None) -> Optional[Dict[str, Any]]:
        """
        Get option chain data from API
        
        Args:
            underlying: Underlying symbol
            expiry: Expiry date
            
        Returns:
            Option chain data
        """
        try:
            option_chain = await self.dhan_client.get_option_chain(underlying, expiry)
            if option_chain:
                self.option_chain_data[underlying] = option_chain
                return option_chain
            return None
            
        except Exception as e:
            self.logger.logger.error(f"Error getting option chain: {e}")
            return None
    
    async def subscribe_option_chain(self, underlying: str = "NIFTY",
                                   expiry: str = None, strikes_range: int = 10):
        """
        Subscribe to option chain for real-time updates
        
        Args:
            underlying: Underlying symbol
            expiry: Expiry date
            strikes_range: Number of strikes on each side of ATM
        """
        try:
            # Get option chain first
            option_chain = await self.get_option_chain(underlying, expiry)
            if not option_chain:
                return
            
            # Get current spot price
            spot_quote = await self.dhan_client.get_market_quote(underlying, "NSE_EQ")
            if not spot_quote:
                return
            
            spot_price = spot_quote.get('ltp', 0)
            
            # Subscribe to relevant strikes
            subscribed_count = 0
            for option in option_chain.get('options', []):
                strike = option.get('strike_price', 0)
                
                # Only subscribe to strikes within range
                if abs(strike - spot_price) <= strikes_range * 50:  # Nifty strikes are in multiples of 50
                    # Subscribe to both call and put
                    call_symbol = option.get('call_symbol')
                    put_symbol = option.get('put_symbol')
                    
                    if call_symbol:
                        await self.subscribe_symbol(call_symbol, "NSE_FNO")
                        subscribed_count += 1
                    
                    if put_symbol:
                        await self.subscribe_symbol(put_symbol, "NSE_FNO")
                        subscribed_count += 1
            
            self.logger.logger.info(f"Subscribed to {subscribed_count} option symbols")
            
        except Exception as e:
            self.logger.logger.error(f"Error subscribing to option chain: {e}")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        self.running = True
        
        try:
            async for message in self.ws_connection:
                if not self.running:
                    break
                
                try:
                    data = json.loads(message)
                    await self._process_tick_data(data)
                    
                except json.JSONDecodeError as e:
                    self.logger.logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    self.logger.logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.logger.warning("WebSocket connection closed")
            self.is_connected = False
            
            # Attempt to reconnect if still running
            if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                self.logger.logger.info(f"Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
                await asyncio.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
                await self.connect()
                
        except Exception as e:
            self.logger.logger.error(f"Message handler error: {e}")
    
    async def _process_tick_data(self, data: Dict[str, Any]):
        """Process incoming tick data"""
        try:
            symbol = data.get('symbol')
            if not symbol:
                return
            
            # Update latest prices
            price_data = {
                'symbol': symbol,
                'ltp': data.get('ltp'),
                'bid': data.get('bid'),
                'ask': data.get('ask'),
                'volume': data.get('volume'),
                'oi': data.get('oi'),  # Open Interest
                'timestamp': datetime.now(),
                'change': data.get('change'),
                'change_percent': data.get('change_percent')
            }
            
            self.latest_prices[symbol] = price_data
            
            # Call symbol-specific callbacks
            for callback in self.price_callbacks.get(symbol, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(price_data)
                    else:
                        callback(price_data)
                except Exception as e:
                    self.logger.logger.error(f"Error in price callback: {e}")
            
            # Call general tick callbacks
            for callback in self.tick_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(price_data)
                    else:
                        callback(price_data)
                except Exception as e:
                    self.logger.logger.error(f"Error in tick callback: {e}")
                    
        except Exception as e:
            self.logger.logger.error(f"Error processing tick data: {e}")
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get summary of current market data"""
        return {
            'connected': self.is_connected,
            'subscribed_symbols': len(self.subscribed_symbols),
            'latest_prices_count': len(self.latest_prices),
            'reconnect_attempts': self.reconnect_attempts
        }
