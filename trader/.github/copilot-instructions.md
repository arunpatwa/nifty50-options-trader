<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Nifty 50 Options Trading Bot - Copilot Instructions

## Project Context
This is an automated trading system for Nifty 50 options using the Dhan API. The system includes:

- Real-time market data processing
- Multiple trading strategies (scalping, momentum, mean reversion)
- Risk management and position sizing
- Order execution and management
- Web-based dashboard for monitoring
- Telegram notifications
- Backtesting capabilities

## Code Style Guidelines

### Python Standards
- Use Python 3.8+ features
- Follow PEP 8 coding standards
- Use type hints for all function parameters and return types
- Use dataclasses or Pydantic models for data structures
- Implement proper error handling with specific exceptions

### Trading System Specific
- Always validate market data before processing
- Implement proper position sizing calculations
- Use decimal.Decimal for financial calculations to avoid floating-point errors
- Log all trading decisions and order executions
- Implement circuit breakers for risk management
- Use async/await for API calls and real-time data processing

### API Integration
- Use proper authentication and token management for Dhan API
- Implement retry logic with exponential backoff for API failures
- Cache market data appropriately to avoid rate limits
- Handle WebSocket connections with proper reconnection logic

### Risk Management
- Always calculate position size based on account balance and risk parameters
- Implement stop-loss and take-profit levels for all trades
- Monitor portfolio exposure and prevent over-leveraging
- Log all risk calculations and decisions

### Testing
- Write unit tests for all strategy logic
- Mock API calls in tests
- Test risk management functions thoroughly
- Include backtesting validation

## Dependencies and Libraries
- Use `requests` and `aiohttp` for HTTP API calls
- Use `websocket-client` for real-time data streams
- Use `pandas` and `numpy` for data analysis
- Use `pydantic` for data validation
- Use `loguru` for logging
- Use `dash` and `plotly` for web dashboard
- Use `python-telegram-bot` for notifications

## Security Considerations
- Never hardcode API keys or sensitive credentials
- Use environment variables for configuration
- Implement proper input validation
- Log security-relevant events
- Use secure WebSocket connections (WSS) where available

## Performance Guidelines
- Use connection pooling for HTTP requests
- Implement caching for frequently accessed data
- Use batch operations where possible
- Monitor memory usage for large datasets
- Implement proper cleanup of resources
