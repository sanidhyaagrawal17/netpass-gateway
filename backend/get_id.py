# diagnose_meraki.py
import os, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("MERAKI_API_KEY", "").strip()
BASE_URL = os.getenv("MERAKI_BASE_URL", "https://api.meraki.in/api/v1").rstrip("/")
NET_ID   = os.getenv("MERAKI_NETWORK_ID", "").strip()

HEADERS = {
    "X-Cisco-Meraki-API-Key": API_KEY,
    "Content-Type": "application/json",
}

print(f"Key   : {'*' * (len(API_KEY)-4)}{API_KEY[-4:] if API_KEY else 'MISSING'}")
print(f"URL   : {BASE_URL}")
print(f"NetID : {NET_ID or 'MISSING'}\n")

r = requests.get(f"{BASE_URL}/organizations", headers=HEADERS, timeout=10)
print(f"[GET /organizations] {r.status_code}")

if r.status_code == 401:
    print("  → Still 401. Check API & Webhooks page — ensure checkbox is enabled and key is freshly generated.")
    exit(1)

orgs = r.json()
print(f"  → {len(orgs)} org(s) found:")
for o in orgs:
    print(f"     {o['id']}  {o['name']}")

# Verify network ID
for o in orgs:
    rn = requests.get(f"{BASE_URL}/organizations/{o['id']}/networks", headers=HEADERS, timeout=10)
    if rn.status_code == 200:
        for n in rn.json():
            marker = " ← MATCH" if n["id"] == NET_ID else ""
            print(f"     Network: {n['id']}  {n['name']}{marker}")