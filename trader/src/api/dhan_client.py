"""
Dhan API Client for automated trading
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.utils.logger import TradingLogger
from config.settings import settings, DHAN_API_BASE_URL

class DhanClient:
    """Dhan API client for trading operations"""
    
    def __init__(self):
        self.logger = TradingLogger(__name__)
        self.base_url = DHAN_API_BASE_URL
        self.client_id = settings.dhan_client_id
        self.access_token = settings.dhan_access_token
        self.session = None
        self.authenticated = False
        
        # API endpoints
        self.endpoints = {
            'orders': '/v2/orders',
            'positions': '/v2/positions',
            'funds': '/v2/funds',
        }
    
    async def initialize(self):
        """Initialize the client session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return await self.authenticate()
    
    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'clientid': self.client_id,
            'accesstoken': self.access_token
        }
    
    async def authenticate(self) -> bool:
        """Authenticate with Dhan API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = self._get_headers()
            url = f"{self.base_url}{self.endpoints['funds']}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    self.authenticated = True
                    self.logger.logger.info("Dhan API authentication successful")
                    return True
                else:
                    error_msg = await response.text()
                    self.logger.logger.error(f"Authentication failed: {error_msg}")
                    return False
                    
        except Exception as e:
            self.logger.logger.error(f"Authentication error: {e}")
            return False
    
    async def get_funds(self) -> Optional[Dict[str, Any]]:
        """Get funds information"""
        try:
            if not await self._ensure_authenticated():
                return None
            
            headers = self._get_headers()
            url = f"{self.base_url}{self.endpoints['funds']}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {})
                else:
                    error_msg = await response.text()
                    self.logger.logger.error(f"Failed to get funds: {error_msg}")
                    return None
                    
        except Exception as e:
            self.logger.logger.error(f"Error getting funds: {e}")
            return None
    
    async def get_orders(self) -> Optional[List[Dict[str, Any]]]:
        """Get all orders"""
        try:
            if not await self._ensure_authenticated():
                return None
            
            headers = self._get_headers()
            url = f"{self.base_url}{self.endpoints['orders']}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', [])
                else:
                    error_msg = await response.text()
                    self.logger.logger.error(f"Failed to get orders: {error_msg}")
                    return None
                    
        except Exception as e:
            self.logger.logger.error(f"Error getting orders: {e}")
            return None
    
    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Get all positions"""
        try:
            if not await self._ensure_authenticated():
                return None
            
            headers = self._get_headers()
            url = f"{self.base_url}{self.endpoints['positions']}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', [])
                else:
                    error_msg = await response.text()
                    self.logger.logger.error(f"Failed to get positions: {error_msg}")
                    return None
                    
        except Exception as e:
            self.logger.logger.error(f"Error getting positions: {e}")
            return None
    
    async def place_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Place a trading order"""
        try:
            if not await self._ensure_authenticated():
                return None
            
            headers = self._get_headers()
            url = f"{self.base_url}{self.endpoints['orders']}"
            
            async with self.session.post(url, headers=headers, json=order_data) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    order_id = result.get('data', {}).get('orderId')
                    self.logger.logger.info(f"Order placed successfully: {order_id}")
                    return order_id
                else:
                    error_msg = result.get('message', 'Unknown error')
                    self.logger.logger.error(f"Failed to place order: {error_msg}")
                    return None
                    
        except Exception as e:
            self.logger.logger.error(f"Error placing order: {e}")
            return None
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure client is authenticated"""
        if not self.authenticated:
            return await self.authenticate()
        return True
