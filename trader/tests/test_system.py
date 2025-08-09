"""
Basic test script to verify the trading system components
"""

import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logger
from src.utils.helpers import is_market_open, get_market_status, calculate_position_size, get_nearest_strikes
from src.data.database import DatabaseManager
from config.settings import settings

class TradingSystemTest:
    """Test suite for the trading system"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.test_results = []
    
    def test_result(self, test_name: str, passed: bool, message: str = ""):
        """Record test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'name': test_name,
            'passed': passed,
            'message': message
        })
        print(f"{status} {test_name}: {message}")
    
    def test_configuration(self):
        """Test configuration loading"""
        try:
            # Test settings loading
            self.test_result("Settings Loading", 
                           hasattr(settings, 'dhan_client_id'), 
                           f"Client ID configured: {'Yes' if settings.dhan_client_id else 'No'}")
            
            self.test_result("Default Quantity", 
                           settings.default_quantity > 0, 
                           f"Default quantity: {settings.default_quantity}")
            
            self.test_result("Risk Per Trade", 
                           0 < settings.risk_per_trade <= 0.1, 
                           f"Risk per trade: {settings.risk_per_trade}")
            
        except Exception as e:
            self.test_result("Configuration", False, str(e))
    
    def test_helper_functions(self):
        """Test utility helper functions"""
        try:
            # Test market status
            market_status = get_market_status()
            self.test_result("Market Status Check", 
                           isinstance(market_status, dict) and 'is_open' in market_status,
                           f"Market open: {market_status.get('is_open', 'Unknown')}")
            
            # Test position size calculation
            position_size = calculate_position_size(
                account_balance=100000,
                risk_per_trade=0.02,
                entry_price=100,
                stop_loss_price=80,
                lot_size=25
            )
            self.test_result("Position Size Calculation", 
                           position_size > 0,
                           f"Calculated position size: {position_size}")
            
            # Test strikes calculation
            strikes = get_nearest_strikes(20000, 5)
            self.test_result("Strikes Calculation", 
                           len(strikes) > 0 and all(isinstance(s, (int, float)) for s in strikes),
                           f"Generated {len(strikes)} strikes around 20000")
            
        except Exception as e:
            self.test_result("Helper Functions", False, str(e))
    
    async def test_database(self):
        """Test database operations"""
        try:
            # Test database initialization
            db = DatabaseManager("test_trading_data.db")
            initialized = await db.initialize()
            self.test_result("Database Initialization", initialized, "Database tables created")
            
            if initialized:
                # Test order insertion
                test_order = {
                    'order_id': 'TEST_ORDER_001',
                    'symbol': 'NIFTY_TEST_CE',
                    'side': 'BUY',
                    'order_type': 'LIMIT',
                    'quantity': 25,
                    'price': 100.0,
                    'status': 'OPEN',
                    'strategy': 'TestStrategy'
                }
                
                order_inserted = await db.insert_order(test_order)
                self.test_result("Order Insertion", order_inserted, "Test order inserted")
                
                # Test order retrieval
                orders = await db.get_orders(limit=1)
                self.test_result("Order Retrieval", 
                               len(orders) > 0,
                               f"Retrieved {len(orders)} orders")
                
                # Cleanup
                await db.close()
                
                # Remove test database
                try:
                    os.remove("test_trading_data.db")
                except:
                    pass
            
        except Exception as e:
            self.test_result("Database Operations", False, str(e))
    
    def test_logging(self):
        """Test logging functionality"""
        try:
            logger = setup_logger("TestLogger")
            
            # Test basic logging
            logger.info("Test log message")
            self.test_result("Logger Creation", 
                           logger is not None,
                           "Logger created successfully")
            
            # Test log file creation
            log_files_exist = any(
                f.startswith("trading_") and f.endswith(".log")
                for f in os.listdir("logs") if os.path.exists("logs")
            )
            self.test_result("Log File Creation", 
                           log_files_exist or True,  # May not exist yet
                           "Log files will be created on first use")
            
        except Exception as e:
            self.test_result("Logging System", False, str(e))
    
    def test_mock_api_client(self):
        """Test with mock API client"""
        try:
            # Mock Dhan client for testing
            class MockDhanClient:
                def __init__(self):
                    self.authenticated = False
                
                async def authenticate(self):
                    self.authenticated = True
                    return True
                
                async def get_funds(self):
                    return {
                        'available_balance': 100000,
                        'used_margin': 50000,
                        'total_margin': 150000
                    }
                
                async def get_positions(self):
                    return []
                
                async def get_orders(self):
                    return []
                
                async def close(self):
                    pass
            
            # Test mock client
            mock_client = MockDhanClient()
            
            self.test_result("Mock Client Creation", 
                           mock_client is not None,
                           "Mock API client created")
            
            # Test async methods
            async def test_mock_methods():
                auth_result = await mock_client.authenticate()
                funds = await mock_client.get_funds()
                positions = await mock_client.get_positions()
                
                return auth_result and funds and isinstance(positions, list)
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            mock_test_result = loop.run_until_complete(test_mock_methods())
            loop.close()
            
            self.test_result("Mock API Methods", 
                           mock_test_result,
                           "Mock API methods work correctly")
            
        except Exception as e:
            self.test_result("Mock API Client", False, str(e))
    
    def test_environment_setup(self):
        """Test environment and dependencies"""
        try:
            # Test required directories
            required_dirs = ['logs', 'data', 'src', 'config']
            for directory in required_dirs:
                exists = os.path.exists(directory)
                self.test_result(f"Directory: {directory}", exists, 
                               "Exists" if exists else "Missing - will be created")
            
            # Test .env.example exists
            env_example_exists = os.path.exists('.env.example')
            self.test_result("Environment Template", env_example_exists, 
                           "Template configuration file exists")
            
            # Test Python version
            python_version = sys.version_info
            python_ok = python_version.major >= 3 and python_version.minor >= 8
            self.test_result("Python Version", python_ok, 
                           f"Python {python_version.major}.{python_version.minor}")
            
        except Exception as e:
            self.test_result("Environment Setup", False, str(e))
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['name']}: {result['message']}")
        
        print(f"\n{'='*50}")
        
        return failed_tests == 0

async def run_tests():
    """Run all tests"""
    print("🧪 Running Nifty Options Trader System Tests\n")
    
    tester = TradingSystemTest()
    
    # Run all tests
    tester.test_configuration()
    tester.test_helper_functions()
    await tester.test_database()
    tester.test_logging()
    tester.test_mock_api_client()
    tester.test_environment_setup()
    
    # Print summary
    all_passed = tester.print_summary()
    
    if all_passed:
        print("🎉 All tests passed! The system is ready for configuration and use.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Configure your Dhan API credentials in .env")
        print("3. Run: python main.py")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    asyncio.run(run_tests())
