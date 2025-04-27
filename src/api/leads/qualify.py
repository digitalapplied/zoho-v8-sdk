# src/api/leads/qualify.py

import os
import traceback
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, APIException, GetRecordsParam, ResponseWrapper, BodyWrapper
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

from .common import (
    MODULE, QUALIFY_FIELDS, logger, extract_field_value
)


def qualify_uncontacted_leads(target_status="Not Contacted"):
    """
    Fetches the most recent 200 leads with the specified status and prints relevant details for qualification.
    Results are also written to a txt file.

    Args:
        target_status (str): The lead status to filter for. Defaults to "Not Contacted".

    Returns:
        list: A list of qualifying leads with their details (dictionaries).
    """
    print("\n" + "=" * 60)
    print(f"LEAD QUALIFICATION PROCESS - Target Status: '{target_status}'")
    print("=" * 60)
    logger.info(f"Starting qualification process for leads with status '{target_status}'")

    ops = RecordOperations(MODULE)
    all_qualifying_leads = []
    unique_statuses = set()  # To report what statuses were actually found
    page = 1 # We only fetch page 1

    print("Starting data retrieval...")
    print(f"Fetching page {page}...")
    logger.info(f"Fetching page {page} of leads with fields: {', '.join(QUALIFY_FIELDS)}")

    # Build ParameterMap for the single page request
    param_instance = ParameterMap()
    param_instance.add(GetRecordsParam.fields, ",".join(QUALIFY_FIELDS))
    param_instance.add(GetRecordsParam.per_page, 200) # Max records per page
    param_instance.add(GetRecordsParam.page, page)
    # Add sorting parameters for most recent first
    param_instance.add(GetRecordsParam.sort_by, "Created_Time")
    param_instance.add(GetRecordsParam.sort_order, "desc")

    try:
        # Execute the request
        response = ops.get_records(param_instance, HeaderMap()) # HeaderMap is optional

        if response is not None:
            status_code = response.get_status_code()
            logger.info(f"API call status code for page {page}: {status_code}")

            if status_code == 204: # No Content
                print("No records found (Status 204).")
                logger.info("Received 204 No Content.")

            elif status_code == 200: # OK
                response_object = response.get_object()

                if isinstance(response_object, ResponseWrapper) or isinstance(response_object, BodyWrapper):
                    records = response_object.get_data() # List of Record objects

                    if not records:
                        # It's possible to get 200 OK but have no records on the page
                        print("No records found on this page (Status 200, empty data).")
                        logger.info(f"No records returned on page {page}, though status was 200.")
                    else:
                        print(f"Processing {len(records)} records from page {page}...")
                        for index, record in enumerate(records):
                            try:
                                lead_id = record.get_id()
                                status = extract_field_value(record, "Lead_Status")
                                notes = extract_field_value(record, "Additional_Relocation_Notes")
                                first_name = extract_field_value(record, "First_Name")
                                last_name = extract_field_value(record, "Last_Name")
                                email = extract_field_value(record, "Email")

                                # Log first 10 records' raw data before filtering
                                if index < 10: 
                                    logger.debug(f"Record {index+1}/{len(records)} PRE-FILTER - ID: {lead_id}, Status: '{status}', Notes: '{notes}'")

                                # Collect all statuses found for reporting/debugging
                                if status is not None:
                                    unique_statuses.add(status)
                                logger.info(f"Found lead ID {lead_id} with status: '{status}'")

                                # Client-side Filtering based on target_status (case-insensitive)
                                if status and status.lower() == target_status.lower() and notes and notes.strip():
                                    qualifying_lead_data = {
                                        "id": lead_id,
                                        "first_name": first_name or "", # Handle None values
                                        "last_name": last_name or "",   # Handle None values
                                        "email": email or "",           # Handle None values
                                        "status": status,
                                        "notes": notes.strip()          # Store stripped notes
                                    }
                                    all_qualifying_leads.append(qualifying_lead_data)
                                    logger.debug(f"Qualifying lead found and added: ID {lead_id}")
                                else:
                                    logger.debug(f"Lead ID {lead_id} fetched but filtered out (Status: '{status}', Notes: '{notes}')")

                            except Exception as inner_ex:
                                lead_id_str = str(getattr(record, 'id', 'UNKNOWN_ID'))
                                print(f"Error processing individual record {lead_id_str}: {inner_ex}")
                                logger.error(f"Error processing individual record {lead_id_str} on page {page}", exc_info=True)
                                # Continue to the next record even if one fails

                elif isinstance(response_object, APIException):
                    # Handle API Exception received as the main response object
                    status_obj = response_object.get_status()
                    code_obj = response_object.get_code()
                    message_obj = response_object.get_message()
                    details = response_object.get_details()
                    status_val = status_obj.get_value() if status_obj else 'N/A'
                    code_val = code_obj.get_value() if code_obj else 'N/A'
                    msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
                    details_str = str(details) if details else 'None'
                    print(f"❌ API Exception during get_records (Page {page}): Code: {code_val}, Status: {status_val}, Message: {msg_val}")
                    print(f"   Details: {details_str}")
                    logger.error(f"API Exception getting records page {page}: Code: {code_val}, Status: {status_val}, Message: {msg_val}, Details: {details_str}")

                else:
                    # Handle unexpected response object type
                    print(f"⚠️ Unexpected response object type for get_records (Status 200): {type(response_object)}")
                    logger.warning(f"Unexpected response object type for get_records page {page} (Status 200): {type(response_object)}")

            else: # Handle other non-200, non-204 status codes
                print(f"❌ Unexpected HTTP status code {status_code} received.")
                logger.error(f"Unexpected HTTP status {status_code} received for get_records page {page}.")
                # Attempt to log the error response body if it's an APIException
                try:
                   error_content = response.get_object()
                   if isinstance(error_content, APIException):
                       status_obj = error_content.get_status()
                       code_obj = error_content.get_code()
                       message_obj = error_content.get_message()
                       details = error_content.get_details()
                       status_val = status_obj.get_value() if status_obj else 'N/A'
                       code_val = code_obj.get_value() if code_obj else 'N/A'
                       msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
                       details_str = str(details) if details else 'None'
                       print(f"   API Error Details: Code: {code_val}, Status: {status_val}, Message: {msg_val}")
                       print(f"   Details: {details_str}") if details else None
                       logger.error(f"API Exception on page {page}: Code: {code_val}, Status: {status_val}, Message: {msg_val}, Details: {details_str}")
                   else:
                       logger.error(f"Error response object for status {status_code}: {error_content}")
                except Exception as e:
                   logger.error(f"Could not parse error response object for status {status_code}: {str(e)}")

        else: # response is None
            print("❌ API call failed: No response received.")
            logger.error(f"API call failed for get_records page {page}: No response received.")

    except APIException as ex:
        # Catch APIExceptions raised directly by the SDK call (e.g., network issues)
        status_obj = ex.get_status()
        code_obj = ex.get_code()
        message_obj = ex.get_message()
        details = ex.get_details()
        status_val = status_obj.get_value() if status_obj else 'N/A'
        code_val = code_obj.get_value() if code_obj else 'N/A'
        msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
        details_str = str(details) if details else 'None'
        print(f"✖ Outer APIException occurred during get_records: Code: {code_val}, Status: {status_val}, Message: {msg_val}")
        print(f"  Details: {details_str}")
        logger.error(f"Outer APIException during get_records page {page}: Code: {code_val}, Status: {status_val}, Message: {msg_val}, Details: {details_str}", exc_info=False)
    except Exception as e:
        print(f"✖ An unexpected error occurred during get_records: {e}")
        logger.error(f"Unexpected error during get_records page {page}", exc_info=True)
        traceback.print_exc()

    # --- Process and Display Results ---
    print("\n" + "=" * 60)
    print(f"RESULTS: Found {len(all_qualifying_leads)} Leads with Status '{target_status}'")
    print("=" * 60)
    logger.info(f"Total qualifying leads found: {len(all_qualifying_leads)}")

    if not all_qualifying_leads:
        print("No leads require qualification based on the criteria.")
        print("\nPossible reasons:")
        print("1. There are no leads with exactly 'Not Contacted' status in the most recent 200 records.")
        print("2. The status might have different capitalization or spacing (e.g., 'Not contacted' or 'NotContacted')")
        print("3. The API name for the field or value might be different from what's displayed in the UI")

        # Report the unique statuses found in the fetched records
        print("\nStatus values found in the fetched records:")
        status_list = sorted(list(unique_statuses))
        if status_list:
            for status in status_list:
                print(f"  - '{status}'")
            print("\nConsider updating the 'target_status' variable if needed.")
        else:
            print("  No status values were successfully extracted from the fetched records.")
            print("  This might indicate an issue with the API field names or response format.")
    else:
        print("\nLeads for Qualification:")
        print("-" * 80)
        for lead in all_qualifying_leads:
            # Use .get() for safety when accessing dictionary keys
            print(f"  Lead ID: {lead.get('id', 'N/A')}")
            print(f"  Name:    {lead.get('first_name', '')} {lead.get('last_name', '')}")
            print(f"  Email:   {lead.get('email', 'N/A')}")
            notes = lead.get('notes', 'N/A')
            print(f"  Notes:   {notes if notes else 'N/A'}") # Ensure empty strings also show as N/A
            print("-" * 80)
            logger.debug(f"Displayed qualification info for Lead ID: {lead.get('id', 'N/A')}")

    print("--- Qualification Process Finished ---")
    logger.info("Qualification process finished.")

    # --- Output to TXT file ---
    try:
        # Construct the output path relative to the project root (assuming src is in the root)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_path = os.path.join(project_root, "lead_qualification_results.txt")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"RESULTS: Found {len(all_qualifying_leads)} Leads with Status '{target_status}'\n")
            f.write("=" * 60 + "\n\n")
            if all_qualifying_leads:
                for lead in all_qualifying_leads:
                    f.write(f"Lead ID: {lead.get('id', 'N/A')}\n")
                    f.write(f"Name:    {lead.get('first_name', '')} {lead.get('last_name', '')}\n")
                    f.write(f"Email:   {lead.get('email', 'N/A')}\n")
                    f.write(f"Notes:   {lead.get('notes', 'N/A')}\n")
                    f.write("-" * 80 + "\n")
            else:
                 f.write("No leads found matching the criteria.\n")
        print(f"Results written to {output_path}")
        logger.info(f"Results successfully written to {output_path}")
    except Exception as e:
        print(f"Error writing results to txt file: {e}")
        logger.error(f"Error writing results to txt file: {e}", exc_info=True)

    return all_qualifying_leads


