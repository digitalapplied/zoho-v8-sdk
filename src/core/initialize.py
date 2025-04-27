from __future__ import annotations
import os
import sys
import pathlib
import logging
from dotenv import load_dotenv

from zohocrmsdk.src.com.zoho.crm.api.initializer import Initializer
from zohocrmsdk.src.com.zoho.crm.api.sdk_config import SDKConfig
from zohocrmsdk.src.com.zoho.crm.api.dc import USDataCenter, EUDataCenter, INDataCenter, CNDataCenter, AUDataCenter
from zohocrmsdk.src.com.zoho.api.authenticator import OAuthToken
from zohocrmsdk.src.com.zoho.api.authenticator.store import FileStore
from zohocrmsdk.src.com.zoho.api.logger import Logger

# Dynamically find the project root (d:\zoho_v8)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent 

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
TOKEN_DIR = DATA_DIR / "tokens"
# Directory where SDK will create its 'resources' folder
API_RESOURCES_DIR = DATA_DIR / "api_resources" 

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
TOKEN_DIR.mkdir(exist_ok=True)
API_RESOURCES_DIR.mkdir(exist_ok=True)

token_file = TOKEN_DIR / "token_store.txt"
log_file = LOGS_DIR / "sdk.log"

# Configure Python's standard logging module for use in other modules
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- File Handler --- 
# Configure file logging first (basicConfig does this if filename is provided)
logging.basicConfig(
    filename=str(log_file),
    level=logging.DEBUG, # Keep DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    # force=True # Use force=True if basicConfig might have run before, though unlikely here
)

# --- Console Handler --- 
# Explicitly add a handler for console output
console_handler = logging.StreamHandler(sys.stdout) # Log to standard output
console_handler.setLevel(logging.DEBUG) # Set level for console
console_handler.setFormatter(log_formatter) # Use the same format

# Add the console handler to the root logger
logging.getLogger().addHandler(console_handler)
# Alternatively, add only to our specific logger:
# logging.getLogger('zoho_sdk').addHandler(console_handler)

# Create a logger that can be imported by other modules
logger = logging.getLogger('zoho_sdk')
# Ensure our specific logger also respects the DEBUG level if it was created before basicConfig
logger.setLevel(logging.DEBUG)

_DC_MAP = {
    "com": USDataCenter.PRODUCTION(),
    "eu": EUDataCenter.PRODUCTION(),
    "in": INDataCenter.PRODUCTION(),
    "com.cn": CNDataCenter.PRODUCTION(),
    "com.au": AUDataCenter.PRODUCTION(),
}

def _pick_dc(accounts_url: str):
    tld = accounts_url.split("accounts.")[-1]
    return _DC_MAP.get(tld, USDataCenter.PRODUCTION())

load_dotenv()

if not Initializer.get_initializer():
    env = _pick_dc(os.getenv("ACCOUNTS_URL", "https://accounts.zoho.com"))
    token = OAuthToken(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        refresh_token=os.getenv("REFRESH_TOKEN"),
        redirect_url="http://localhost"
    )

    Initializer.initialize(
        environment=env,
        token=token,
        store=FileStore(str(token_file)),
        sdk_config=SDKConfig(auto_refresh_fields=True),
        resource_path=str(API_RESOURCES_DIR),
        logger=Logger.get_instance(Logger.Levels.INFO, str(log_file)),
    )
