import os
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic import validator
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

class TradingSettings(BaseSettings):
    """Trading configuration settings"""
    
    # Dhan API Configuration
    dhan_client_id: str = os.getenv('DHAN_CLIENT_ID', '')
    dhan_access_token: str = os.getenv('DHAN_ACCESS_TOKEN', '')
    
    # Trading Parameters
    nifty_symbol: str = os.getenv('NIFTY_SYMBOL', 'NIFTY')
    default_quantity: int = int(os.getenv('DEFAULT_QUANTITY', '25'))
    max_positions: int = int(os.getenv('MAX_POSITIONS', '5'))
    risk_per_trade: float = float(os.getenv('RISK_PER_TRADE', '0.02'))
    daily_loss_limit: float = float(os.getenv('DAILY_LOSS_LIMIT', '5000'))
    portfolio_limit: float = float(os.getenv('PORTFOLIO_LIMIT', '100000'))
    
    # Market Hours
    market_start_time: str = os.getenv('MARKET_START_TIME', '09:15')
    market_end_time: str = os.getenv('MARKET_END_TIME', '15:30')
    
    # Notifications
    telegram_bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')
    enable_telegram_notifications: bool = os.getenv('ENABLE_TELEGRAM_NOTIFICATIONS', 'false').lower() == 'true'
    
    # Dashboard
    dashboard_host: str = os.getenv('DASHBOARD_HOST', 'localhost')
    dashboard_port: int = int(os.getenv('DASHBOARD_PORT', '8050'))
    dashboard_debug: bool = os.getenv('DASHBOARD_DEBUG', 'false').lower() == 'true'
    
    # Database
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./trading_data.db')
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', 'logs/trading.log')
    
    @validator('risk_per_trade')
    def validate_risk_per_trade(cls, v):
        if not 0 < v <= 0.1:  # Max 10% risk per trade
            raise ValueError('Risk per trade must be between 0 and 0.1 (10%)')
        return v
    
    @validator('default_quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Default quantity must be positive')
        return v

# Global settings instance
settings = TradingSettings()

# API Configuration
DHAN_API_BASE_URL = "https://dhanhq.co/api"
DHAN_FEED_URL = "wss://api-feed.dhan.co"

# Market Configuration
NIFTY_INDEX_SYMBOL = "NIFTY 50"
OPTIONS_SEGMENT = "NSE_FNO"

# Risk Management Defaults
DEFAULT_STOP_LOSS_PERCENTAGE = 0.20  # 20% stop loss
DEFAULT_TARGET_PERCENTAGE = 0.30     # 30% target
MAX_CONCURRENT_TRADES = 3

# Strategy Configuration
SCALPING_TIMEFRAME = "1min"
MOMENTUM_TIMEFRAME = "5min"
SWING_TIMEFRAME = "15min"

# Order Configuration
ORDER_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1
