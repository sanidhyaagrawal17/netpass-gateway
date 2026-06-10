import os
import requests
from dotenv import load_dotenv

# 1. Load the environment variables
load_dotenv()
API_KEY = os.getenv("MERAKI_API_KEY")

print("\n--- MERAKI API DIAGNOSTIC ---")
if not API_KEY:
    print("[-] ERROR: API Key is blank. Check your .env file.")
    exit()

print(f"[+] Testing Key: {API_KEY[:4]}...{API_KEY[-4:]}")

# 2. Hit the simplest, most fundamental Meraki endpoint
url = "https://api.meraki.com/api/v1/organizations"
headers = {
    "X-Cisco-Meraki-API-Key": API_KEY,
    "Accept": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    
    print(f"[+] HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        print("[+] SUCCESS! Your key is perfectly valid.")
        print(f"[+] Data Returned: {response.json()}")
    elif response.status_code == 401:
        print("[-] FAILED: 401 Unauthorized.")
        print("[-] The Cisco Cloud is actively rejecting this specific string.")
    else:
        print(f"[-] FAILED: {response.status_code}")
        print(f"[-] Details: {response.text}")

except Exception as e:
    print(f"[-] SYSTEM ERROR: {e}")
print("-----------------------------\n")