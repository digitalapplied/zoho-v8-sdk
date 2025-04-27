# src/api/leads/common.py

import os
import traceback
from dotenv import load_dotenv

# --- SDK Imports ---
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, BodyWrapper, Record, APIException, SuccessResponse,
    ActionWrapper, GetRecordsParam, Info, GetRecordParam, ResponseWrapper
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

# --- Initialize SDK ---
# This import ensures the code in src/core/initialize.py runs if not already initialized
from src.core import initialize
from src.core.initialize import logger  # Import the configured logger

# --- Configuration ---
# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

MODULE = "Leads"
# Fields potentially required by layout/system for the UPDATE workaround
UPDATE_REQ_FIELDS = ["Last_Name", "Company", "Lead_Status"]
# Fields needed for the QUALIFICATION task
QUALIFY_FIELDS = ["id", "First_Name", "Last_Name", "Email", "Lead_Status", "Additional_Relocation_Notes"]

# --- Load Data from .env ---
# Load environment variables from .env file in the project root
load_dotenv()

# Variables for the update example (keep for reference or future use)
try:
    TARGET_LEAD_ID_FOR_UPDATE = int(os.getenv("LEAD_ID", "0"))  # Default to 0 if not set
    NEW_MOBILE_FOR_UPDATE = os.getenv("NEW_MOBILE", "")
    if TARGET_LEAD_ID_FOR_UPDATE == 0:
        logger.warning("LEAD_ID not set or invalid in .env. Update function will be skipped if called.")
    if not NEW_MOBILE_FOR_UPDATE:
        logger.warning("NEW_MOBILE not set in .env. Update function will be skipped if called.")

except ValueError:
    logger.warning(f"Invalid LEAD_ID in .env: '{os.getenv('LEAD_ID')}'. Using 0.")
    TARGET_LEAD_ID_FOR_UPDATE = 0
    NEW_MOBILE_FOR_UPDATE = os.getenv("NEW_MOBILE", "")  # Still try to get mobile
except Exception as e:
    logger.error(f"Error loading .env variables for update: {e}")
    TARGET_LEAD_ID_FOR_UPDATE = 0
    NEW_MOBILE_FOR_UPDATE = ""

# Variable for the qualification example
try:
    # Add default empty string if not found
    QUALIFICATION_CUSTOM_VIEW_ID = os.getenv("QUALIFICATION_CUSTOM_VIEW_ID", "")
    if not QUALIFICATION_CUSTOM_VIEW_ID:
         logger.warning("QUALIFICATION_CUSTOM_VIEW_ID not set in .env. Qualification by CV might require explicit ID.")
except Exception as e:
    logger.error(f"Error loading QUALIFICATION_CUSTOM_VIEW_ID from .env: {e}")
    QUALIFICATION_CUSTOM_VIEW_ID = ""

# --- Helper Functions ---

def extract_field_value(record, field_name):
    """
    Helper function to extract field values from Zoho records,
    handling Choice objects properly.
    
    Args:
        record: The Zoho record object
        field_name: The name of the field to extract
        
    Returns:
        The extracted field value
    """
    field_value = record.get_key_value(field_name)
    if field_value is None:
        return None
    # Handle Choice objects
    if hasattr(field_value, 'get_value'):
        return field_value.get_value()
    return field_value