def qualify_leads_from_custom_view(custom_view_id="1649349000008182385", output_filename="lead_qualification_cv_results.txt"):
    """
    Fetches the first 200 leads from a specified Zoho CRM Custom View and prints relevant details.
    Results are also written to a txt file.

    Args:
        custom_view_id (str): The ID of the Custom View to fetch records from.
        output_filename (str): The name for the output text file.
    """
    print("=" * 60)
    print(f"LEAD QUALIFICATION PROCESS - Custom View ID: {custom_view_id}")
    print("=" * 60)
    logger.info(f"Starting qualification process for leads from Custom View ID: {custom_view_id}")

    ops = RecordOperations(MODULE)
    qualified_leads_cv = []
    page = 1 # We only fetch page 1

    print("Starting data retrieval from Custom View...")
    print(f"Fetching page {page}...")
    logger.info(f"Fetching page {page} from CV {custom_view_id} with fields: {', '.join(QUALIFY_FIELDS)}")

    # Build ParameterMap for the Custom View request
    param_instance = ParameterMap()
    param_instance.add(GetRecordsParam.cvid, custom_view_id)
    param_instance.add(GetRecordsParam.fields, ",".join(QUALIFY_FIELDS))
    param_instance.add(GetRecordsParam.per_page, 200) # Max records per page
    param_instance.add(GetRecordsParam.page, page)
    # Remove sorting - Custom View likely handles sorting
    # param_instance.add(GetRecordsParam.sort_by, "Created_Time")
    # param_instance.add(GetRecordsParam.sort_order, "desc")

    try:
        # Execute the request
        response = ops.get_records(param_instance, HeaderMap()) # HeaderMap is optional

        if response is not None:
            status_code = response.get_status_code()
            logger.info(f"API call status code for CV {custom_view_id}, page {page}: {status_code}")

            if status_code == 204: # No Content
                print(f"No records found in Custom View {custom_view_id} (Status 204).")
                logger.info(f"Received 204 No Content for CV {custom_view_id}.")

            elif status_code == 200: # OK
                response_object = response.get_object()

                if isinstance(response_object, ResponseWrapper) or isinstance(response_object, BodyWrapper):
                    records = response_object.get_data() # List of Record objects

                    if not records:
                        print(f"No records found on this page for CV {custom_view_id} (Status 200, empty data).")
                        logger.info(f"No records returned on page {page} for CV {custom_view_id}, though status was 200.")
                    else:
                        print(f"Processing {len(records)} records from CV {custom_view_id}, page {page}...")
                        for index, record in enumerate(records):
                            try:
                                lead_id = record.get_id()
                                # Extract fields needed for output
                                first_name = extract_field_value(record, "First_Name")
                                last_name = extract_field_value(record, "Last_Name")
                                email = extract_field_value(record, "Email")
                                notes = extract_field_value(record, "Additional_Relocation_Notes")
                                status = extract_field_value(record, "Lead_Status") # Keep for logging/verification

                                # Log first 10 records' raw data before filtering (optional but good for verification)
                                if index < 10:
                                    logger.debug(f"CV Record {index+1}/{len(records)} - ID: {lead_id}, Status: '{status}', Notes: '{notes}'")

                                # Assuming the Custom View handles the filtering, 
                                # we just format the data for output.
                                full_name = ' '.join(filter(None, [first_name, last_name]))
                                qualified_leads_cv.append({
                                    'id': lead_id,
                                    'name': full_name or 'N/A',
                                    'email': email or 'N/A',
                                    'notes': notes.strip() if notes else 'N/A' # Store stripped notes or N/A
                                })
                                logger.debug(f"Added lead from CV: ID {lead_id}")

                            except Exception as inner_ex:
                                lead_id_str = str(getattr(record, 'id', 'UNKNOWN_ID'))
                                print(f"Error processing individual record {lead_id_str} from CV: {inner_ex}")
                                logger.error(f"Error processing individual record {lead_id_str} from CV {custom_view_id} on page {page}", exc_info=True)
                                # Continue to the next record even if one fails

                elif isinstance(response_object, APIException):
                    # Handle API Exception received as the main response object
                    status_obj = response_object.get_status()
                    code_obj = response_object.get_code()
                    message_obj = response_object.get_message()
                    details = response_object.get_details()
                    status_val = status_obj.get_value() if status_obj else 'N/A'
                    code_val = code_obj.get_value() if code_obj else 'N/A'
                    message_val = message_obj.get_value() if message_obj else 'N/A'
                    print(f"API Exception received for CV {custom_view_id}: Status: {status_val}, Code: {code_val}, Message: {message_val}")
                    if details:
                        print(f"Details: {details}")
                    logger.error(f"API Exception for CV {custom_view_id}: Status: {status_val}, Code: {code_val}, Message: {message_val}, Details: {details}")

                else:
                    # Handle unexpected response object type
                    print(f"Received unexpected response object type: {type(response_object)}")
                    logger.warning(f"Unexpected response type for CV {custom_view_id}: {type(response_object)}")

            else: # Handle other HTTP status codes (e.g., 401, 403, 429, 500)
                print(f"Error fetching records from CV {custom_view_id}: HTTP Status Code {status_code}")
                logger.error(f"HTTP Error for CV {custom_view_id}: {status_code}. Response: {response.get_string() if hasattr(response, 'get_string') else 'N/A'}")

    except APIException as api_ex:
        # Handle API Exception during the operation itself
        status_obj = api_ex.get_status()
        code_obj = api_ex.get_code()
        message_obj = api_ex.get_message()
        details = api_ex.get_details()
        status_val = status_obj.get_value() if status_obj else 'N/A'
        code_val = code_obj.get_value() if code_obj else 'N/A'
        message_val = message_obj.get_value() if message_obj else 'N/A'
        print(f"API Exception occurred during operation for CV {custom_view_id}: Status: {status_val}, Code: {code_val}, Message: {message_val}")
        if details:
            print(f"Details: {details}")
        logger.error(f"API Exception during operation for CV {custom_view_id}: Status: {status_val}, Code: {code_val}, Message: {message_val}, Details: {details}", exc_info=True)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.error(f"Unexpected error during qualification for CV {custom_view_id}: {e}", exc_info=True)

    # --- Display Results --- 
    print("\n" + "=" * 60)
    print(f"RESULTS: Found {len(qualified_leads_cv)} Leads from Custom View {custom_view_id}")
    print("=" * 60 + "\n")

    if not qualified_leads_cv:
        print("  No leads were found or processed successfully from the Custom View.")
    else:
        print("Qualified Leads from Custom View:")
        print("-" * 80)
        for lead in qualified_leads_cv:
            print(f"  Lead ID: {lead.get('id', 'N/A')}")
            print(f"  Name:    {lead.get('name', 'N/A')}")
            print(f"  Email:   {lead.get('email', 'N/A')}")
            notes = lead.get('notes', 'N/A')
            print(f"  Notes:   {notes}")
            print("-" * 80)
            logger.debug(f"Displayed info for Lead ID from CV: {lead.get('id', 'N/A')}")

    print("--- Custom View Qualification Process Finished ---")
    logger.info(f"Custom View qualification process finished for CV ID: {custom_view_id}.")

    # --- Output to TXT file --- 
    try:
        # Assuming the script is run from the project root (d:\zoho_v8),
        # construct the path relative to the current working directory.
        output_path = os.path.join("src", output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"RESULTS: Found {len(qualified_leads_cv)} Leads from Custom View ID {custom_view_id}\n")
            f.write("=" * 60 + "\n\n")
            if qualified_leads_cv:
                for lead in qualified_leads_cv:
                    f.write(f"Lead ID: {lead.get('id', 'N/A')}\n")
                    f.write(f"Name:    {lead.get('name', 'N/A')}\n")
                    f.write(f"Email:   {lead.get('email', 'N/A')}\n")
                    f.write(f"Notes:   {lead.get('notes', 'N/A')}\n")
                    f.write("-" * 80 + "\n")
            else:
                f.write("No leads found or processed from this Custom View.\n")
        
        print(f"Results written to {output_path}")
        logger.info(f"Results successfully written to {output_path}")

    except Exception as e:
        print(f"Error writing results to file {output_filename}: {e}")
        logger.error(f"Error writing results to file {output_path}: {e}", exc_info=True)
