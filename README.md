# NetPass Gateway

A full-stack Network Access Control (NAC) application built to interface with Cisco Meraki infrastructure. NetPass replaces static password sharing with a dynamic, approval-based External Captive Portal (EXCAP) to enforce strict, device-level session management.

This project was developed as an exploration into the intersection of software development and core network engineering, focusing on secure session management, API state synchronization, and identity lifecycle automation.

## 🏗 System Architecture

NetPass utilizes a decoupled architecture to manage the AAA (Authentication, Authorization, and Accounting) lifecycle:
* **Frontend (React + Vite):** An asynchronous guest portal with automated polling and QR-code generation, alongside a secure administrative dashboard for queue management.
* **Backend (Python + FastAPI):** An API gateway that intercepts client requests, manages a local ledger, and communicates securely with the Cisco Meraki Cloud.
* **Local Ledger (SQLite):** Acts as a local RADIUS-like controller to enforce tracking and prevent unauthorized credential sharing.
* **Infrastructure (Cisco Meraki API):** The hardware layer executing the authentication and routing.

## ✨ Key Technical Features

* **EXCAP Integration:** Leverages the Meraki `splashAuthorizationStatus` API to build a custom External Captive Portal, allowing granular control over individual MAC addresses rather than just global identities.
* **Identity Collision Handling (Upsert Pattern):** Implements robust state-reconciliation logic to bypass Cisco Meraki's global email uniqueness constraints ("Ghost Identities"). It utilizes automated email aliasing and cascading API requests to guarantee seamless credential generation.
* **Asynchronous Polling:** The React frontend uses an intelligent polling loop to query the backend ledger, instantly displaying access credentials and connection QR codes the moment a network administrator approves a request.
* **Manual Kill Switch:** A secure administrative ledger allows network operators to instantly revoke Wi-Fi access and purge identities from the Cisco Cloud with a single click.

## 🛠 Tech Stack
* **Frontend:** React.js, React Router, Axios, QRCode.react, CSS Variables (Dark/Light mode native)
* **Backend:** Python 3, FastAPI, Uvicorn, Requests, SQLite3
* **Networking/Security:** Cisco Meraki API, IEEE 802.1X concepts, WPA/WPA2

## 🚀 Local Development Setup

To run this project locally, you will need a Cisco Meraki dashboard account with API access enabled.

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/netpass-gateway.git](https://github.com/YOUR_USERNAME/netpass-gateway.git)
cd netpass-gateway