# NetPass: Enterprise Guest Provisioning Engine

NetPass is a full-stack application designed to automate the secure provisioning of temporary wireless access via the Cisco Meraki Cloud API. It provides a React-based interface for network administrators to generate timed credentials, display Wi-Fi QR codes, and execute instant security revocations.

## System Architecture

```mermaid
graph TD
    %% Define Styles
    classDef frontend fill:#61DAFB,stroke:#333,stroke-width:2px,color:#000;
    classDef backend fill:#3776AB,stroke:#333,stroke-width:2px,color:#fff;
    classDef cloud fill:#78B72A,stroke:#333,stroke-width:2px,color:#fff;
    classDef physical fill:#f9f9f9,stroke:#333,stroke-width:2px,color:#000;

    %% Nodes
    Admin["👨‍💻 Admin / NetPass UI (React)"]:::frontend
    Gateway["⚙️ FastAPI Gateway (Python)"]:::backend
    CiscoCloud["☁️ Cisco Meraki Cloud (API Shard)"]:::cloud
    DB[("Meraki Auth Database")]:::cloud
    AP["📡 Meraki Access Point (MX/MR)"]:::physical
    Guest["📱 Guest Device"]:::physical

    %% Data Flow
    Admin -- "POST (Name, Email, Duration)" --> Gateway
    Gateway -- "Formats ISO-8601 & Generates Crypto Token" --> Gateway
    Gateway -- "REST API (POST /merakiAuthUsers)" --> CiscoCloud
    CiscoCloud -- "Writes User" --> DB
    Gateway -- "Returns Login Data" --> Admin
    
    DB -. "Syncs Security Rules" .-> AP
    Guest -- "Connects via Captive Portal" --> AP
    AP -- "RADIUS/Meraki Auth Check" --> DB