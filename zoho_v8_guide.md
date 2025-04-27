# Definitive Guide: Setting Up and Using Zoho CRM Python SDK (`zohocrmsdk`) - Rev. 4 (Refactored)

This guide details the reliable, step-by-step method to initialize and use the `zohocrmsdk` Python package for Zoho CRM API v8. This process reflects a refactored project structure for better maintainability and incorporates workarounds discovered during implementation.

**Target SDK:** `zohocrmsdk` (Latest recommended version)
**Target API:** Zoho CRM API v8

### Prerequisites

1.  **Python:** Version 3.x installed.
2.  **pip:** Python package installer.
3.  **Zoho CRM Account:** An active account with API access.
4.  **Zoho API Console Access:** ([https://api-console.zoho.com](https://api-console.zoho.com)).
5.  **PowerShell (Windows)** or **`curl` (macOS/Linux):** For the one-time manual token exchange.

---

### Phase 1: One-Time Setup - Obtaining Credentials & Refresh Token

*(Perform these steps only once per application setup, or if your Refresh Token is revoked).*

1.  **Register a Self-Client Application:**
    *   Go to the [Zoho API Console](https://api-console.zoho.com).
    *   Click **GET STARTED** or **Add Client** -> **Self Client** -> **CREATE** -> **OK**.
    *   Go to the **Client Secret** tab. Copy your **Client ID** and **Client Secret**.

2.  **Generate Initial Grant Token (With ALL Required Scopes):**
    *   In the Self Client view -> **Generate Code** tab.
    *   **Scope field (Crucial):** `ZohoCRM.modules.ALL,ZohoCRM.settings.ALL,ZohoCRM.users.READ,ZohoCRM.org.READ` (Adjust if fewer scopes are needed, but these cover most common uses and initialization checks).
    *   **Time Duration:** 10 minutes.
    *   Click **CREATE** -> Select Portal/Org -> **CREATE**.
    *   **Immediately copy the generated Grant Token (Code)**.

3.  **Manually Exchange Grant Token for Refresh Token:**
    *   **Immediately** (within 10 mins), open **Windows PowerShell**.
    *   Execute (replace placeholders):
        ```powershell
        Invoke-RestMethod -Method Post -Uri "https://accounts.zoho.com/oauth/v2/token" -Body @{
            grant_type    = "authorization_code"
            client_id     = "YOUR_CLIENT_ID_HERE"
            client_secret = "YOUR_CLIENT_SECRET_HERE"
            code          = "YOUR_GRANT_TOKEN_HERE"
        }
        ```
    *   From the JSON output, **copy the `"refresh_token"` value**. Store this securely.

4.  **Create and Populate `.env` File:**
    *   In your project root directory (`d:\zoho_v8`), create a file named `.env` (or copy from `.env.template`).
    *   Ensure it contains:
        ```dotenv
        # .env file for Zoho CRM SDK

        CLIENT_ID=YOUR_CLIENT_ID_HERE
        CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
        REFRESH_TOKEN=YOUR_REFRESH_TOKEN_HERE_FROM_STEP_3

        # Your Zoho login email (used for UserSignature in operations)
        USER_EMAIL=your_zoho_login_email@example.com

        # Account URL (Used to determine DataCenter, e.g., .com, .eu, .com.au)
        ACCOUNTS_URL=https://accounts.zoho.com

        # --- Variables for the lead update example ---
        LEAD_ID_TO_UPDATE=YOUR_LEAD_ID_HERE
        NEW_MOBILE_NUMBER=YOUR_NEW_MOBILE_HERE
        ```

---

### Phase 2: Python Project Setup

5.  **Project Structure Overview:**
    ```
    d:\zoho_v8\
    ├── .env
    ├── .env.template
    ├── src/
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── leads.py      # Lead operations
    │   ├── core/
    │   │   ├── __init__.py
    │   │   └── initialize.py # SDK initialization
    │   ├── tests/
    │   │   └── ...           # Test scripts
    │   └── __init__.py
    ├── data/
    │   ├── tokens/         # Token storage
    │   └── api_resources/  # SDK resources
    ├── logs/               # Log files
    └── venv/               # Virtual environment
    ```

6.  **Create and Activate Virtual Environment (from `d:\zoho_v8`):**
    *   `python -m venv venv`
    *   Activate: `.\venv\Scripts\Activate.ps1` (Win PS), `.\venv\Scripts\activate.bat` (Win Cmd), or `source venv/bin/activate` (Mac/Linux)

7.  **Install Required Libraries:**
    *   `(venv) pip install --upgrade pip`
    *   `(venv) pip install zohocrmsdk python-dotenv`

---

### Phase 3: SDK Initialization Code (`src/core/initialize.py`)

8.  **Review `src/core/initialize.py`:**
    *   This script handles the SDK initialization using the credentials from `.env`.
    *   It dynamically determines the DataCenter based on `ACCOUNTS_URL`.
    *   It configures `FileStore` to use `data/tokens/token_store.txt`.
    *   It sets the SDK resource path to `data/api_resources`.
    *   It configures logging to `logs/sdk.log`.
    *   Crucially, it uses the **Refresh Token** flow for authentication.

    ```python
    # Excerpt from src/core/initialize.py (Conceptual)
    import os
    from dotenv import load_dotenv
    from zohocrmsdk.src.com.zoho.api.authenticator import OAuthToken
    from zohocrmsdk.src.com.zoho.api.authenticator.store import FileStore
    from zohocrmsdk.src.com.zoho.crm.api.initializer import Initializer
    from zohocrmsdk.src.com.zoho.crm.api.dc import USDataCenter, EUDataCenter, INDataCenter, CNDataCenter, AUDataCenter # etc.
    from zohocrmsdk.src.com.zoho.api.logger import Logger
    from zohocrmsdk.src.com.zoho.crm.api.sdk_config import SDKConfig

    # --- Determine Project Root --- (Example implementation)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Navigate up from src/core/initialize.py

    # --- Load Environment Variables ---
    load_dotenv(os.path.join(project_root, '.env'))

    # --- Configure Paths Dynamically ---
    log_file_path = os.path.join(project_root, "logs", "sdk.log")
    token_store_path = os.path.join(project_root, "data", "tokens", "token_store.txt")
    resource_path = os.path.join(project_root, "data", "api_resources")

    # --- Ensure Directories Exist ---
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    os.makedirs(os.path.dirname(token_store_path), exist_ok=True)
    os.makedirs(resource_path, exist_ok=True)

    # --- Logger Setup ---
    logger = Logger.get_instance(level=Logger.Levels.INFO, file_path=log_file_path)

    # --- Initialization Function ---
    def initialize_sdk():
        if Initializer.get_initializer() is not None:
            return True, logger
        try:
            # Determine Environment from ACCOUNTS_URL
            accounts_url = os.getenv('ACCOUNTS_URL', 'https://accounts.zoho.com') # Default to .com
            environment = USDataCenter.PRODUCTION() # Default
            if '.eu' in accounts_url: environment = EUDataCenter.PRODUCTION()
            elif '.in' in accounts_url: environment = INDataCenter.PRODUCTION()
            elif '.com.cn' in accounts_url: environment = CNDataCenter.PRODUCTION()
            elif '.com.au' in accounts_url: environment = AUDataCenter.PRODUCTION()
            # Add more conditions here if other data centers are needed

            # Token using Refresh Token
            token = OAuthToken(
                client_id=os.getenv("CLIENT_ID"),
                client_secret=os.getenv("CLIENT_SECRET"),
                refresh_token=os.getenv("REFRESH_TOKEN"),
                redirect_url="http://localhost" # Dummy required
            )
            store = FileStore(file_path=token_store_path)
            config = SDKConfig(auto_refresh_fields=True, pick_list_validation=False)

            # Initialize
            Initializer.initialize(
                environment=environment,
                token=token,
                store=store,
                sdk_config=config,
                resource_path=resource_path,
                logger=logger
            )
            return True, logger
        except Exception as e:
            logger.error(f"SDK Initialization Failed: {e}")
            return False, logger

    # --- Trigger Initialization on Import ---
    IS_INITIALIZED, SDK_LOGGER = initialize_sdk()
    if not IS_INITIALIZED:
        print("CRITICAL: SDK Initialization failed on module load. Check logs.")
    ```

---

### Phase 4: Example Operation Code (`src/api/leads.py`)

9.  **Review `src/api/leads.py`:**
    *   This script demonstrates updating a lead's mobile number.
    *   It imports `Initializer` from `src.core.initialize` which triggers the initialization.
    *   It uses `UserSignature` with the email from `.env` for the API call.
    *   It includes the workaround for potential `MANDATORY_NOT_FOUND` errors by fetching the record first (though not strictly required if only updating non-mandatory, non-layout-rule-affected fields like Mobile).

    ```python
    # Excerpt from src/api/leads.py (Conceptual)
    import os
    from dotenv import load_dotenv
    from zohocrmsdk.src.com.zoho.crm.api.record import Record, BodyWrapper
    from zohocrmsdk.src.com.zoho.crm.api.modules import ModulesOperations
    from zohocrmsdk.src.com.zoho.crm.api.record import RecordOperations
    from zohocrmsdk.src.com.zoho.crm.api.user_signature import UserSignature
    from zohocrmsdk.src.com.zoho.crm.api.util import APIResponse

    # Import to trigger initialization
    from src.core.initialize import Initializer, SDK_LOGGER, IS_INITIALIZED

    # --- Load Lead ID and Mobile from .env ---
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(project_root, '.env'))
    lead_id_to_update = int(os.getenv('LEAD_ID_TO_UPDATE', 0))
    new_mobile = os.getenv('NEW_MOBILE_NUMBER', '')
    user_email = os.getenv('USER_EMAIL', '')

    # --- Update Function ---
    def update_lead_mobile(lead_id: int, mobile: str):
        if not Initializer.get_initializer(): # Double check, though IS_INITIALIZED should cover it
            SDK_LOGGER.error("SDK not initialized. Cannot update lead.")
            return
        if not lead_id or not mobile or not user_email:
            SDK_LOGGER.error("Lead ID, New Mobile, or User Email missing in .env")
            return

        try:
            record_operations = RecordOperations()
            request = BodyWrapper()
            record1 = Record()
            record1.set_id(lead_id)
            # Use add_key_value for robustness, especially if field names change
            record1.add_key_value('Mobile', mobile) # Assuming 'Mobile' is the API name
            request.set_data([record1])

            user = UserSignature(email=user_email)
            SDK_LOGGER.info(f"Attempting to update Lead ID: {lead_id} with Mobile: {mobile}")

            # Pass the UserSignature instance directly to the user parameter
            response = record_operations.update_records('Leads', request, user=user)

            # Process response...
            if response is not None:
                SDK_LOGGER.info(f"Update Response Status Code: {response.get_status_code()}")
                action_response = response.get_object()
                if isinstance(action_response, ActionWrapper):
                    action_response_list = action_response.get_data()
                    for action_result in action_response_list:
                        if isinstance(action_result, SuccessResponse):
                            SDK_LOGGER.info(f"Status: {action_result.get_status().get_value()}")
                            SDK_LOGGER.info(f"Code: {action_result.get_code().get_value()}")
                            SDK_LOGGER.info(f"Details: {action_result.get_details()}")
                            SDK_LOGGER.info(f"Message: {action_result.get_message().get_value()}")
                        elif isinstance(action_result, APIException):
                            SDK_LOGGER.error(f"Status: {action_result.get_status().get_value()}")
                            SDK_LOGGER.error(f"Code: {action_result.get_code().get_value()}")
                            SDK_LOGGER.error(f"Details: {action_result.get_details()}")
                            SDK_LOGGER.error(f"Message: {action_result.get_message().get_value()}")
                elif isinstance(action_response, APIException):
                    SDK_LOGGER.error(f"Status: {action_response.get_status().get_value()}")
                    SDK_LOGGER.error(f"Code: {action_response.get_code().get_value()}")
                    SDK_LOGGER.error(f"Details: {action_response.get_details()}")
                    SDK_LOGGER.error(f"Message: {action_response.get_message().get_value()}")
            else:
                SDK_LOGGER.warning("Received no response from the server for update operation.")

        except Exception as e:
            SDK_LOGGER.error(f"Error updating lead: {e}", exc_info=True)

    # --- Main Execution Block ---
    if __name__ == "__main__":
        if IS_INITIALIZED:
            SDK_LOGGER.info("SDK Initialized. Proceeding with lead update.")
            update_lead_mobile(lead_id_to_update, new_mobile)
            SDK_LOGGER.info("Lead update process finished.")
        else:
            print("Cannot run lead update: SDK failed to initialize. Check logs/sdk.log")
            SDK_LOGGER.critical("Cannot run lead update: SDK failed to initialize.")
    ```

---

### Phase 5: Running the Code

10. **Run Operations (from project root `d:\zoho_v8`):**
    *   Ensure your virtual environment (`venv`) is activated.
    *   **To update the lead:**
        ```bash
        (venv) python -m src.api.leads
        ```
    *   **To run tests (example):**
        ```bash
        (venv) python -m src.tests.test_init
        ```

---

### Troubleshooting Notes

*   **Initialization Failure:** Check `logs/sdk.log`. Ensure `.env` has correct `CLIENT_ID`, `CLIENT_SECRET`, `REFRESH_TOKEN`. Verify `ACCOUNTS_URL` matches your Zoho region (.com, .eu etc.). Check network connectivity.
*   **`INVALID_TOKEN` / `OAUTH_SCOPE_MISMATCH`:** Ensure the Refresh Token was generated with *all* required scopes (`ZohoCRM.modules.ALL`, etc.). You may need to regenerate the Grant/Refresh token (Phase 1).
*   **`MANDATORY_NOT_FOUND` on Update:** While less common for simple fields like Mobile, if you update other fields, you might need to fetch the record first, get its data map, update the specific field in the map, and then send the entire map back in the update request. The `leads.py` example might include this pattern if needed.
*   **Import Errors:** Ensure the virtual environment is active and you are running commands from the project root (`d:\zoho_v8`) using the `python -m src...` format.
*   **Path Errors:** The dynamic path calculation in `initialize.py` should handle locating `data` and `logs` correctly, but double-check permissions if errors persist.
*   **`AttributeError: 'NoneType' object has no attribute 'get_status_code'` (or similar on response):** This often means the API call failed before returning a standard response object. Check the `logs/sdk.log` for detailed errors from the SDK, often related to initialization issues, invalid user email, or missing required fields not caught by basic validation.
*   **UserSignature:** Make sure the `USER_EMAIL` in `.env` exactly matches the email of an active, confirmed user in your Zoho CRM instance who has permission to perform the operation.