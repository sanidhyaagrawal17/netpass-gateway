import os
import requests
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

API_KEY = os.getenv("MERAKI_API_KEY")
BASE_URL = os.getenv("MERAKI_BASE_URL")

print("\n--- SHARD VERIFICATION TEST ---")
print(f"[*] Target URL: {BASE_URL}")

if not API_KEY or not BASE_URL:
    print("[-] CRITICAL ERROR: Missing API_KEY or BASE_URL in .env file.")
    exit()

# We test the simplest endpoint to check network routing speed
url = f"{BASE_URL}/organizations"
headers = {
    "X-Cisco-Meraki-API-Key": API_KEY,
    "Accept": "application/json"
}

try:
    # We keep the 10-second timeout. If the shard works, it should respond in < 1 second.
    print("[*] Pinging Cisco Meraki India Shard...")
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"[*] HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        print("[+] SUCCESS! Connection established perfectly.")
        print(f"[+] Response Time: {response.elapsed.total_seconds()} seconds")
    else:
        print(f"[-] FAILED: {response.status_code}")
        print(f"[-] Details: {response.text}")

except requests.exceptions.ReadTimeout:
    print("[-] FAILED: ReadTimeout. The connection is still hanging.")
except Exception as e:
    print(f"[-] SYSTEM ERROR: {e}")
print("-------------------------------\n")