#!/usr/bin/env python3
"""
Fixed URL construction script for dhan_client.py
"""

import re

def fix_dhan_client():
    """Fix the URL construction in dhan_client.py"""
    
    with open('src/api/dhan_client.py', 'r') as f:
        content = f.read()
    
    # Backup the original
    with open('src/api/dhan_client.py.backup', 'w') as f:
        f.write(content)
    
    # Fix all the URL constructions
    # Pattern 1: urljoin(self.base_url, self.endpoints['key'])
    content = re.sub(r'urljoin\(self\.base_url,\s*self\.endpoints\[([^]]+)\]\)', 
                     r'f"{self.base_url}{self.endpoints[\1]}"', content)
    
    # Pattern 2: urljoin(self.base_url, f"{self.endpoints['key']}/something")  
    content = re.sub(r'urljoin\(self\.base_url,\s*f"{self\.endpoints\[([^]]+)\]}/([^"]+)"\)', 
                     r'f"{self.base_url}{self.endpoints[\1]}/\2"', content)
    
    # Remove urljoin import since we don't need it anymore
    content = re.sub(r'from urllib\.parse import urljoin\n', '', content)
    
    # Write the fixed version
    with open('src/api/dhan_client.py.fixed', 'w') as f:
        f.write(content)
    
    print("✅ Created fixed version: src/api/dhan_client.py.fixed")
    print("🔄 Review the file and then rename it to replace the original")

if __name__ == "__main__":
    fix_dhan_client()
