import os
import time
import requests
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()
API_KEY = os.getenv("MERAKI_API_KEY")

if not API_KEY:
    print("[-] CRITICAL ERROR: API Key is blank. Check your .env file.")
    exit()

print("\n--- MERAKI API POLLING SCRIPT ---")
print(f"[*] Testing Key: {API_KEY[:4]}...{API_KEY[-4:]}")
print("[*] Waiting for Cisco Cloud firewall propagation...")

url = "https://api.meraki.com/api/v1/organizations"
headers = {
    "X-Cisco-Meraki-API-Key": API_KEY,
    "Accept": "application/json"
}

attempt = 1

while True:
    try:
        print(f"\n[*] Attempt {attempt} - Pinging Meraki Cloud...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print(f"[+] HTTP Status: {response.status_code}")
            print("[+] SUCCESS! The firewall has synced. Your key is fully authorized.")
            print("\n[+] You can now return to your React app and hit 'Authorize'!")
            break
            
        elif response.status_code == 401:
            print("[-] HTTP Status: 401 Unauthorized.")
            print("[-] Firewall is still blocking the request. Waiting 10 seconds before retrying...")
            time.sleep(10)
            attempt += 1
            
        else:
            print(f"[-] UNEXPECTED ERROR: {response.status_code}")
            print(f"[-] Details: {response.text}")
            print("[-] Exiting script. Check dashboard settings.")
            break

    except requests.exceptions.RequestException as e:
        print(f"[-] NETWORK ERROR: {e}")
        print("[-] Retrying in 10 seconds...")
        time.sleep(10)
        attempt += 1