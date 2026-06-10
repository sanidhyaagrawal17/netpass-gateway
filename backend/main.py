import os
import uuid
import secrets
import sqlite3
import requests
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIG & SECURITY SETUP
# =============================================================================
MERAKI_API_KEY = os.getenv("MERAKI_API_KEY", "").strip()
MERAKI_BASE_URL = os.getenv("MERAKI_BASE_URL", "https://api.meraki.com/api/v1").rstrip("/")
MERAKI_NETWORK_ID = os.getenv("MERAKI_NETWORK_ID", "").strip()
DB_FILE = "netpass.db"

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be set in .env — run: python -c \"import secrets; print(secrets.token_hex(32))\"")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

def verify_password(plain_password, hashed_password):
    # bcrypt requires bytes, so we encode the strings to utf-8 first
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    # generate a salt and hash the password natively
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8') # convert back to string for SQLite
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS guests
                     (id TEXT PRIMARY KEY, name TEXT, email TEXT, duration_hours INTEGER,
                      password TEXT, expires_at TEXT, status TEXT, meraki_id TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (username TEXT PRIMARY KEY, hashed_password TEXT)''')
        
        c.execute("SELECT * FROM admins")
        if not c.fetchone():
            default_user = "admin"
            default_pass = os.getenv("ADMIN_DEFAULT_PASSWORD", "change_this_on_first_login")
            c.execute("INSERT INTO admins (username, hashed_password) VALUES (?, ?)", 
                      (default_user, get_password_hash(default_pass)))
            print("\n" + "="*50)
            print("[!] DEFAULT ADMIN CREATED")
            print(f"    Username: {default_user}")
            print(f"    Password: {default_pass}")
            print("="*50 + "\n")
            
        conn.commit()

init_db()

# =============================================================================
# AUTHENTICATION DEPENDENCY
# =============================================================================
def verify_admin(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
        
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM admins WHERE username = ?", (username,))
        if not c.fetchone():
            raise credentials_exception
    return username

app = FastAPI(title="NetPass API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {"X-Cisco-Meraki-API-Key": MERAKI_API_KEY, "Content-Type": "application/json", "Accept": "application/json"}

class GuestProvisionRequest(BaseModel):
    name: str
    email: EmailStr
    duration_hours: int

# =============================================================================
# ADMIN LOGIN ENDPOINTS
# =============================================================================
@app.post("/admin/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT username, hashed_password FROM admins WHERE username = ?", (form_data.username,))
        user = c.fetchone()
        
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user[0]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/me")
def get_current_admin(username: str = Depends(verify_admin)):
    return {"username": username}

# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================
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
        c.execute("SELECT status, password, expires_at, email FROM guests WHERE id = ?", (local_id,))
        guest = c.fetchone()
    if not guest: raise HTTPException(status_code=404, detail="Request not found.")
    return dict(guest)

# =============================================================================
# PROTECTED ADMIN ENDPOINTS
# =============================================================================
@app.get("/guests", dependencies=[Depends(verify_admin)])
def get_guests():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, name, email, duration_hours, expires_at, status, meraki_id FROM guests ORDER BY rowid DESC")
        return [dict(r) for r in c.fetchall()]

@app.post("/approve-request/{local_id}", dependencies=[Depends(verify_admin)])
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
            actual_email = f"{guest['email'].split('@')[0]}+{secrets.token_hex(2)}@{guest['email'].split('@')[1]}"
            payload["email"] = actual_email
            payload["login"] = actual_email
            r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
            r.raise_for_status()
        elif not r.ok:
            raise requests.exceptions.HTTPError(response=r)
            
        meraki_id = r.json().get("id")
        
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        raise HTTPException(status_code=502, detail=f"Meraki API Error: {e.response.status_code} - {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE guests SET email = ?, password = ?, expires_at = ?, status = 'Active', meraki_id = ? WHERE id = ?", 
                  (actual_email, generated_password, expires_at_str, meraki_id, local_id))
        conn.commit()
    return {"status": "success"}

@app.delete("/reject-request/{local_id}", dependencies=[Depends(verify_admin)])
def reject_request(local_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM guests WHERE id = ? AND status = 'Pending'", (local_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Pending request not found.")
        c.execute("UPDATE guests SET status = 'Rejected' WHERE id = ?", (local_id,))
        conn.commit()
    return {"status": "success"}

@app.delete("/revoke-guest/{local_id}", dependencies=[Depends(verify_admin)])
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
        r = requests.delete(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Meraki revocation failed: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE guests SET status = 'Revoked' WHERE id = ?", (local_id,))
        conn.commit()
        
    return {"status": "success"}