# src/core/initialize.py
from __future__ import annotations
import os
import sys
import pathlib
import logging # Import standard logging
from dotenv import load_dotenv

# --- Zoho SDK Imports ---
from zohocrmsdk.src.com.zoho.crm.api.initializer import Initializer
from zohocrmsdk.src.com.zoho.crm.api.sdk_config import SDKConfig
from zohocrmsdk.src.com.zoho.crm.api.dc import USDataCenter, EUDataCenter, INDataCenter, CNDataCenter, AUDataCenter
from zohocrmsdk.src.com.zoho.api.authenticator import OAuthToken
from zohocrmsdk.src.com.zoho.api.authenticator.store import FileStore
from zohocrmsdk.src.com.zoho.api.logger import Logger as SDKLogger # Rename SDK logger
# REMOVED: from zohocrmsdk.src.com.zoho.crm.api.util import SDKException # <-- REMOVE THIS LINE

# --- Project Structure Setup ---
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "zoho_data" # Corrected path from previous edits
LOGS_DIR = PROJECT_ROOT / "logs"
TOKEN_DIR = DATA_DIR / "tokens"
API_RESOURCES_DIR = DATA_DIR / "api_resources"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
TOKEN_DIR.mkdir(exist_ok=True)
API_RESOURCES_DIR.mkdir(exist_ok=True)

token_file = TOKEN_DIR / "token_store.txt"
app_log_file = LOGS_DIR / "app.log" # Application log
sdk_log_file = LOGS_DIR / "sdk.log" # SDK internal log

# --- Application Logging Setup (Standard Python Logging) ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# File Handler for application logs
file_handler = logging.FileHandler(str(app_log_file))
file_handler.setFormatter(log_formatter)

# Console Handler for application logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Get the application logger instance
logger = logging.getLogger('zoho_app')
logger.setLevel(logging.DEBUG) # Set the desired level for your app logs
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False

logger.info("Application logging configured.")

# --- Zoho SDK Configuration ---
_DC_MAP = {
    "com": USDataCenter.PRODUCTION(),
    "eu": EUDataCenter.PRODUCTION(),
    "in": INDataCenter.PRODUCTION(),
    "com.cn": CNDataCenter.PRODUCTION(),
    "com.au": AUDataCenter.PRODUCTION(),
}

def _pick_dc(accounts_url: str):
    """Selects the Zoho Data Center object based on the accounts URL TLD."""
    try:
        if not isinstance(accounts_url, str):
            logger.warning(f"ACCOUNTS_URL is not a string ('{accounts_url}'), defaulting to US DC.")
            return USDataCenter.PRODUCTION()
        domain_part = accounts_url.split('//')[-1].split('/')[0]
        tld = domain_part.split('accounts.zoho.')[-1]
        selected_dc = _DC_MAP.get(tld)
        if selected_dc:
             logger.info(f"Picked Data Center for TLD '{tld}'.")
             return selected_dc
        else:
             logger.warning(f"Could not map TLD '{tld}' to a Data Center, defaulting to US.")
             return USDataCenter.PRODUCTION()
    except Exception as e:
        logger.error(f"Error picking Data Center from URL '{accounts_url}': {e}", exc_info=True)
        logger.warning("Defaulting to US Data Center due to error.")
        return USDataCenter.PRODUCTION()

# Load .env variables from project root
dotenv_path = PROJECT_ROOT / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(".env file loaded.")
else:
    logger.warning(f".env file not found at {dotenv_path}. SDK might fail if env vars not set externally.")

# --- SDK Initialization ---
if not Initializer.get_initializer():
    logger.info("Attempting Zoho CRM SDK Initialization...")
    try:
        # Environment
        accounts_url_env = os.getenv("ACCOUNTS_URL", "https://accounts.zoho.com")
        environment = _pick_dc(accounts_url_env)
        logger.debug(f"Using Environment: {environment}, derived from ACCOUNTS_URL: {accounts_url_env}")

        # Token
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        refresh_token = os.getenv("REFRESH_TOKEN")
        if not all([client_id, client_secret, refresh_token]):
             logger.critical("Missing required OAuth credentials (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN) in environment variables.")
             raise ValueError("Missing required OAuth credentials in environment variables.")

        token = OAuthToken(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            redirect_url="http://localhost"
        )
        logger.debug("OAuthToken object created.")

        # Token Store
        store = FileStore(file_path=str(token_file))
        logger.debug(f"Using FileStore at: {token_file}")

        # SDK Config
        sdk_config = SDKConfig(
            auto_refresh_fields=True,
            pick_list_validation=False,
        )
        logger.debug(f"SDKConfig: auto_refresh_fields={sdk_config.get_auto_refresh_fields()}, pick_list_validation={sdk_config.get_pick_list_validation()}")

        # Resource Path
        resource_path = str(API_RESOURCES_DIR)
        logger.debug(f"Using SDK resource path: {resource_path}")

        # SDK Logger
        sdk_internal_logger = SDKLogger.get_instance(level=SDKLogger.Levels.INFO, file_path=str(sdk_log_file))
        logger.debug(f"SDK internal logger configured at: {sdk_log_file}")

        # Request Proxy
        request_proxy = None

        # --- Perform Initialization ---
        Initializer.initialize(
            environment=environment,
            token=token,
            store=store,
            sdk_config=sdk_config,
            resource_path=resource_path,
            logger=sdk_internal_logger,
            proxy=request_proxy
        )
        logger.info("Zoho CRM SDK Initialization successful.")

    # REMOVED specific SDKException catch
    # except SDKException as e:
    #    logger.critical(f"SDK Initialization Failed (SDKException): {e.message}", exc_info=True)
    #    raise RuntimeError(f"Fatal: Zoho SDK Initialization Failed (SDKException). Check logs. Error: {e.message}")
    except ValueError as e: # Catch missing credentials error
        logger.critical(f"SDK Initialization Failed: {e}")
        raise RuntimeError(f"Fatal: Zoho SDK Initialization Failed. {e}")
    except Exception as e: # General catch-all remains
        logger.critical(f"SDK Initialization Failed (Unexpected Error): {e}", exc_info=True)
        raise RuntimeError(f"Fatal: Zoho SDK Initialization Failed (Unexpected Error). Check logs. Error: {e}")
else:
     logger.info("Zoho CRM SDK already initialized.")

# --- End of src/core/initialize.py ---