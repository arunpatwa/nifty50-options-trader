"""
Helper utilities for the trading bot
"""

import asyncio
from datetime import datetime, time
import pytz
from typing import Optional, Dict, Any, List
import math
from decimal import Decimal, ROUND_HALF_UP

def is_market_open() -> bool:
    """
    Check if the market is currently open (NSE timings in IST)
    
    Returns:
        bool: True if market is open, False otherwise
    """
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist).time()
    
    # Market hours: 9:15 AM to 3:30 PM IST
    market_start = time(9, 15)
    market_end = time(15, 30)
    
    # Check if current day is a weekday (Monday = 0, Sunday = 6)
    current_day = datetime.now(ist).weekday()
    is_weekday = current_day < 5  # Monday to Friday
    
    return is_weekday and market_start <= current_time <= market_end

def get_market_status() -> Dict[str, Any]:
    """
    Get detailed market status information
    
    Returns:
        Dictionary with market status details
    """
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    current_time = now.time()
    current_day = now.weekday()
    
    market_start = time(9, 15)
    market_end = time(15, 30)
    
    is_weekday = current_day < 5
    is_open = is_weekday and market_start <= current_time <= market_end
    
    status = {
        'is_open': is_open,
        'is_weekday': is_weekday,
        'current_time': current_time.strftime('%H:%M:%S'),
        'market_start': market_start.strftime('%H:%M:%S'),
        'market_end': market_end.strftime('%H:%M:%S'),
        'day_name': now.strftime('%A')
    }
    
    if not is_open:
        if not is_weekday:
            status['reason'] = 'Weekend'
        elif current_time < market_start:
            status['reason'] = 'Before market hours'
        else:
            status['reason'] = 'After market hours'
    
    return status

def calculate_option_greeks(spot_price: float, strike_price: float, 
                          time_to_expiry: float, volatility: float,
                          risk_free_rate: float = 0.06, option_type: str = 'call') -> Dict[str, float]:
    """
    Calculate basic option Greeks using Black-Scholes model
    
    Args:
        spot_price: Current price of underlying
        strike_price: Strike price of option
        time_to_expiry: Time to expiry in years
        volatility: Implied volatility
        risk_free_rate: Risk-free rate (default 6% for India)
        option_type: 'call' or 'put'
    
    Returns:
        Dictionary with calculated Greeks
    """
    try:
        from scipy.stats import norm
        import numpy as np
        
        S = spot_price
        K = strike_price
        T = time_to_expiry
        r = risk_free_rate
        sigma = volatility
        
        # Calculate d1 and d2
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        
        # Calculate Greeks
        if option_type.lower() == 'call':
            delta = norm.cdf(d1)
            theta = -(S*norm.pdf(d1)*sigma)/(2*np.sqrt(T)) - r*K*np.exp(-r*T)*norm.cdf(d2)
        else:  # put
            delta = norm.cdf(d1) - 1
            theta = -(S*norm.pdf(d1)*sigma)/(2*np.sqrt(T)) + r*K*np.exp(-r*T)*norm.cdf(-d2)
        
        gamma = norm.pdf(d1) / (S*sigma*np.sqrt(T))
        vega = S*norm.pdf(d1)*np.sqrt(T) / 100  # Per 1% change in volatility
        rho = K*T*np.exp(-r*T)*norm.cdf(d2) / 100 if option_type.lower() == 'call' else -K*T*np.exp(-r*T)*norm.cdf(-d2) / 100
        
        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 4),
            'theta': round(theta, 2),
            'vega': round(vega, 2),
            'rho': round(rho, 2)
        }
        
    except ImportError:
        # If scipy is not available, return basic estimates
        return {
            'delta': 0.5,
            'gamma': 0.01,
            'theta': -1.0,
            'vega': 10.0,
            'rho': 5.0
        }
    except Exception as e:
        print(f"Error calculating Greeks: {e}")
        return {}

def round_to_tick_size(price: float, tick_size: float = 0.05) -> float:
    """
    Round price to nearest tick size
    
    Args:
        price: Price to round
        tick_size: Tick size (default 0.05 for Nifty options)
    
    Returns:
        Rounded price
    """
    return round(price / tick_size) * tick_size

def calculate_position_size(account_balance: float, risk_per_trade: float,
                          entry_price: float, stop_loss_price: float,
                          lot_size: int = 25) -> int:
    """
    Calculate position size based on risk management
    
    Args:
        account_balance: Total account balance
        risk_per_trade: Risk percentage per trade (e.g., 0.02 for 2%)
        entry_price: Entry price per unit
        stop_loss_price: Stop loss price per unit
        lot_size: Minimum lot size (default 25 for Nifty)
    
    Returns:
        Position size in lots
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0
    
    # Calculate risk per unit
    risk_per_unit = abs(entry_price - stop_loss_price)
    
    if risk_per_unit <= 0:
        return 0
    
    # Calculate maximum risk amount
    max_risk_amount = account_balance * risk_per_trade
    
    # Calculate maximum units
    max_units = max_risk_amount / risk_per_unit
    
    # Convert to lots and round down
    lots = int(max_units / lot_size)
    
    return max(0, lots)

def get_nearest_strikes(spot_price: float, count: int = 10) -> List[float]:
    """
    Get nearest strike prices around the spot price
    
    Args:
        spot_price: Current spot price
        count: Number of strikes on each side
    
    Returns:
        List of strike prices
    """
    # Nifty strikes are typically in multiples of 50
    strike_interval = 50
    
    # Find nearest strike
    nearest_strike = round(spot_price / strike_interval) * strike_interval
    
    strikes = []
    for i in range(-count, count + 1):
        strike = nearest_strike + (i * strike_interval)
        if strike > 0:
            strikes.append(strike)
    
    return sorted(strikes)

def format_currency(amount: float) -> str:
    """
    Format amount as Indian currency
    
    Args:
        amount: Amount to format
    
    Returns:
        Formatted string
    """
    if amount >= 10000000:  # 1 crore
        return f"₹{amount/10000000:.2f}Cr"
    elif amount >= 100000:  # 1 lakh
        return f"₹{amount/100000:.2f}L"
    elif amount >= 1000:  # 1 thousand
        return f"₹{amount/1000:.2f}K"
    else:
        return f"₹{amount:.2f}"

def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on exception
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise last_exception
            
        return wrapper
    return decorator

def get_expiry_dates() -> List[str]:
    """
    Get next few expiry dates for Nifty options
    
    Returns:
        List of expiry dates in YYYY-MM-DD format
    """
    from datetime import datetime, timedelta
    
    expiries = []
    current_date = datetime.now()
    
    # Find next few Thursdays (Nifty expiry day)
    days_until_thursday = (3 - current_date.weekday()) % 7
    if days_until_thursday == 0 and current_date.hour >= 15:  # After 3 PM on Thursday
        days_until_thursday = 7
    
    next_thursday = current_date + timedelta(days=days_until_thursday)
    
    for i in range(4):  # Next 4 expiries
        expiry_date = next_thursday + timedelta(weeks=i)
        expiries.append(expiry_date.strftime('%Y-%m-%d'))
    
    return expiries
