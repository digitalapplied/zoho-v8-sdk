# src/api/leads.py

import os
import traceback
from dotenv import load_dotenv

# --- SDK Imports ---
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, BodyWrapper, Record, APIException, SuccessResponse,
    ActionWrapper, GetRecordsParam, Info, GetRecordParam, ResponseWrapper # Added ResponseWrapper
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

# --- Initialize SDK ---
# This import ensures the code in src/core/initialize.py runs if not already initialized
from src.core import initialize
from src.core.initialize import logger # Import the configured logger

# --- Configuration ---
# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE = "Leads"
# Fields potentially required by layout/system for the UPDATE workaround
_UPDATE_REQ_FIELDS = ["Last_Name", "Company", "Lead_Status"]
# Fields needed for the QUALIFICATION task
_QUALIFY_FIELDS = ["id", "First_Name", "Last_Name", "Email", "Lead_Status", "Additional_Relocation_Notes"]

# --- Load Data from .env ---
# Load environment variables from .env file in the project root
load_dotenv()

# Variables for the update example (keep for reference or future use)
try:
    _TARGET_LEAD_ID_FOR_UPDATE = int(os.getenv("LEAD_ID", "0")) # Default to 0 if not set
    _NEW_MOBILE_FOR_UPDATE = os.getenv("NEW_MOBILE", "")
    if _TARGET_LEAD_ID_FOR_UPDATE == 0:
        logger.warning("LEAD_ID not set or invalid in .env. Update function will be skipped if called.")
    if not _NEW_MOBILE_FOR_UPDATE:
        logger.warning("NEW_MOBILE not set in .env. Update function will be skipped if called.")

except ValueError:
    logger.warning(f"Invalid LEAD_ID in .env: '{os.getenv('LEAD_ID')}'. Using 0.")
    _TARGET_LEAD_ID_FOR_UPDATE = 0
    _NEW_MOBILE_FOR_UPDATE = os.getenv("NEW_MOBILE", "") # Still try to get mobile
except Exception as e:
    logger.error(f"Error loading .env variables for update: {e}")
    _TARGET_LEAD_ID_FOR_UPDATE = 0
    _NEW_MOBILE_FOR_UPDATE = ""


