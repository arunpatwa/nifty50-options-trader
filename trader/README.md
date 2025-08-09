# Nifty 50 Options Automated Trader

An advanced Python-based automated trading system for Nifty 50 options using the Dhan API. This system provides real-time market data processing, strategy implementation, risk management, and automated order execution.

## Features

- **Real-time Market Data**: Live options chain data and market feeds
- **Multiple Trading Strategies**: Scalping, swing, and momentum-based strategies
- **Risk Management**: Position sizing, stop-loss, and portfolio risk controls
- **Order Management**: Automated order placement, modification, and tracking
- **Backtesting Engine**: Historical strategy testing and performance analysis
- **Web Dashboard**: Real-time monitoring and control interface
- **Telegram Integration**: Trade notifications and alerts
- **Database Logging**: Complete trade history and performance tracking

## Project Structure

```
trader/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── config.yaml
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dhan_client.py
│   │   └── market_data.py
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base_strategy.py
│   │   ├── scalping.py
│   │   └── momentum.py
│   ├── risk_management/
│   │   ├── __init__.py
│   │   ├── position_manager.py
│   │   └── risk_calculator.py
│   ├── orders/
│   │   ├── __init__.py
│   │   ├── order_manager.py
│   │   └── execution_engine.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── data_manager.py
│   │   └── database.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── helpers.py
├── dashboard/
│   ├── __init__.py
│   ├── app.py
│   └── components/
├── backtesting/
│   ├── __init__.py
│   ├── backtest_engine.py
│   └── performance_analyzer.py
├── notifications/
│   ├── __init__.py
│   └── telegram_bot.py
├── tests/
│   ├── __init__.py
│   ├── test_strategies.py
│   ├── test_api.py
│   └── test_risk_management.py
├── logs/
├── data/
├── .env
├── main.py
├── requirements.txt
└── README.md
```

## Setup Instructions

1. **Clone and Navigate**:
   ```bash
   cd /home/sherlock/nifty50-options-trader/trader
   ```

2. **Create Virtual Environment** (if not already created):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Linux/Mac
   # or
   .venv\Scripts\activate  # On Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env file with your settings
   nano .env  # or use your preferred editor
   ```
   
   **Important**: Add your actual Dhan API credentials:
   ```env
   DHAN_CLIENT_ID=your_actual_client_id
   DHAN_ACCESS_TOKEN=your_actual_access_token
   ```

5. **Test the System**:
   ```bash
   python tests/test_system.py
   ```

6. **Run the Application**:
   ```bash
   # For full automated trading
   python main.py
   
   # For example/demo mode
   python example.py
   
   # For dashboard only (monitoring)
   python example.py dashboard
   ```

7. **Access Dashboard**:
   - Open http://localhost:8050 for the web interface
   - Monitor positions, P&L, and strategy performance

## Configuration

Edit the `.env` file with your settings:

```env
# Dhan API Configuration
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Trading Configuration
NIFTY_SYMBOL=NIFTY
DEFAULT_QUANTITY=25
MAX_POSITIONS=5
RISK_PER_TRADE=0.02

# Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

### Basic Trading
```python
from src.api.dhan_client import DhanClient
from src.strategies.scalping import ScalpingStrategy

# Initialize
client = DhanClient()
strategy = ScalpingStrategy()

# Start automated trading
strategy.run()
```

### Risk Management
```python
from src.risk_management.position_manager import PositionManager

pm = PositionManager()
pm.set_max_risk_per_trade(0.02)  # 2% risk per trade
pm.set_portfolio_limit(100000)   # 1 lakh portfolio limit
```

## Strategies Included

1. **Scalping Strategy**: Quick in-and-out trades based on price action
2. **Momentum Strategy**: Trend-following approach for options
3. **Mean Reversion**: Counter-trend strategy for oversold/overbought conditions

## Safety Features

- **Position Limits**: Maximum positions per strategy
- **Daily Loss Limit**: Automatic trading halt on losses
- **Connection Monitoring**: Auto-reconnection for API failures
- **Error Handling**: Comprehensive exception management
- **Logging**: Detailed trade and system logs

## Disclaimer

This software is for educational purposes only. Trading in options involves substantial risk and is not suitable for all investors. Past performance does not guarantee future results. Use at your own risk.

## License

MIT License - see LICENSE file for details
