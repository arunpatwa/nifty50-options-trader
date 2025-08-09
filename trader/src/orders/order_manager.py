"""
Order manager for handling order placement, modification, and tracking
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from src.utils.logger import TradingLogger
from src.api.dhan_client import DhanClient
from src.risk_management.position_manager import PositionManager
from config.settings import ORDER_TIMEOUT_SECONDS, MAX_RETRIES

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"

class Order:
    """Represents a trading order"""
    
    def __init__(self, symbol: str, side: str, quantity: int, 
                 order_type: str = "LIMIT", price: float = None, 
                 strategy: str = None):
        self.order_id = str(uuid.uuid4())
        self.broker_order_id = None
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.strategy = strategy
        
        # Status tracking
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.filled_price = 0.0
        self.average_price = 0.0
        
        # Timestamps
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.filled_at = None
        
        # Metadata
        self.error_message = None
        self.metadata = {}
    
    def update_status(self, status: OrderStatus, **kwargs):
        """Update order status"""
        self.status = status
        self.updated_at = datetime.now()
        
        if 'filled_quantity' in kwargs:
            self.filled_quantity = kwargs['filled_quantity']
        
        if 'filled_price' in kwargs:
            self.filled_price = kwargs['filled_price']
            
        if 'error_message' in kwargs:
            self.error_message = kwargs['error_message']
        
        if status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            if not self.filled_at:
                self.filled_at = datetime.now()
    
    def is_open(self) -> bool:
        """Check if order is open"""
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
    
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    def is_cancelled(self) -> bool:
        """Check if order is cancelled"""
        return self.status == OrderStatus.CANCELLED
    
    def get_remaining_quantity(self) -> int:
        """Get remaining unfilled quantity"""
        return self.quantity - self.filled_quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            'order_id': self.order_id,
            'broker_order_id': self.broker_order_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'price': self.price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'average_price': self.average_price,
            'strategy': self.strategy,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'error_message': self.error_message,
            'metadata': self.metadata
        }

class OrderManager:
    """Manages order placement, modification, and tracking"""
    
    def __init__(self, dhan_client: DhanClient, position_manager: PositionManager):
        self.logger = TradingLogger(__name__)
        self.dhan_client = dhan_client
        self.position_manager = position_manager
        
        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.broker_order_mapping: Dict[str, str] = {}  # broker_id -> our_order_id
        
        # Monitoring
        self.monitoring_active = False
        self.order_timeout = ORDER_TIMEOUT_SECONDS
        self.max_retries = MAX_RETRIES
    
    async def place_order(self, order_params: Dict[str, Any]) -> Optional[str]:
        """
        Place a new order
        
        Args:
            order_params: Order parameters
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            # Create order object
            order = Order(
                symbol=order_params['symbol'],
                side=order_params['side'],
                quantity=order_params['quantity'],
                order_type=order_params.get('order_type', 'LIMIT'),
                price=order_params.get('price'),
                strategy=order_params.get('strategy')
            )
            
            # Validate order
            if not self._validate_order(order):
                return None
            
            # Build Dhan API order payload
            dhan_order_params = self._build_dhan_order_params(order)
            
            # Place order with broker
            response = await self.dhan_client.place_order(dhan_order_params)
            
            if response and response.get('status') == 'success':
                broker_order_id = response.get('data', {}).get('orderId')
                order.broker_order_id = broker_order_id
                order.update_status(OrderStatus.OPEN)
                
                # Store order
                self.orders[order.order_id] = order
                if broker_order_id:
                    self.broker_order_mapping[broker_order_id] = order.order_id
                
                self.logger.logger.info(f"Order placed: {order.symbol} {order.side} {order.quantity} @ {order.price}")
                return order.order_id
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                order.update_status(OrderStatus.REJECTED, error_message=error_msg)
                self.orders[order.order_id] = order
                self.logger.logger.error(f"Order rejected: {error_msg}")
                return None
                
        except Exception as e:
            self.logger.logger.error(f"Error placing order: {e}")
            return None
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> bool:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            modifications: Fields to modify
            
        Returns:
            True if modification successful
        """
        try:
            if order_id not in self.orders:
                self.logger.logger.error(f"Order not found: {order_id}")
                return False
            
            order = self.orders[order_id]
            
            if not order.is_open():
                self.logger.logger.error(f"Order {order_id} is not open for modification")
                return False
            
            # Update local order
            for field, value in modifications.items():
                if hasattr(order, field):
                    setattr(order, field, value)
            
            # Modify order with broker
            if order.broker_order_id:
                response = await self.dhan_client.modify_order(order.broker_order_id, modifications)
                
                if response and response.get('status') == 'success':
                    order.updated_at = datetime.now()
                    self.logger.logger.info(f"Order modified: {order_id}")
                    return True
                else:
                    error_msg = response.get('message', 'Unknown error') if response else 'No response'
                    self.logger.logger.error(f"Order modification failed: {error_msg}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error modifying order {order_id}: {e}")
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancellation successful
        """
        try:
            if order_id not in self.orders:
                self.logger.logger.error(f"Order not found: {order_id}")
                return False
            
            order = self.orders[order_id]
            
            if not order.is_open():
                self.logger.logger.warning(f"Order {order_id} is not open for cancellation")
                return True  # Already not active
            
            # Cancel order with broker
            if order.broker_order_id:
                success = await self.dhan_client.cancel_order(order.broker_order_id)
                
                if success:
                    order.update_status(OrderStatus.CANCELLED)
                    self.logger.logger.info(f"Order cancelled: {order_id}")
                    return True
                else:
                    self.logger.logger.error(f"Order cancellation failed: {order_id}")
                    return False
            
            # If no broker order ID, just mark as cancelled
            order.update_status(OrderStatus.CANCELLED)
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """
        Cancel all open orders
        
        Returns:
            Number of orders cancelled
        """
        open_orders = [order_id for order_id, order in self.orders.items() if order.is_open()]
        cancelled_count = 0
        
        for order_id in open_orders:
            if await self.cancel_order(order_id):
                cancelled_count += 1
        
        self.logger.logger.info(f"Cancelled {cancelled_count} orders")
        return cancelled_count
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders(self, status: Optional[OrderStatus] = None, strategy: Optional[str] = None) -> List[Order]:
        """
        Get orders with optional filters
        
        Args:
            status: Filter by status
            strategy: Filter by strategy
            
        Returns:
            List of matching orders
        """
        orders = list(self.orders.values())
        
        if status:
            orders = [order for order in orders if order.status == status]
        
        if strategy:
            orders = [order for order in orders if order.strategy == strategy]
        
        return orders
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders"""
        return [order for order in self.orders.values() if order.is_open()]
    
    async def monitor_orders(self):
        """Monitor orders for status updates"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                await self._sync_order_status()
                await self._handle_timeouts()
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.logger.error(f"Error in order monitoring: {e}")
                await asyncio.sleep(10)
    
    async def stop_monitoring(self):
        """Stop order monitoring"""
        self.monitoring_active = False
    
    async def _sync_order_status(self):
        """Sync order status with broker"""
        try:
            # Get orders from broker
            broker_orders = await self.dhan_client.get_orders()
            if not broker_orders:
                return
            
            # Update local orders based on broker status
            for broker_order in broker_orders:
                broker_order_id = broker_order.get('orderId')
                if broker_order_id in self.broker_order_mapping:
                    local_order_id = self.broker_order_mapping[broker_order_id]
                    local_order = self.orders.get(local_order_id)
                    
                    if local_order:
                        await self._update_order_from_broker_data(local_order, broker_order)
                        
        except Exception as e:
            self.logger.logger.error(f"Error syncing order status: {e}")
    
    async def _update_order_from_broker_data(self, order: Order, broker_data: Dict[str, Any]):
        """Update local order from broker data"""
        try:
            broker_status = broker_data.get('orderStatus', '').upper()
            
            # Map broker status to our status
            status_mapping = {
                'OPEN': OrderStatus.OPEN,
                'FILLED': OrderStatus.FILLED,
                'CANCELLED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED,
                'PARTIAL': OrderStatus.PARTIALLY_FILLED
            }
            
            new_status = status_mapping.get(broker_status)
            if new_status and new_status != order.status:
                # Update filled quantity if available
                filled_qty = broker_data.get('filledQty', 0)
                filled_price = broker_data.get('avgPrice', 0.0)
                
                order.update_status(
                    new_status,
                    filled_quantity=filled_qty,
                    filled_price=filled_price
                )
                
                # If filled, update position
                if new_status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED] and filled_qty > 0:
                    await self._handle_fill(order, filled_qty, filled_price)
                    
        except Exception as e:
            self.logger.logger.error(f"Error updating order from broker data: {e}")
    
    async def _handle_fill(self, order: Order, filled_qty: int, filled_price: float):
        """Handle order fill"""
        try:
            # Update position
            position_qty = filled_qty if order.side == 'BUY' else -filled_qty
            self.position_manager.add_position(
                symbol=order.symbol,
                quantity=position_qty,
                price=filled_price,
                strategy=order.strategy
            )
            
            self.logger.logger.info(f"Order fill handled: {order.symbol} {filled_qty}@{filled_price}")
            
        except Exception as e:
            self.logger.logger.error(f"Error handling order fill: {e}")
    
    async def _handle_timeouts(self):
        """Handle order timeouts"""
        current_time = datetime.now()
        
        for order in self.orders.values():
            if order.is_open():
                time_since_creation = (current_time - order.created_at).total_seconds()
                
                if time_since_creation > self.order_timeout:
                    self.logger.logger.warning(f"Order timeout: {order.order_id}")
                    await self.cancel_order(order.order_id)
    
    def _validate_order(self, order: Order) -> bool:
        """Validate order parameters"""
        if not order.symbol:
            self.logger.logger.error("Order validation failed: No symbol")
            return False
        
        if order.side not in ['BUY', 'SELL']:
            self.logger.logger.error(f"Order validation failed: Invalid side {order.side}")
            return False
        
        if order.quantity <= 0:
            self.logger.logger.error(f"Order validation failed: Invalid quantity {order.quantity}")
            return False
        
        if order.order_type == 'LIMIT' and (not order.price or order.price <= 0):
            self.logger.logger.error(f"Order validation failed: Invalid price {order.price}")
            return False
        
        return True
    
    def _build_dhan_order_params(self, order: Order) -> Dict[str, Any]:
        """Build Dhan API order parameters"""
        return {
            'trading_symbol': order.symbol,
            'transaction_type': order.side,
            'exchange_segment': 'NSE_FNO',  # Assuming options trading
            'product_type': 'INTRADAY',
            'order_type': order.order_type,
            'quantity': order.quantity,
            'price': order.price if order.order_type == 'LIMIT' else 0,
            'validity': 'DAY'
        }
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get order management summary"""
        open_orders = self.get_open_orders()
        filled_orders = [order for order in self.orders.values() if order.is_filled()]
        cancelled_orders = [order for order in self.orders.values() if order.is_cancelled()]
        
        return {
            'total_orders': len(self.orders),
            'open_orders': len(open_orders),
            'filled_orders': len(filled_orders),
            'cancelled_orders': len(cancelled_orders),
            'monitoring_active': self.monitoring_active
        }
