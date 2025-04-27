# Zoho CRM Python SDK v8 Implementation

A field-tested implementation of the Zoho CRM Python SDK v8 (`zohocrmsdk`), following best practices for authentication, initialization, and API operations within a structured Python package.

## Features

- Automatic DataCenter detection based on account URL (`ACCOUNTS_URL` in `.env`)
- Proper token management with FileStore for automatic renewals
- Safe Lead update pattern that pre-fetches mandatory fields
- Robust path handling for data and log files
- Organized project structure using Python packages

## Project Structure

```
d:\zoho_v8\
├── .env                # Environment variables (Create from .env.template)
├── .env.template       # Template for environment variables
├── .gitignore          # Git ignore configuration
├── README.md           # This file
├── CHECKLIST.md        # Implementation progress tracking
├── zoho_v8_guide.md    # Original guide
├── src/                # Source code package
│   ├── api/            # API interaction modules
│   │   ├── __init__.py
│   │   └── leads.py    # Lead operations logic
│   ├── core/           # Core application logic/setup
│   │   ├── __init__.py
│   │   └── initialize.py # SDK initialization
│   ├── tests/          # Test suite
│   │   ├── __init__.py
│   │   └── test_init.py # Initialization tests
│   └── __init__.py
├── data/               # Data files (ignored by Git)
│   ├── tokens/         # Token storage
│   │   └── token_store.txt
│   └── api_resources/  # SDK generated resources
│       └── resources/
├── logs/               # Application logs (ignored by Git)
│   └── sdk.log
└── venv/               # Virtual environment (ignored by Git)
```

## Setup

1.  **Clone the repository** (if you haven't already).

2.  **Create and activate a virtual environment:**
    ```bash
    # Navigate to the project root directory (d:\zoho_v8)
    python -m venv venv

    # Activate the environment (choose one based on your shell)
    .\venv\Scripts\Activate.ps1  # Windows PowerShell
    .\venv\Scripts\activate.bat  # Windows Command Prompt
    source venv/bin/activate     # Linux/macOS (Bash/Zsh)
    ```

3.  **Install dependencies:**
    ```bash
    # Ensure pip is up-to-date
    python -m pip install --upgrade pip

    # Install required packages (replace with your actual requirements file if you have one)
    pip install python-dotenv zohocrmsdk
    ```
    *Note: If you create a `requirements.txt` file, use `pip install -r requirements.txt`.* 

4.  **Configure Environment Variables:**
    - Copy `.env.template` to `.env`.
    - Fill in the required values in the `.env` file (`ACCOUNTS_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `REFRESH_TOKEN`, `LEAD_ID`, `NEW_MOBILE`).

## Usage

Ensure your virtual environment is activated before running any scripts.
All commands should be run from the project root directory (`d:\zoho_v8`).

*   **Run Lead Update:**
    ```bash
    python -m src.api.leads
    ```
    *This script will initialize the SDK (if not already done) and attempt to update the lead specified in your `.env` file.*

*   **Run Initialization Tests:**
    ```bash
    python -m src.tests.test_init
    ```
    *This script tests the SDK initialization process.*

## Notes

- The SDK initialization (`src.core.initialize`) is automatically triggered when modules like `src.api.leads` or `src.tests.test_init` are imported.
- Log files are stored in the `logs/` directory.
- Token information is stored in `data/tokens/`.
- SDK resource files are stored in `data/api_resources/`.
