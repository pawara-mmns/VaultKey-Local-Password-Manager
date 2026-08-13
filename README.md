# VaultKey

VaultKey is a local-first desktop password manager built with Python and PySide6. This repository currently contains the Phase 1 application shell: a responsive dark interface, reusable navigation, dashboard, and placeholder views for the planned vault features.

No credential storage, master-password handling, database, or encryption is implemented in Phase 1.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux with desktop support

## Setup

Create and activate a virtual environment, then install the dependency:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate` instead.

## Run

```powershell
python main.py
```

The window has a minimum size of 1100 × 700 and uses layouts throughout so content adapts as it is resized.

## Current structure

```text
VaultKey/
├── main.py
├── requirements.txt
├── app/
│   ├── application.py
│   ├── config.py
│   ├── components/
│   │   ├── page_widgets.py
│   │   └── sidebar.py
│   └── ui/
│       ├── main_window.py
│       ├── dashboard.py
│       ├── vault_page.py
│       ├── favorites_page.py
│       ├── generator_page.py
│       ├── categories_page.py
│       └── settings_page.py
├── styles/dark.qss
├── assets/
└── data/
```

## Roadmap

Phase 2 will add first-launch vault setup, unlock flow, SQLite initialization, and secure master-password handling. It is intentionally not included in this phase.