# --- Function for Updating a Single Lead (Existing Logic - Refined) ---
def update_single_lead_mobile(target_lead_id: int, new_mobile: str):
    """
    Updates the mobile number for a specific lead, including mandatory field workaround.
    """
    if not target_lead_id or target_lead_id == 0 or not new_mobile:
        print("❌ Update skipped: Invalid Lead ID (must be > 0) or Mobile Number provided.")
        logger.warning(f"Update skipped for Lead ID '{target_lead_id}' due to invalid ID or missing mobile number.")
        return

    print(f"\n--- Starting Update Process for Lead ID: {target_lead_id} ---")
    logger.info(f"Attempting update for Lead ID: {target_lead_id}")
    ops = RecordOperations(MODULE)

    try:
        # ---- 1 · Fetch potentially required fields for update ----
        print(f"Fetching required fields ({', '.join(_UPDATE_REQ_FIELDS)}) for update workaround...")
        fetch_params = ParameterMap()
        # Use GetRecordParam here for fetching specific fields of a single record
        fetch_params.add(GetRecordParam.fields, ",".join(_UPDATE_REQ_FIELDS))

        # Using HeaderMap() is generally optional unless specific headers are needed
        resp = ops.get_record(target_lead_id, fetch_params, HeaderMap())

        # More robust check for get_record response
        rec = None # Initialize rec
        if resp is not None and resp.get_status_code() == 200:
            response_object = resp.get_object()
            # Check if the response object is the expected type (e.g., BodyWrapper for get_record)
            # Note: The exact response object type for get_record might vary, adjust if needed.
            # Assuming it contains get_data() returning a list of records.
            if hasattr(response_object, 'get_data') and response_object.get_data():
                rec_list = response_object.get_data()
                if rec_list:
                    rec = rec_list[0] # Get the first record
                    print("Required fields fetched successfully for update.")
                    logger.info(f"Required fields fetched for Lead ID: {target_lead_id}")
                else:
                    print("❌ Error fetching record: No data found in response list.")
                    logger.error(f"Fetch for update failed for {target_lead_id}: No data in response list.")
                    return
            else:
                print(f"❌ Error fetching record: Unexpected response object structure or no data. Type: {type(response_object)}")
                logger.error(f"Fetch for update failed for {target_lead_id}: Unexpected response structure or no data. Type: {type(response_object)}")
                return
        else:
            status_code = resp.get_status_code() if resp else 'N/A'
            print(f"❌ Error fetching record for update: Status {status_code}")
            logger.error(f"Fetch for update failed for {target_lead_id}: Status {status_code}")
            # Log the response object if available for more details
            if resp and resp.get_object():
                logger.error(f"Fetch error object: {resp.get_object()}")
            return # Stop if fetch failed

        # ---- 2 · Build update payload ----
        print("Building update payload...")
        patch = Record()
        # Add back fetched required fields - Ensure they exist on the fetched record 'rec'
        for f in _UPDATE_REQ_FIELDS:
            fetched_value = rec.get_key_value(f)
            if fetched_value is not None: # Only add if value was successfully fetched
                 patch.add_key_value(f, fetched_value)
            else:
                 # Handle case where a required field wasn't fetched (might indicate field API name issue)
                 print(f"⚠️ Warning: Required field '{f}' not found on fetched record. Update might fail.")
                 logger.warning(f"Required field '{f}' not found on fetched record {target_lead_id}.")
                 # Depending on strictness, you might want to return here or proceed cautiously.

        # Add the field to be updated
        patch.add_key_value("Mobile", new_mobile)
        print(f" Payload built with Mobile: {new_mobile}")

        body = BodyWrapper(); body.set_data([patch]); body.set_trigger(["workflow", "blueprint"])
        print(f" BodyWrapper prepared with trigger: {body.get_trigger()}")

        # ---- 3 · Push the update ----
        print(f"Calling update_record for Lead ID {target_lead_id}...")
        update_response = ops.update_record(target_lead_id, body, HeaderMap())

        if update_response is None:
             print("⚠️ Update call failed: No response received from API.")
             logger.error(f"Update call for Lead ID {target_lead_id} returned None.")
             return

        action_handler = update_response.get_object()
        print("Handling update response...")

        if action_handler:
            if isinstance(action_handler, ActionWrapper) and action_handler.get_data():
                results = action_handler.get_data()
                if results: # Check if results list is not empty
                    res = results[0] # Process the first result
                    status_obj = res.get_status()
                    code_obj = res.get_code()
                    message_obj = res.get_message()

                    status = status_obj.get_value() if status_obj else 'N/A'
                    code = code_obj.get_value() if code_obj else 'N/A'
                    msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)

                    if isinstance(res, SuccessResponse):
                        print(f"✅ Successfully updated Lead {target_lead_id}. Status: {status}, Code: {code}, Message: {msg_val}")
                        logger.info(f"Successfully updated Lead {target_lead_id}. Status: {status}, Code: {code}, Message: {msg_val}")
                    elif isinstance(res, APIException):
                        details = res.get_details()
                        details_str = str(details) if details else 'None'
                        print(f"❌ API Exception during update for Lead {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}")
                        print(f"   Details: {details_str}")
                        logger.error(f"API Exception updating Lead {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}")
                    else:
                        print(f"⚠️ Unexpected action result type in ActionWrapper data: {type(res)}")
                        logger.warning(f"Unexpected action result type for update {target_lead_id}: {type(res)}")
                else:
                    print("⚠️ Update response ActionWrapper contained no data/results.")
                    logger.warning(f"Update response ActionWrapper for {target_lead_id} had no data.")

            elif isinstance(action_handler, APIException):
                status_obj = action_handler.get_status()
                code_obj = action_handler.get_code()
                message_obj = action_handler.get_message()
                details = action_handler.get_details()

                status = status_obj.get_value() if status_obj else 'N/A'
                code = code_obj.get_value() if code_obj else 'N/A'
                msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
                details_str = str(details) if details else 'None'

                print(f"❌ Top-level API Exception during update: Code: {code}, Status: {status}, Message: {msg_val}")
                print(f"   Details: {details_str}")
                logger.error(f"Top-level API Exception updating Lead {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}")
            else:
                print(f"⚠️ Unexpected response object type: {type(action_handler)}")
                logger.warning(f"Unexpected response object type for update {target_lead_id}: {type(action_handler)}")
        else:
            # This case might occur if the status code was not 200/202 etc. but no exception was thrown by SDK
            status_code = update_response.get_status_code() if update_response else 'N/A'
            print(f"⚠️ Update might have failed. Status Code: {status_code}. No standard ActionWrapper or APIException object received.")
            logger.warning(f"Update for {target_lead_id} resulted in status {status_code}, but no structured error object found.")

    except APIException as ex:
        # Catch potential APIExceptions raised directly by the SDK call itself
        status_obj = ex.get_status()
        code_obj = ex.get_code()
        message_obj = ex.get_message()
        details = ex.get_details()
        status = status_obj.get_value() if status_obj else 'N/A'
        code = code_obj.get_value() if code_obj else 'N/A'
        msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
        details_str = str(details) if details else 'None'
        print(f"✖ APIException occurred during update process: Code: {code}, Status: {status}, Message: {msg_val}")
        print(f"  Details: {details_str}")
        logger.error(f"APIException during update process for {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}", exc_info=False) # No need for full traceback if details captured
        # traceback.print_exc() # Optional: uncomment for full stack trace
    except Exception as e:
        print(f"✖ An unexpected error occurred during update: {e}")
        logger.error(f"Unexpected error during update process for {target_lead_id}", exc_info=True)
        traceback.print_exc()
    finally:
        print(f"--- Update Process Finished for Lead ID: {target_lead_id} ---")


