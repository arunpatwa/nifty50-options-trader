#!/usr/bin/env python3
"""
Quick setup verification and configuration helper
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if environment is properly set up"""
    print("🔍 Checking Nifty Options Trader Setup...\n")
    
    checks = []
    
    # Check Python version
    python_version = sys.version_info
    python_ok = python_version.major >= 3 and python_version.minor >= 8
    checks.append(("Python Version", python_ok, f"Python {python_version.major}.{python_version.minor}"))
    
    # Check virtual environment
    venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_exists = Path('.venv').exists()
    checks.append(("Virtual Environment", venv_active or venv_exists, "Active" if venv_active else "Available" if venv_exists else "Missing"))
    
    # Check directories
    required_dirs = ['src', 'config', 'logs', 'data']
    for directory in required_dirs:
        exists = Path(directory).exists()
        checks.append((f"Directory {directory}", exists, "✓" if exists else "Missing"))
    
    # Check .env file
    env_exists = Path('.env').exists()
    env_example_exists = Path('.env.example').exists()
    checks.append(("Environment Config", env_exists, "Configured" if env_exists else "Needs setup"))
    
    # Print results
    all_good = True
    for name, status, details in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}: {details}")
        if not status:
            all_good = False
    
    print("\n" + "="*50)
    
    if all_good:
        print("🎉 Environment check passed!")
        return True
    else:
        print("⚠️  Environment needs setup. Please follow the instructions below.")
        return False

def setup_environment():
    """Help set up the environment"""
    print("\n📋 Setup Instructions:")
    print("="*50)
    
    if not Path('.env').exists():
        if Path('.env.example').exists():
            print("1. Copy environment template:")
            print("   cp .env.example .env")
            print()
        
        print("2. Edit .env file and add your Dhan API credentials:")
        print("   - DHAN_CLIENT_ID=your_client_id")
        print("   - DHAN_ACCESS_TOKEN=your_access_token")
        print()
    
    if not Path('.venv').exists():
        print("3. Create virtual environment:")
        print("   python -m venv .venv")
        print("   source .venv/bin/activate  # Linux/Mac")
        print("   # or")
        print("   .venv\\Scripts\\activate  # Windows")
        print()
    
    print("4. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    
    print("5. Test the system:")
    print("   python tests/test_system.py")
    print()
    
    print("6. Run the trader:")
    print("   python main.py")
    print()

def show_safety_warnings():
    """Show important safety warnings"""
    print("⚠️  IMPORTANT SAFETY WARNINGS:")
    print("="*50)
    print("🚨 This is automated trading software that can place real trades")
    print("🚨 with real money. Please understand the risks:")
    print()
    print("   • Start with PAPER TRADING or small amounts only")
    print("   • Options trading involves substantial risk of loss")
    print("   • Market conditions can change rapidly")
    print("   • Software may have bugs - monitor carefully")
    print("   • Set appropriate position sizes and risk limits")
    print("   • Never risk more than you can afford to lose")
    print()
    print("📚 Recommended before using:")
    print("   • Test thoroughly in paper trading mode")
    print("   • Understand each strategy's logic")
    print("   • Set conservative risk parameters")
    print("   • Monitor the system closely during initial runs")
    print("   • Have a plan for emergency situations")
    print()
    print("✅ By using this software, you acknowledge these risks")
    print("   and take full responsibility for your trading decisions.")
    print("="*50)

def main():
    """Main function"""
    print("🚀 Nifty 50 Options Automated Trader")
    print("   Setup Verification & Configuration Helper")
    print()
    
    # Show safety warnings first
    show_safety_warnings()
    print()
    
    # Check environment
    env_ok = check_environment()
    
    if not env_ok:
        setup_environment()
        
        print("\n📞 Need help?")
        print("   • Check the README.md file for detailed instructions")
        print("   • Ensure you have Dhan API access enabled")
        print("   • Test with the test_system.py script first")
        print()
        print("🔄 Run this script again after setup to verify")
    else:
        print("\n🎯 Next Steps:")
        print("   • Configure your .env file with real API credentials")
        print("   • Start with paper trading or small amounts")
        print("   • Run: python tests/test_system.py")
        print("   • Then: python example.py  # for demo mode")
        print("   • Or: python main.py      # for live trading")
        print()
        print("📊 Dashboard: http://localhost:8050")
        print("   Run 'python example.py dashboard' to start monitoring")

if __name__ == "__main__":
    main()
