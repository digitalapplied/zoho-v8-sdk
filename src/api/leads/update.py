# src/api/leads/update.py

import traceback
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, BodyWrapper, Record, APIException, SuccessResponse,
    ActionWrapper, GetRecordParam
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

from .common import (
    MODULE, UPDATE_REQ_FIELDS, logger
)


def update_single_lead_mobile(target_lead_id: int, new_mobile: str):
    """
    Updates the mobile number for a specific lead, including mandatory field workaround.
    
    Args:
        target_lead_id (int): The ID of the lead to update
        new_mobile (str): The new mobile number to set
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if not target_lead_id or target_lead_id == 0 or not new_mobile:
        print("❌ Update skipped: Invalid Lead ID (must be > 0) or Mobile Number provided.")
        logger.warning(f"Update skipped for Lead ID '{target_lead_id}' due to invalid ID or missing mobile number.")
        return False

    print(f"\n--- Starting Update Process for Lead ID: {target_lead_id} ---")
    logger.info(f"Attempting update for Lead ID: {target_lead_id}")
    ops = RecordOperations(MODULE)

    try:
        # ---- 1 · Fetch potentially required fields for update ----
        print(f"Fetching required fields ({', '.join(UPDATE_REQ_FIELDS)}) for update workaround...")
        fetch_params = ParameterMap()
        # Use GetRecordParam here for fetching specific fields of a single record
        fetch_params.add(GetRecordParam.fields, ",".join(UPDATE_REQ_FIELDS))

        # Using HeaderMap() is generally optional unless specific headers are needed
        resp = ops.get_record(target_lead_id, fetch_params, HeaderMap())

        # More robust check for get_record response
        rec = None  # Initialize rec
        if resp is not None and resp.get_status_code() == 200:
            response_object = resp.get_object()
            # Check if the response object is the expected type (e.g., BodyWrapper for get_record)
            # Note: The exact response object type for get_record might vary, adjust if needed.
            # Assuming it contains get_data() returning a list of records.
            if hasattr(response_object, 'get_data') and response_object.get_data():
                rec_list = response_object.get_data()
                if rec_list:
                    rec = rec_list[0]  # Get the first record
                    print("Required fields fetched successfully for update.")
                    logger.info(f"Required fields fetched for Lead ID: {target_lead_id}")
                else:
                    print("❌ Error fetching record: No data found in response list.")
                    logger.error(f"Fetch for update failed for {target_lead_id}: No data in response list.")
                    return False
            else:
                print(f"❌ Error fetching record: Unexpected response object structure or no data. Type: {type(response_object)}")
                logger.error(f"Fetch for update failed for {target_lead_id}: Unexpected response structure or no data. Type: {type(response_object)}")
                return False
        else:
            status_code = resp.get_status_code() if resp else 'N/A'
            print(f"❌ Error fetching record for update: Status {status_code}")
            logger.error(f"Fetch for update failed for {target_lead_id}: Status {status_code}")
            # Log the response object if available for more details
            if resp and resp.get_object():
                logger.error(f"Fetch error object: {resp.get_object()}")
            return False  # Stop if fetch failed

        # ---- 2 · Build update payload ----
        print("Building update payload...")
        patch = Record()
        # Add back fetched required fields - Ensure they exist on the fetched record 'rec'
        for f in UPDATE_REQ_FIELDS:
            fetched_value = rec.get_key_value(f)
            if fetched_value is not None:  # Only add if value was successfully fetched
                patch.add_key_value(f, fetched_value)
            else:
                # Handle case where a required field wasn't fetched (might indicate field API name issue)
                print(f"⚠️ Warning: Required field '{f}' not found on fetched record. Update might fail.")
                logger.warning(f"Required field '{f}' not found on fetched record {target_lead_id}.")
                # Depending on strictness, you might want to return here or proceed cautiously.

        # Add the field to be updated
        patch.add_key_value("Mobile", new_mobile)
        print(f" Payload built with Mobile: {new_mobile}")

        body = BodyWrapper()
        body.set_data([patch])
        body.set_trigger(["workflow", "blueprint"])
        print(f" BodyWrapper prepared with trigger: {body.get_trigger()}")

        # ---- 3 · Push the update ----
        print(f"Calling update_record for Lead ID {target_lead_id}...")
        update_response = ops.update_record(target_lead_id, body, HeaderMap())

        if update_response is None:
            print("⚠️ Update call failed: No response received from API.")
            logger.error(f"Update call for Lead ID {target_lead_id} returned None.")
            return False

        action_handler = update_response.get_object()
        print("Handling update response...")

        if action_handler:
            if isinstance(action_handler, ActionWrapper) and action_handler.get_data():
                results = action_handler.get_data()
                if results:  # Check if results list is not empty
                    res = results[0]  # Process the first result
                    status_obj = res.get_status()
                    code_obj = res.get_code()
                    message_obj = res.get_message()

                    status = status_obj.get_value() if status_obj else 'N/A'
                    code = code_obj.get_value() if code_obj else 'N/A'
                    msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)

                    if isinstance(res, SuccessResponse):
                        print(f"✅ Successfully updated Lead {target_lead_id}. Status: {status}, Code: {code}, Message: {msg_val}")
                        logger.info(f"Successfully updated Lead {target_lead_id}. Status: {status}, Code: {code}, Message: {msg_val}")
                        return True
                    elif isinstance(res, APIException):
                        details = res.get_details()
                        details_str = str(details) if details else 'None'
                        print(f"❌ API Exception during update for Lead {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}")
                        print(f"   Details: {details_str}")
                        logger.error(f"API Exception updating Lead {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}")
                        return False
                    else:
                        print(f"⚠️ Unexpected action result type in ActionWrapper data: {type(res)}")
                        logger.warning(f"Unexpected action result type for update {target_lead_id}: {type(res)}")
                        return False
                else:
                    print("⚠️ Update response ActionWrapper contained no data/results.")
                    logger.warning(f"Update response ActionWrapper for {target_lead_id} had no data.")
                    return False

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
                return False
            else:
                print(f"⚠️ Unexpected response object type: {type(action_handler)}")
                logger.warning(f"Unexpected response object type for update {target_lead_id}: {type(action_handler)}")
                return False
        else:
            # This case might occur if the status code was not 200/202 etc. but no exception was thrown by SDK
            status_code = update_response.get_status_code() if update_response else 'N/A'
            print(f"⚠️ Update might have failed. Status Code: {status_code}. No standard ActionWrapper or APIException object received.")
            logger.warning(f"Update for {target_lead_id} resulted in status {status_code}, but no structured error object found.")
            return False

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
        logger.error(f"APIException during update process for {target_lead_id}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}", exc_info=False)  # No need for full traceback if details captured
        return False
    except Exception as e:
        print(f"✖ An unexpected error occurred during update: {e}")
        logger.error(f"Unexpected error during update process for {target_lead_id}", exc_info=True)
        traceback.print_exc()
        return False
    finally:
        print(f"--- Update Process Finished for Lead ID: {target_lead_id} ---")
