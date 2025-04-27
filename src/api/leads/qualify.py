# src/api/leads/qualify.py

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
    param_instance.add(GetRecordsParam.fields, ",".join(QUALIFY_FIELDS))
    param_instance.add(GetRecordsParam.per_page, 200)  # Max records per page (adjust if needed, 200 is common max)

    print("Starting data retrieval...")
    
    while more_records:
        print(f"Fetching page {page}...")
        logger.info(f"Fetching page {page} of leads with fields: {', '.join(QUALIFY_FIELDS)}")

        # Add/update the page parameter for the current iteration
        param_instance.add(GetRecordsParam.page, page)  # Overwrites previous page value if key exists

        try:
            # Execute the request
            response = ops.get_records(param_instance, HeaderMap())  # HeaderMap optional

            if response is not None:
                status_code = response.get_status_code()
                logger.info(f"API call status code for page {page}: {status_code}")

                if status_code == 204:  # No Content -> means no records found (could be end of data)
                    print("No more records found (Status 204).")
                    logger.info("Received 204 No Content, stopping pagination.")
                    more_records = False

                elif status_code == 200:  # OK -> records potentially found
                    response_object = response.get_object()

                    if isinstance(response_object, ResponseWrapper) or isinstance(response_object, BodyWrapper):
                        records = response_object.get_data()  # List of Record objects
                        info = response_object.get_info()     # Info object for pagination details

                        if not records:
                            # It's possible to get 200 OK but have no records on the *current* page
                            print("No records found on this page (Status 200, empty data).")
                            logger.info(f"No records returned on page {page}, though status was 200.")
                            # Check info object to decide if there *might* be more on subsequent pages
                            if info is None or info.get_more_records() is not True:
                                more_records = False  # Stop if no records AND no indication of more
                                print("No more records indicated by API info.")
                                logger.info("No more records indicated by API info object on empty page.")
                            else:
                                # This case is unusual (empty page but more_records=True), log it.
                                print("Empty page, but API indicates more records. Proceeding to next page.")
                                logger.warning(f"Empty data on page {page}, but info.more_records=True. Proceeding.")
                                page += 1  # Increment page to fetch next
                                continue

                        else:  # Records found on this page
                            print(f"Processing {len(records)} records from page {page}...")
                            for record in records:
                                try:
                                    lead_id = record.get_id()
                                    
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
                                            "first_name": first_name or "",  # Handle None values
                                            "last_name": last_name or "",    # Handle None values
                                            "email": email or "",            # Handle None values
                                            "status": status,
                                            "notes": notes or ""             # Handle None values
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
                        more_records = False  # Stop pagination on error

                    else:
                        # Handle unexpected response object type
                        print(f"⚠️ Unexpected response object type for get_records (Status 200): {type(response_object)}")
                        logger.warning(f"Unexpected response object type for get_records page {page} (Status 200): {type(response_object)}")
                        more_records = False
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

            else:  # response is None
                print("❌ API call failed: No response received.")
                logger.error(f"API call failed for get_records page {page}: No response received.")
                more_records = False

        except APIException as ex:
            # Catch APIExceptions raised directly by the SDK call (e.g., network issues before response)
            status_obj = ex.get_status()
            code_obj = ex.get_code()
            message_obj = ex.get_message()
            details = ex.get_details()
            status = status_obj.get_value() if status_obj else 'N/A'
            code = code_obj.get_value() if code_obj else 'N/A'
            msg_val = message_obj.get_value() if message_obj and hasattr(message_obj, 'get_value') else str(message_obj)
            details_str = str(details) if details else 'None'
            print(f"✖ Outer APIException occurred during get_records pagination: Code: {code}, Status: {status}, Message: {msg_val}")
            print(f"  Details: {details_str}")
            logger.error(f"Outer APIException during get_records page {page}: Code: {code}, Status: {status}, Message: {msg_val}, Details: {details_str}", exc_info=False)
            more_records = False  # Stop on exception
        except Exception as e:
            print(f"✖ An unexpected error occurred during get_records pagination: {e}")
            logger.error(f"Unexpected error during get_records page {page}", exc_info=True)
            traceback.print_exc()
            more_records = False  # Stop on exception

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
            print(f"  Notes:   {notes if notes else 'N/A'}")  # Ensure empty strings also show as N/A
            print("-" * 80)
            logger.debug(f"Displayed qualification info for Lead ID: {lead.get('id', 'N/A')}")

    print("--- Qualification Process Finished ---")
    logger.info("Qualification process finished.")
    
    return all_qualifying_leads
