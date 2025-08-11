#!/usr/bin/env python3
"""
Telegram Bot Test Script
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

def test_telegram_bot():
    """Test Telegram bot configuration and connectivity"""
    print("🤖 TESTING TELEGRAM BOT INTEGRATION")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    print(f"📱 Bot Token: {'✅ Set' if bot_token else '❌ Missing'}")
    print(f"💬 Chat ID: {'✅ Set' if chat_id else '❌ Missing'}")
    
    if not bot_token or not chat_id:
        print("\n❌ Missing Telegram credentials!")
        print("Please check your .env file for:")
        print("- TELEGRAM_BOT_TOKEN")
        print("- TELEGRAM_CHAT_ID")
        return False
    
    print(f"🔑 Token length: {len(bot_token)} characters")
    print(f"👤 Chat ID: {chat_id}")
    print()
    
    # Test 1: Get bot info
    print("🔍 Test 1: Getting bot information...")
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data['result']
                print(f"✅ Bot connected successfully!")
                print(f"   Bot Name: {bot_info.get('first_name', 'N/A')}")
                print(f"   Username: @{bot_info.get('username', 'N/A')}")
                print(f"   Bot ID: {bot_info.get('id', 'N/A')}")
                print(f"   Can Join Groups: {bot_info.get('can_join_groups', False)}")
            else:
                print(f"❌ Bot API error: {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test 2: Send test message
    print(f"\n📤 Test 2: Sending test message to chat {chat_id}...")
    try:
        test_message = f"""🚀 *Nifty Options Trading Bot - Test Message*

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ Telegram integration is working!
🤖 Bot is ready to send trading notifications

This is a test message to verify the Telegram bot setup."""

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': test_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                message_id = data['result']['message_id']
                print(f"✅ Test message sent successfully!")
                print(f"   Message ID: {message_id}")
                print(f"   Chat ID confirmed: {data['result']['chat']['id']}")
                
                # Try to get chat info
                chat_info = data['result']['chat']
                chat_type = chat_info.get('type', 'unknown')
                chat_name = chat_info.get('first_name') or chat_info.get('title', 'Unknown')
                print(f"   Chat Type: {chat_type}")
                print(f"   Chat Name: {chat_name}")
                
            else:
                print(f"❌ Failed to send message: {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False
    
    # Test 3: Check chat accessibility
    print(f"\n🔍 Test 3: Verifying chat accessibility...")
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        payload = {'chat_id': chat_id}
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                chat_data = data['result']
                print(f"✅ Chat accessible!")
                print(f"   Chat Type: {chat_data.get('type', 'N/A')}")
                print(f"   Chat Title: {chat_data.get('title') or chat_data.get('first_name', 'N/A')}")
            else:
                print(f"⚠️ Chat info warning: {data.get('description', 'Unknown')}")
        else:
            print(f"⚠️ Chat check failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Chat check error: {e}")
    
    print(f"\n🎉 TELEGRAM BOT TESTS COMPLETED!")
    print("✅ Your Telegram bot is working correctly!")
    print("✅ Ready to send trading notifications!")
    return True

def send_sample_trading_notification():
    """Send a sample trading notification"""
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if not bot_token or not chat_id:
        return
    
    sample_message = f"""📈 *TRADE ALERT - Sample Notification*

🎯 **Strategy**: Scalping Strategy
📊 **Symbol**: NIFTY 25500 CE
🔥 **Action**: BUY
📦 **Quantity**: 25 lots
💰 **Price**: ₹125.50
⏰ **Time**: {datetime.now().strftime('%H:%M:%S')}

📊 **Analysis**:
• Strong momentum detected
• Volume spike confirmed
• Risk-reward ratio: 1:2

🛡️ **Risk Management**:
• Stop Loss: ₹115.00
• Target: ₹145.00
• Position Size: 2% of portfolio

⚡ This is a sample trading notification to demonstrate the system!"""

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': sample_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"\n📱 Sample trading notification sent successfully!")
            else:
                print(f"\n❌ Failed to send sample notification: {data.get('description')}")
        else:
            print(f"\n❌ HTTP Error sending sample: {response.status_code}")
    except Exception as e:
        print(f"\n❌ Error sending sample notification: {e}")

if __name__ == "__main__":
    success = test_telegram_bot()
    
    if success:
        print(f"\n🎯 Would you like to see a sample trading notification?")
        send_sample_trading_notification()
        
        print(f"\n📋 SETUP SUMMARY:")
        print("✅ Bot Token: Valid and working")
        print("✅ Chat ID: Accessible")  
        print("✅ Message Delivery: Successful")
        print("✅ Ready for live trading notifications!")
        
        print(f"\n🔧 INTEGRATION STATUS:")
        print("Your trading bot will automatically send notifications for:")
        print("• 📈 Trade entries and exits")
        print("• 🛡️ Stop loss and take profit triggers")  
        print("• ⚠️ Risk management alerts")
        print("• 📊 Daily performance summaries")
        print("• 🚨 System errors and warnings")
    else:
        print(f"\n❌ TELEGRAM BOT SETUP INCOMPLETE")
        print("Please fix the issues above before using notifications.")
