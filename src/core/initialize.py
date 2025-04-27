from __future__ import annotations
import os
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
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger that can be imported by other modules
logger = logging.getLogger('zoho_sdk')

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
