# src/api/leads/common.py

import os
import traceback
from dotenv import load_dotenv

# --- SDK Imports (Keep if specific SDK classes are needed here, otherwise remove) ---
# from zohocrmsdk.src.com.zoho.crm.api.record import (...)
# from zohocrmsdk.src.com.zoho.crm.api import (...)

# --- Logging Setup ---
# Import the application logger configured in initialize.py
try:
    from src.core.initialize import logger, PROJECT_ROOT # Import logger and PROJECT_ROOT
except ImportError as e:
    import logging
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger('zoho_common_fallback')
    logger.error(f"Failed to import logger/PROJECT_ROOT from src.core.initialize: {e}")
    # Define PROJECT_ROOT manually as a fallback if needed elsewhere in this file
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Configuration ---
MODULE = "Leads"
# Fields potentially required by layout/system for the UPDATE workaround
UPDATE_REQ_FIELDS = ["Last_Name", "Company", "Lead_Status"]
# Fields needed for the QUALIFICATION task (using Custom View)
# Ensure these API names are correct for your Leads module
QUALIFY_FIELDS = ["id", "First_Name", "Last_Name", "Email", "Lead_Status", "Additional_Relocation_Notes"]

# --- Load Data from .env ---
# Load environment variables from .env file in the project root
# initialize.py already loads it, but doing it here ensures these vars are loaded
# if common.py is imported before initialize.py somehow (though unlikely with cli.py entry)
dotenv_path = PROJECT_ROOT / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    # logger.debug(".env loaded in common.py (might be redundant).") # Optional debug log
else:
    logger.warning(f".env file not found at {dotenv_path} when loading from common.py.")


# Variables for the update example
try:
    TARGET_LEAD_ID_FOR_UPDATE = int(os.getenv("LEAD_ID", "0"))
    NEW_MOBILE_FOR_UPDATE = os.getenv("NEW_MOBILE", "")
    # Log warnings if defaults are used or values are invalid
    if TARGET_LEAD_ID_FOR_UPDATE == 0:
        logger.debug("LEAD_ID not set or invalid in .env. Default update requires explicit --id.")
    if not NEW_MOBILE_FOR_UPDATE:
        logger.debug("NEW_MOBILE not set in .env. Default update requires explicit --mobile.")
except ValueError:
    logger.warning(f"Invalid LEAD_ID '{os.getenv('LEAD_ID')}' in .env. Defaulting update ID to 0.")
    TARGET_LEAD_ID_FOR_UPDATE = 0
    NEW_MOBILE_FOR_UPDATE = os.getenv("NEW_MOBILE", "") # Still try to get mobile
except Exception as e:
    logger.error(f"Error loading .env variables for update defaults: {e}", exc_info=True)
    TARGET_LEAD_ID_FOR_UPDATE = 0
    NEW_MOBILE_FOR_UPDATE = ""

# Variable for the qualification example
try:
    QUALIFICATION_CUSTOM_VIEW_ID = os.getenv("QUALIFICATION_CUSTOM_VIEW_ID", "")
    if not QUALIFICATION_CUSTOM_VIEW_ID:
         logger.debug("QUALIFICATION_CUSTOM_VIEW_ID not set in .env. Default qualify requires explicit --cvid.")
except Exception as e:
    logger.error(f"Error loading QUALIFICATION_CUSTOM_VIEW_ID from .env: {e}", exc_info=True)
    QUALIFICATION_CUSTOM_VIEW_ID = ""


# --- Helper Functions ---
def extract_field_value(record, field_name):
    """
    Helper function to extract field values from Zoho Record objects,
    handling potential Choice objects (used in qualify.py).

    Args:
        record: The Zoho Record object.
        field_name (str): The API name of the field to extract.

    Returns:
        The extracted field value (usually string or None), simplified from Choice objects.
    """
    if not hasattr(record, 'get_key_value'):
        logger.warning(f"Attempted to extract '{field_name}' from non-record object: {type(record)}")
        return None

    try:
        field_value = record.get_key_value(field_name)
        if field_value is None:
            # logger.debug(f"Field '{field_name}' is None in record.")
            return None
        # Handle Choice objects (like Lead_Status often is)
        if hasattr(field_value, 'get_value') and callable(field_value.get_value):
            # logger.debug(f"Extracting value from Choice object for '{field_name}'.")
            return field_value.get_value()
        # Handle lists (e.g., multi-select lookups - return as is for now)
        if isinstance(field_value, list):
            # logger.debug(f"Field '{field_name}' is a list.")
            return field_value
        # Assume other types are primitive enough (string, int, bool, etc.)
        # logger.debug(f"Field '{field_name}' value: {field_value} (Type: {type(field_value)})")
        return field_value
    except Exception as e:
        logger.error(f"Error extracting field '{field_name}' from record: {e}", exc_info=True)
        return None

# --- End of src/api/leads/common.py ---