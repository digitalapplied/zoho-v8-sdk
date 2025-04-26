from __future__ import annotations
import os, pathlib
from dotenv import load_dotenv

from zohocrmsdk.src.com.zoho.crm.api.initializer import Initializer
from zohocrmsdk.src.com.zoho.crm.api.sdk_config import SDKConfig
from zohocrmsdk.src.com.zoho.crm.api.dc import USDataCenter, EUDataCenter, INDataCenter, CNDataCenter, AUDataCenter
from zohocrmsdk.src.com.zoho.api.authenticator import OAuthToken
from zohocrmsdk.src.com.zoho.api.authenticator.store import FileStore
from zohocrmsdk.src.com.zoho.api.logger import Logger

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
    resources = pathlib.Path("resources").resolve()
    resources.mkdir(exist_ok=True)

    Initializer.initialize(
        environment=env,
        token=token,
        store=FileStore("resources/token_store.txt"),
        sdk_config=SDKConfig(auto_refresh_fields=True),
        resource_path=str(resources),
        logger=Logger.get_instance(Logger.Levels.INFO, "logs/sdk.log"),
    )