# --- NEW FUNCTION: Fetch and Qualify Leads ---
def qualify_uncontacted_leads(target_status="Not Contacted"):
    """
    Fetches leads with the specified status and prints relevant details for qualification.
    Handles pagination and client-side filtering.
    
    Args:
        target_status (str): The lead status to filter for. Defaults to "Not Contacted".
        
    Returns:
        list: A list of qualifying leads with their details
    """
    print("\n" + "=" * 60)
    print(f"LEAD QUALIFICATION PROCESS - Target Status: '{target_status}'")
    print("=" * 60)
    logger.info(f"Starting qualification process for leads with status '{target_status}'")

    ops = RecordOperations(MODULE)
    all_qualifying_leads = []
    # Collect unique statuses found for reporting
    unique_statuses = set()
    page = 1
    more_records = True

    # Prepare parameters for get_records - Apply fields and per_page outside the loop
    param_instance = ParameterMap()
    param_instance.add(GetRecordsParam.fields, ",".join(_QUALIFY_FIELDS))
    param_instance.add(GetRecordsParam.per_page, 200) # Max records per page (adjust if needed, 200 is common max)

    print("Starting data retrieval...")
    
    while more_records:
        print(f"Fetching page {page}...")
        logger.info(f"Fetching page {page} of leads with fields: {', '.join(_QUALIFY_FIELDS)}")

        # Add/update the page parameter for the current iteration
        # It's safer to create a new map or update the existing one carefully
        # For simplicity here, let's update the existing one.
        # If the SDK reuses the map object internally in ways that cause issues,
        # creating a new map inside the loop might be necessary.
        param_instance.add(GetRecordsParam.page, page) # Overwrites previous page value if key exists

        try:
            # Execute the request
            response = ops.get_records(param_instance, HeaderMap()) # HeaderMap optional

            if response is not None:
                status_code = response.get_status_code()
                logger.info(f"API call status code for page {page}: {status_code}")

                if status_code == 204: # No Content -> means no records found (could be end of data)
                    print("No more records found (Status 204).")
                    logger.info("Received 204 No Content, stopping pagination.")
                    more_records = False
                    # break # Exit loop immediately

                elif status_code == 200: # OK -> records potentially found
                    response_object = response.get_object()

                    if isinstance(response_object, ResponseWrapper) or isinstance(response_object, BodyWrapper):
                        records = response_object.get_data() # List of Record objects
                        info = response_object.get_info()     # Info object for pagination details

                        if not records:
                            # It's possible to get 200 OK but have no records on the *current* page
                            # especially if it's the last page or if filters applied server-side resulted in none.
                            print("No records found on this page (Status 200, empty data).")
                            logger.info(f"No records returned on page {page}, though status was 200.")
                            # Check info object to decide if there *might* be more on subsequent pages
                            if info is None or info.get_more_records() is not True:
                                more_records = False # Stop if no records AND no indication of more
                                print("No more records indicated by API info.")
                                logger.info("No more records indicated by API info object on empty page.")
                            else:
                                # This case is unusual (empty page but more_records=True), log it.
                                print("Empty page, but API indicates more records. Proceeding to next page.")
                                logger.warning(f"Empty data on page {page}, but info.more_records=True. Proceeding.")
                                page += 1 # Increment page to fetch next
                                # `continue` might be slightly cleaner here to skip processing loop
                                continue

                        else: # Records found on this page
                            print(f"Processing {len(records)} records from page {page}...")
                            for record in records:
                                try:
                                    lead_id = record.get_id()
                                    # Get field values and handle Choice objects properly
                                    def extract_field_value(record, field_name):
                                        field_value = record.get_key_value(field_name)
                                        if field_value is None:
                                            return None
                                        # Handle Choice objects
                                        if hasattr(field_value, 'get_value'):
                                            return field_value.get_value()
                                        return field_value
                                    
                                    status = extract_field_value(record, "Lead_Status")
                                    notes = extract_field_value(record, "Additional_Relocation_Notes")
                                    first_name = extract_field_value(record, "First_Name")
                                    last_name = extract_field_value(record, "Last_Name")
                                    email = extract_field_value(record, "Email")

                                    # --- Client-side Filtering ---
                                    # Add to unique statuses set for reporting
                                    if status is not None:
                                        unique_statuses.add(status)
                                    
                                    # Log all statuses to help identify what values are actually in the CRM
                                    logger.info(f"Found lead ID {lead_id} with status: '{status}'")
                                    
                                    if status == target_status:
                                        qualifying_lead_data = {
                                            "id": lead_id,
                                            "first_name": first_name or "", # Handle None values
                                            "last_name": last_name or "", # Handle None values
                                            "email": email or "",       # Handle None values
                                            "status": status,
                                            "notes": notes or ""        # Handle None values
                                        }
                                        all_qualifying_leads.append(qualifying_lead_data)
                                        logger.debug(f"Qualifying lead found and added: ID {lead_id}")
                                    else:
                                        # Optional: log leads fetched but filtered out client-side
                                        logger.debug(f"Lead ID {lead_id} fetched but filtered out (Status: '{status}')")

                                except Exception as inner_ex:
                                    lead_id_str = str(getattr(record, 'id', 'UNKNOWN_ID'))
                                    print(f"Error processing individual record {lead_id_str}: {inner_ex}")
                                    logger.error(f"Error processing individual record {lead_id_str} on page {page}", exc_info=True)
                                    # Continue to next record

                            # Check for more records using the Info object AFTER processing the page
                            if info is not None and info.get_more_records() is True:
                                page += 1
                                more_records = True
                                print("More records indicated, fetching next page.")
                                logger.info("More records indicated by API, proceeding to next page.")
                            else:
                                print("No more records indicated by API after processing page.")
                                logger.info("No more records indicated by API info object.")
                                more_records = False

                    elif isinstance(response_object, APIException):
                        # Handle API Exception received as the main response object
                        status_obj = response_object.get_status()
                        code_obj = response_object.get_code()
                        message_obj = response_object.get_message()
                        details = response_object.get_details()
                        status = status_obj.get_value() if status_obj else 'N/A'
                        code = code_obj.get_value() if code_obj else 'N/A'
                        msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
                        details_str = str(details) if details else 'None'
                        print(f"❌ API Exception during get_records (Page {page}): Code: {code}, Status: {status}, Message: {msg_val}")
                        print(f"   Details: {details_str}")
                        logger.error(f"API Exception getting records page {page}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}")
                        more_records = False # Stop pagination on error
                        # break

                    else:
                        # Handle unexpected response object type
                        print(f"⚠️ Unexpected response object type for get_records (Status 200): {type(response_object)}")
                        logger.warning(f"Unexpected response object type for get_records page {page} (Status 200): {type(response_object)}")
                        more_records = False
                        # break
                else:
                    # Handle other non-200, non-204 status codes
                    print(f"❌ Unexpected HTTP status code {status_code} received.")
                    logger.error(f"Unexpected HTTP status {status_code} received for get_records page {page}.")
                    # Try to log the response body if possible (might be APIException or other format)
                    try:
                       error_content = response.get_object()
                       if isinstance(error_content, APIException):
                           status = error_content.get_status().get_value() if error_content.get_status() else 'N/A'
                           code = error_content.get_code().get_value() if error_content.get_code() else 'N/A'
                           msg = error_content.get_message()
                           msg_val = msg.get_value() if hasattr(msg, 'get_value') else str(msg)
                           details = error_content.get_details()
                           print(f"   API Error Details: Code: {code}, Status: {status}, Message: {msg_val}")
                           print(f"   Details: {details}") if details else None
                           logger.error(f"API Exception on page {page}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details}")
                       else:
                           logger.error(f"Error response object for status {status_code}: {error_content}")
                    except Exception as e:
                       logger.error(f"Could not parse error response object for status {status_code}: {str(e)}")
                    
                    # For 400 errors on page > 1, it might be that we've reached the end of available data
                    # despite the API previously indicating more_records=True
                    if status_code == 400 and page > 1:
                        print("Received 400 error on page > 1, likely reached end of available data.")
                        logger.info("400 error on page > 1 interpreted as end of data.")
                    
                    more_records = False

            else: # response is None
                print("❌ API call failed: No response received.")
                logger.error(f"API call failed for get_records page {page}: No response received.")
                more_records = False
                # break

        except APIException as ex:
            # Catch APIExceptions raised directly by the SDK call (e.g., network issues before response)
            status_obj = ex.get_status(); code_obj = ex.get_code(); message_obj = ex.get_message(); details = ex.get_details()
            status = status_obj.get_value() if status_obj else 'N/A'; code = code_obj.get_value() if code_obj else 'N/A'
            msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
            details_str = str(details) if details else 'None'
            print(f"✖ Outer APIException occurred during get_records pagination: Code: {code}, Status: {status}, Message: {msg_val}")
            print(f"  Details: {details_str}")
            logger.error(f"Outer APIException during get_records page {page}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}", exc_info=False)
            # traceback.print_exc() # Optional: uncomment for full stack trace
            more_records = False # Stop on exception
            # break
        except Exception as e:
            print(f"✖ An unexpected error occurred during get_records pagination: {e}")
            logger.error(f"Unexpected error during get_records page {page}", exc_info=True)
            traceback.print_exc()
            more_records = False # Stop on exception
            # break

    # --- Process and Display Results ---
    print("\n" + "=" * 60)
    print(f"RESULTS: Found {len(all_qualifying_leads)} Leads with Status '{target_status}'")
    print("=" * 60)
    logger.info(f"Total qualifying leads found: {len(all_qualifying_leads)}")
    
    if not all_qualifying_leads:
        print("No leads require qualification based on the criteria.")
        print("\nPossible reasons:")
        print("1. There are no leads with exactly 'Not Contacted' status in your CRM")
        print("2. The status might have different capitalization or spacing (e.g., 'Not contacted' or 'NotContacted')")
        print("3. The API name for the field or value might be different from what's displayed in the UI")
        
        # Report the unique statuses found
        print("\nStatus values found in your CRM:")
        status_list = sorted(unique_statuses)
        if status_list:
            for status in status_list:
                print(f"  - '{status}'")
            print("\nConsider updating the 'target_status' variable in the code to match one of these values.")
        else:
            print("  No status values were successfully extracted from the records.")
            print("  This might indicate an issue with the API field names or response format.")
    else:
        print("\nLeads for Qualification:")
        print("-" * 80)
        for lead in all_qualifying_leads:
            # Use .get() for safety, although we handled None during creation
            print(f"  Lead ID: {lead.get('id', 'N/A')}")
            print(f"  Name:    {lead.get('first_name', '')} {lead.get('last_name', '')}")
            print(f"  Email:   {lead.get('email', 'N/A')}")
            notes = lead.get('notes', 'N/A')
            print(f"  Notes:   {notes if notes else 'N/A'}") # Ensure empty strings also show as N/A
            print("-" * 80)
            logger.debug(f"Displayed qualification info for Lead ID: {lead.get('id', 'N/A')}")

    print("--- Qualification Process Finished ---")
    logger.info("Qualification process finished.")


