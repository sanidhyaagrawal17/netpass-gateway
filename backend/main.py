import os
import uuid
import secrets
import sqlite3
import requests
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

# CONFIG
MERAKI_API_KEY = os.getenv("MERAKI_API_KEY", "").strip()
MERAKI_BASE_URL = os.getenv("MERAKI_BASE_URL", "https://api.meraki.com/api/v1").rstrip("/")
MERAKI_NETWORK_ID = os.getenv("MERAKI_NETWORK_ID", "").strip()
DB_FILE = "netpass.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS guests
                     (id TEXT PRIMARY KEY, name TEXT, email TEXT, duration_hours INTEGER,
                      password TEXT, expires_at TEXT, status TEXT, meraki_id TEXT)''')
        conn.commit()

init_db()

app = FastAPI(title="NetPass API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {"X-Cisco-Meraki-API-Key": MERAKI_API_KEY, "Content-Type": "application/json", "Accept": "application/json"}

class GuestProvisionRequest(BaseModel):
    name: str
    email: EmailStr
    duration_hours: int

@app.get("/guests")
def get_guests():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM guests ORDER BY rowid DESC")
        return [dict(r) for r in c.fetchall()]

@app.post("/request-access")
def request_access(request: GuestProvisionRequest):
    local_id = str(uuid.uuid4())
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO guests (id, name, email, duration_hours, status) VALUES (?, ?, ?, ?, ?)",
                  (local_id, request.name, request.email, request.duration_hours, "Pending"))
        conn.commit()
    return {"status": "success", "id": local_id}

@app.get("/request-status/{local_id}")
def check_request_status(local_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # FIX: Added 'email' to the SELECT statement so React can fetch it
        c.execute("SELECT status, password, expires_at, email FROM guests WHERE id = ?", (local_id,))
        guest = c.fetchone()
    if not guest: raise HTTPException(status_code=404, detail="Request not found.")
    return dict(guest)

@app.post("/approve-request/{local_id}")
def approve_request(local_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM guests WHERE id = ?", (local_id,))
        guest = c.fetchone()
        
    if not guest or guest["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Invalid request.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=guest["duration_hours"])
    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    generated_password = secrets.token_urlsafe(10)
    
    # Track the actual email we end up using
    actual_email = guest["email"]

    url = f"{MERAKI_BASE_URL}/networks/{MERAKI_NETWORK_ID}/merakiAuthUsers"
    payload = {
        "email": actual_email, "login": actual_email, "name": guest["name"],
        "password": generated_password, "accountType": "Guest",
        "emailPasswordToUser": False, "isAdmin": False,
        "authorizations": [{"ssidNumber": 0, "authorizedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "expiresAt": expires_at_str}],
    }

    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        if r.status_code == 400 and "taken" in r.text.lower():
            # If Meraki blocks it, generate the alias
            actual_email = f"{guest['email'].split('@')[0]}+{secrets.token_hex(2)}@{guest['email'].split('@')[1]}"
            payload["email"] = actual_email
            payload["login"] = actual_email
            r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
            r.raise_for_status()
        meraki_id = r.json().get("id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        # FIX: We now UPDATE the 'email' column with the actual_email used
        c.execute("UPDATE guests SET email = ?, password = ?, expires_at = ?, status = 'Active', meraki_id = ? WHERE id = ?", 
                  (actual_email, generated_password, expires_at_str, meraki_id, local_id))
        conn.commit()
    return {"status": "success"}
@app.delete("/revoke-guest/{local_id}")
def revoke_guest(local_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT meraki_id FROM guests WHERE id = ?", (local_id,))
        row = c.fetchone()
        meraki_id = row["meraki_id"] if row else None
    
    if not meraki_id: raise HTTPException(status_code=404, detail="Guest not found.")
    url = f"{MERAKI_BASE_URL}/networks/{MERAKI_NETWORK_ID}/merakiAuthUsers/{meraki_id}"
    try:
        requests.delete(url, headers=HEADERS, timeout=15).raise_for_status()
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("UPDATE guests SET status = 'Revoked' WHERE id = ?", (local_id,))
            conn.commit()
        return {"status": "success"}
    except: raise HTTPException(status_code=500, detail="Failed.")