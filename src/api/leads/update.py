# src/api/leads/update.py

import traceback
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, BodyWrapper, Record, APIException, SuccessResponse, # APIException imported
    ActionWrapper, GetRecordParam, Field, ResponseWrapper
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

# Import logger from the corrected location
from src.core.initialize import logger
# Import constants needed
from .common import MODULE, UPDATE_REQ_FIELDS


def update_single_lead_mobile(target_lead_id: int, new_mobile: str) -> bool:
    """Updates the Mobile field for a single lead ID.

    Includes a workaround for potential mandatory field requirements during updates
    by fetching essential fields first and including them in the update payload.

    Args:
        target_lead_id: The Zoho CRM ID of the lead to update.
        new_mobile: The new mobile number string.

    Returns:
        True if the update was successful, False otherwise.
    """
    if not isinstance(target_lead_id, int) or target_lead_id <= 0:
        logger.error(f"Invalid target_lead_id provided for update: {target_lead_id}")
        print(f"❌ Error: Invalid Lead ID '{target_lead_id}'. Must be a positive integer.")
        return False
    if not isinstance(new_mobile, str) or not new_mobile:
        logger.error(f"Invalid new_mobile provided for update: {new_mobile}")
        print(f"❌ Error: Invalid Mobile Number '{new_mobile}'. Must be a non-empty string.")
        return False

    print(f"\n--- Starting Update Process for Lead ID: {target_lead_id} ---")
    logger.info(f"Attempting update for Lead ID: {target_lead_id} with new mobile.")
    ops = RecordOperations(MODULE) # Pass module name
    fetched_record_data = None # Define scope outside try block

    # ---- 1 · Fetch potentially required fields ----
    try:
        print(f"Fetching required fields ({', '.join(UPDATE_REQ_FIELDS)}) for update workaround...")
        fetch_params = ParameterMap()
        fetch_params.add(GetRecordParam.fields, ",".join(UPDATE_REQ_FIELDS))
        header_instance = HeaderMap()
        resp = ops.get_record(target_lead_id, fetch_params, header_instance)

        if resp is not None:
            status_code = resp.get_status_code()
            logger.debug(f"Fetch record (for update) response status code: {status_code}")
            if status_code == 200:
                response_object = resp.get_object()
                if isinstance(response_object, ResponseWrapper):
                    record_list = response_object.get_data()
                    if record_list and len(record_list) > 0:
                        fetched_record_data = record_list[0]
                        print("✅ Successfully fetched required fields.")
                        logger.info(f"Successfully fetched required fields for {target_lead_id}")
                    else:
                         print("❌ Fetch successful (200), but no data returned for the lead.")
                         logger.error(f"Fetch for update workaround succeeded (200) but returned no data for Lead ID {target_lead_id}.")
                         return False # Fail early
                else:
                     print(f"❌ Unexpected response type after fetch (expected ResponseWrapper): {type(response_object)}")
                     logger.error(f"Fetch for update workaround failed for {target_lead_id}: Unexpected response object type {type(response_object)}")
                     return False # Fail early
            elif status_code == 204:
                print(f"❌ Lead with ID {target_lead_id} not found (status code 204). Cannot update.")
                logger.error(f"Fetch for update workaround failed: Lead ID {target_lead_id} not found (204)." )
                return False # Fail early
            else: # Handle other error status codes
                error_message = f"Fetch failed with status code: {status_code}."
                try:
                    if isinstance(resp.get_object(), APIException):
                        ex = resp.get_object()
                        status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
                        code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
                        message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
                        details_val = ex.get_details()
                        error_message = f"API Error during fetch: {status_val} - {code_val} - {message_val}"
                        logger.error(f"Fetch for update workaround failed for {target_lead_id} (APIException): Status={status_val}, Code={code_val}, Msg={message_val}, Details={details_val}")
                    else:
                        logger.error(f"Fetch for update workaround failed for {target_lead_id}: Unknown error, status code {status_code}, Response Obj: {resp.get_object()}")
                except Exception as log_ex:
                     logger.error(f"Additionally, error parsing error response object: {log_ex}")
                print(f"❌ {error_message} Cannot fetch required fields.")
                return False # Fail early
        else:
            print("❌ No response received from the server during fetch.")
            logger.error(f"Fetch for update workaround failed for {target_lead_id}: No response received.")
            return False # Fail early

    # --- Specific APIException Catch for Fetch ---
    except APIException as ex:
        status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
        code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
        message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
        details_val = ex.get_details()
        print(f"❌ A Zoho APIException occurred during fetch: Status={status_val}, Code={code_val}, Message={message_val}")
        logger.error(f"Fetch process failed for {target_lead_id} (SDK APIException): Status={status_val}, Code={code_val}, Msg={message_val}, Details={details_val}", exc_info=True)
        return False
    # --- General Exception Catch for Fetch ---
    except Exception as e:
        print(f"❌ An unexpected error occurred during fetch: {e}")
        logger.error(f"Fetch process failed for {target_lead_id} with an unexpected error", exc_info=True)
        return False

    # --- Proceed only if fetch was successful ---
    if fetched_record_data is None:
         print("❌ Could not retrieve existing record data (fetch might have failed silently or record was empty). Cannot proceed.")
         return False

    # ---- 2 · Build update payload ----
    try:
        print("Building update payload...")
        patch = Record()
        successful_adds = 0
        for field_api_name in UPDATE_REQ_FIELDS:
            # Use try-except inside the loop for robustness if one field fails
             try:
                field_value = fetched_record_data.get_key_value(field_api_name)
                if field_value is not None:
                    if field_api_name == "Last_Name":
                        patch.add_field_value(Field.Leads.last_name(), field_value)
                    elif field_api_name == "Company":
                         patch.add_field_value(Field.Leads.company(), field_value)
                    elif field_api_name == "Lead_Status":
                         patch.add_field_value(Field.Leads.lead_status(), field_value)
                    else:
                         logger.warning(f"Required field '{field_api_name}' defined in UPDATE_REQ_FIELDS, but no specific Field.Leads mapping found in update.py. Skipping.")
                         continue
                    logger.debug(f"Added required field '{field_api_name}' back to update patch for {target_lead_id}")
                    successful_adds += 1
                else:
                    logger.debug(f"Required field '{field_api_name}' was None in fetched data for {target_lead_id}. Not adding to patch.")
             except Exception as field_e:
                  print(f"⚠️ Error processing required field '{field_api_name}' for payload: {field_e}")
                  logger.error(f"Error adding required field '{field_api_name}' to payload for {target_lead_id}", exc_info=True)
                  # Decide whether to continue or fail if a required field cannot be added

        patch.add_field_value(Field.Leads.mobile(), new_mobile)
        print(f"  Payload built. Added Mobile: {new_mobile} and {successful_adds}/{len(UPDATE_REQ_FIELDS)} required fields.")
        logger.debug(f"Update payload built for {target_lead_id} including new mobile and {successful_adds} required fields.")

        body = BodyWrapper()
        body.set_data([patch])
        body.set_trigger(["workflow", "blueprint"])
        print(f"  BodyWrapper prepared with trigger: {body.get_trigger()}")

    except AttributeError as attr_err:
         print(f"❌ Error: Issue finding field definition in SDK: {attr_err}")
         logger.critical(f"SDK Field definition error during payload build for {target_lead_id}: {attr_err}", exc_info=True)
         return False
    except Exception as build_e:
        print(f"❌ An unexpected error occurred during payload building: {build_e}")
        logger.error(f"Payload build process failed for {target_lead_id}", exc_info=True)
        return False

    # ---- 3 · Push the update ----
    try:
        print("Sending update request to Zoho...")
        header_instance = HeaderMap() # Re-declare or use the one from fetch
        update_response = ops.update_record(target_lead_id, body, header_instance)

        # Process Response
        if update_response is not None:
            status_code = update_response.get_status_code()
            logger.debug(f"Update record response status code: {status_code}")
            response_object = update_response.get_object()

            if isinstance(response_object, ActionWrapper):
                action_response_list = response_object.get_data()
                if not action_response_list:
                    print("❌ Update action response list is empty. Update likely failed.")
                    logger.error(f"Update for {target_lead_id} resulted in an empty action response list.")
                    return False
                action_response = action_response_list[0]
                if isinstance(action_response, SuccessResponse):
                    status = action_response.get_status().get_value()
                    code = action_response.get_code().get_value()
                    message = action_response.get_message().get_value()
                    details = action_response.get_details()
                    print(f"✅ Lead {target_lead_id} Mobile Updated Successfully! Status: {status}, Code: {code}, Message: {message}")
                    logger.info(f"Update successful for Lead ID {target_lead_id}. Status={status}, Code={code}, Msg={message}, Details={details}")
                    return True
                elif isinstance(action_response, APIException):
                    ex = action_response
                    status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
                    code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
                    message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
                    details_val = ex.get_details()
                    print(f"❌ API Error during update action: {status_val} - {code_val} - {message_val}")
                    logger.error(f"Update failed for Lead ID {target_lead_id} (APIException in ActionWrapper): Status={status_val}, Code={code_val}, Msg={message_val}, Details={details_val}")
                    return False
                else:
                     print(f"❌ Unexpected action response type within ActionWrapper: {type(action_response)}")
                     logger.error(f"Update failed for {target_lead_id}: Unexpected action response type {type(action_response)} inside ActionWrapper.")
                     return False
            elif isinstance(response_object, APIException):
                ex = response_object
                status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
                code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
                message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
                details_val = ex.get_details()
                print(f"❌ API Error response for update operation: {status_val} - {code_val} - {message_val}")
                logger.error(f"Update operation failed for {target_lead_id} (Top-level APIException): Status={status_val}, Code={code_val}, Msg={message_val}, Details={details_val}")
                return False
            else:
                print(f"❌ Unexpected response object type after update: {type(response_object)}")
                logger.error(f"Update failed for {target_lead_id}: Unexpected response object type {type(response_object)}")
                return False
        else:
            print("❌ No response received from the server during update.")
            logger.error(f"Update failed for {target_lead_id}: No response received from server.")
            return False

    # --- Specific APIException Catch for Update ---
    except APIException as ex:
         status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
         code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
         message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
         details_val = ex.get_details()
         print(f"❌ A Zoho APIException occurred during update: Status={status_val}, Code={code_val}, Message={message_val}")
         logger.error(f"Update process failed for {target_lead_id} (SDK APIException): Status={status_val}, Code={code_val}, Msg={message_val}, Details={details_val}", exc_info=True)
         return False
    # --- General Exception Catch for Update ---
    except Exception as e:
         print(f"❌ An unexpected error occurred during update: {e}")
         logger.error(f"Update process failed for {target_lead_id} with an unexpected error", exc_info=True)
         return False
    finally:
        print(f"--- Update Process Finished for Lead ID: {target_lead_id} ---")

    # Fallback return - should not be reached
    logger.warning(f"Update function for {target_lead_id} reached end without explicit True/False return.")
    return False

# --- End of src/api/leads/update.py ---