# --- Main Execution Block ---
def main():
    """Main function to run the lead qualification or update functionality"""
    # Ensure SDK is initialized (check happens implicitly via import,
    # but an explicit check adds robustness if initialize.py might fail silently)
    if initialize.Initializer.get_initializer():
        print("SDK Initialized. Ready to proceed.")
        logger.info("SDK Check: Initializer is available.")

        # Check if the token_store.txt file exists in the expected location
        token_path = os.path.join(PROJECT_ROOT, "zoho_data", "tokens", "token_store.txt")
        if not os.path.exists(token_path):
            logger.warning(f"Token file not found at expected path: {token_path}")
            # It might be in the location specified in initialize.py instead
        
        # --- Choose which function to run ---
        import sys
        
        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1].lower() == "update":
                # Run the update function
                print("\nRunning Lead Update...")
                if _TARGET_LEAD_ID_FOR_UPDATE and _TARGET_LEAD_ID_FOR_UPDATE != 0 and _NEW_MOBILE_FOR_UPDATE:
                    update_single_lead_mobile(_TARGET_LEAD_ID_FOR_UPDATE, _NEW_MOBILE_FOR_UPDATE)
                else:
                    print("Skipping update example: LEAD_ID (> 0) or NEW_MOBILE not set correctly in .env")
                    logger.warning("Update example skipped due to missing/invalid .env variables.")
                print("\nLead Update finished.")
            else:
                # Use the first argument as the target status
                target_status = sys.argv[1]
                print(f"\nRunning Lead Qualification with custom status: '{target_status}'...")
                qualify_uncontacted_leads(target_status)
                print("\nLead Qualification finished.")
        else:
            # Default: Run the qualification function with default status
            print("\nRunning Lead Qualification with default status...")
            qualify_uncontacted_leads()
            print("\nLead Qualification finished.")

    else:
        print("CRITICAL ERROR: SDK not initialized. Cannot proceed.")
        print("Please check configuration in .env and logs in logs/sdk.log")
        logger.critical("Script aborted: SDK Initializer is not available.")


if __name__ == "__main__":
    main()
