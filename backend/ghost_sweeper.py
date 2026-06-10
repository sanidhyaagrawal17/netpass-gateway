import os
import requests
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

MERAKI_API_KEY = os.getenv("MERAKI_API_KEY")
MERAKI_BASE_URL = os.getenv("MERAKI_BASE_URL")
MERAKI_NETWORK_ID = os.getenv("MERAKI_NETWORK_ID")

if not all([MERAKI_API_KEY, MERAKI_BASE_URL, MERAKI_NETWORK_ID]):
    print("[-] CRITICAL ERROR: Missing environment variables in .env file.")
    exit()

HEADERS = {
    "X-Cisco-Meraki-API-Key": MERAKI_API_KEY,
    "Accept": "application/json"
}

print("\n================ GHOST SWEEPER ================")
print("[*] Connecting to Meraki Cloud...")

# 1. Fetch all users directly from the Meraki database
url = f"{MERAKI_BASE_URL}/networks/{MERAKI_NETWORK_ID}/merakiAuthUsers"

try:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    cloud_users = response.json()
except Exception as e:
    print(f"[-] Failed to fetch users: {e}")
    exit()

if not cloud_users:
    print("[+] The Meraki Cloud database is completely empty. No ghosts found!")
    print("===============================================\n")
    exit()

print(f"[!] Found {len(cloud_users)} user(s) hardcoded in the Cloud Database:\n")

# 2. Display the ghosts
for i, user in enumerate(cloud_users, 1):
    name = user.get("name", "UNKNOWN (Orphaned)")
    email = user.get("email", "UNKNOWN")
    user_id = user.get("id")
    print(f"  {i}. {name} | {email} | ID: {user_id}")

print("\n===============================================")

# 3. The Purge Prompt
confirm = input("\n[?] Do you want to NUKE ALL of these users from the cloud? (y/N): ")

if confirm.lower() in ['y', 'yes']:
    print("\n[*] Initiating mass purge...")
    
    success_count = 0
    for user in cloud_users:
        user_id = user.get("id")
        email = user.get("email")
        
        delete_url = f"{MERAKI_BASE_URL}/networks/{MERAKI_NETWORK_ID}/merakiAuthUsers/{user_id}"
        
        try:
            del_resp = requests.delete(delete_url, headers=HEADERS, timeout=10)
            if del_resp.status_code == 204:
                print(f"[+] DELETED: {email}")
                success_count += 1
            else:
                print(f"[-] FAILED to delete {email}: Status {del_resp.status_code}")
        except Exception as e:
            print(f"[-] ERROR deleting {email}: {e}")
            
    print(f"\n[+] Purge Complete. {success_count}/{len(cloud_users)} ghosts eradicated.")
else:
    print("\n[*] Purge canceled. No users were deleted.")

print("===============================================\n")