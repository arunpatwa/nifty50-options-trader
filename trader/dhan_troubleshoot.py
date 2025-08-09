#!/usr/bin/env python3
"""
Dhan API credential troubleshooting and validation script
"""

import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

def check_environment():
    """Check environment variables"""
    print("🔍 CHECKING DHAN API CREDENTIALS")
    print("=" * 50)
    
    # Load .env file
    load_dotenv()
    
    client_id = os.getenv('DHAN_CLIENT_ID', '')
    access_token = os.getenv('DHAN_ACCESS_TOKEN', '')
    
    print(f"📁 Environment file: {'.env' if os.path.exists('.env') else '.env.example'}")
    print(f"🔑 DHAN_CLIENT_ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"🎫 DHAN_ACCESS_TOKEN: {'✅ Set' if access_token else '❌ Missing'}")
    
    if client_id:
        print(f"   Client ID length: {len(client_id)} characters")
        print(f"   Client ID format: {'Numeric' if client_id.isdigit() else 'Alphanumeric'}")
    
    if access_token:
        print(f"   Access token length: {len(access_token)} characters")
        print(f"   Token starts with: {access_token[:10]}...")
    
    return client_id, access_token

def test_dhan_api_endpoints(client_id, access_token):
    """Test different Dhan API endpoints"""
    print(f"\n🌐 TESTING DHAN API ENDPOINTS")
    print("=" * 50)
    
    base_urls = [
        "https://api.dhan.co",
        "https://api.dhan.co/v2", 
        "https://dhanhq.co/api",
        "https://api.dhanhq.co"
    ]
    
    endpoints = [
        "/v2/funds",
        "/funds", 
        "/v1/funds",
        "/api/v2/funds"
    ]
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'clientid': client_id,
        'accesstoken': access_token
    }
    
    alternate_headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'client_id': client_id,
        'access_token': access_token,
        'Authorization': f'Bearer {access_token}'
    }
    
    for base_url in base_urls:
        print(f"\n🔗 Testing base URL: {base_url}")
        for endpoint in endpoints:
            full_url = base_url + endpoint
            
            # Test with original headers
            try:
                response = requests.get(full_url, headers=headers, timeout=10)
                status = response.status_code
                
                if status == 200:
                    print(f"  ✅ {endpoint}: SUCCESS (200)")
                    return True, base_url, endpoint
                elif status == 401:
                    print(f"  🔐 {endpoint}: Unauthorized (401) - Check credentials")
                elif status == 404:
                    print(f"  ❌ {endpoint}: Not Found (404)")
                elif status == 403:
                    print(f"  🚫 {endpoint}: Forbidden (403)")
                else:
                    print(f"  ⚠️  {endpoint}: {status} - {response.text[:100]}")
                    
            except requests.exceptions.RequestException as e:
                print(f"  ⚡ {endpoint}: Connection Error - {str(e)[:50]}")
                
            # Test with alternate headers
            try:
                response = requests.get(full_url, headers=alternate_headers, timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ {endpoint} (alt headers): SUCCESS")
                    return True, base_url, endpoint
            except:
                pass
    
    return False, None, None

def show_dhan_setup_guide():
    """Show guide for getting Dhan API credentials"""
    print(f"\n📚 HOW TO GET DHAN API CREDENTIALS")
    print("=" * 50)
    print("🔗 Step 1: Login to Dhan")
    print("   • Go to https://web.dhan.co")
    print("   • Login with your trading account")
    print()
    print("⚙️  Step 2: Find API Section")
    print("   • Look for 'API' or 'Developer' section")
    print("   • Usually under: Profile → Settings → API")
    print("   • Or: Account → API Management")
    print()
    print("🎫 Step 3: Generate API Credentials")
    print("   • DHAN_CLIENT_ID: Usually your 8-digit account number")
    print("   • DHAN_ACCESS_TOKEN: Long alphanumeric string")
    print("   • Some platforms call it 'API Key' or 'Secret'")
    print()
    print("🔒 Step 4: API Permissions")
    print("   • Enable 'Trading' permissions")
    print("   • Enable 'Market Data' permissions")
    print("   • Some APIs require approval (may take 1-2 days)")
    print()
    print("📱 Alternative: Check Dhan Mobile App")
    print("   • API section may be in mobile app")
    print("   • Settings → API Access")
    print()
    print("📞 If Still Having Issues:")
    print("   • Contact Dhan customer support")
    print("   • Ask specifically for 'API trading access'")
    print("   • Mention you need REST API credentials")

def main():
    print("🚀 DHAN API CREDENTIAL VALIDATOR")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check credentials
    client_id, access_token = check_environment()
    
    if not client_id or not access_token:
        print(f"\n❌ CREDENTIALS MISSING")
        print("Please add your Dhan API credentials to the .env file:")
        print("DHAN_CLIENT_ID=your_client_id_here")
        print("DHAN_ACCESS_TOKEN=your_access_token_here")
        show_dhan_setup_guide()
        return
    
    # Test API endpoints
    success, working_base_url, working_endpoint = test_dhan_api_endpoints(client_id, access_token)
    
    if success:
        print(f"\n✅ SUCCESS! Found working endpoint:")
        print(f"   Base URL: {working_base_url}")
        print(f"   Endpoint: {working_endpoint}")
        print(f"\n🔧 Update your code to use: {working_base_url}")
    else:
        print(f"\n❌ NO WORKING ENDPOINTS FOUND")
        print("This suggests either:")
        print("1. 🔑 Incorrect API credentials")
        print("2. 🚫 API access not enabled in your Dhan account") 
        print("3. 🔗 Wrong API endpoints (Dhan may have changed them)")
        print("4. 🌐 Network/connectivity issues")
        
        show_dhan_setup_guide()

if __name__ == "__main__":
    main()
