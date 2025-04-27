# src/api/leads/qualify.py
import os
import traceback

# --- Zoho SDK Imports ---
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, APIException, GetRecordsParam, ResponseWrapper, BodyWrapper
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap
from zohocrmsdk.src.com.zoho.crm.api.record import Info as RecordInfo # Avoid conflict with logging.Info

# --- Local Imports ---
# Import logger from the corrected location
from src.core.initialize import logger, PROJECT_ROOT # Import logger and PROJECT_ROOT
# Import common variables and helper
from .common import (
    MODULE, QUALIFY_FIELDS, extract_field_value, QUALIFICATION_CUSTOM_VIEW_ID
)


def qualify_leads_from_custom_view(custom_view_id=None, output_filename="lead_qualification_cv_results.txt"):
    """
    Fetches leads from a specified Zoho CRM Custom View, extracts details,
    and writes them to a file. Handles pagination up to Zoho's limit for CV fetches.

    Args:
        custom_view_id (str, optional): The ID of the Custom View. If None, uses
                                        QUALIFICATION_CUSTOM_VIEW_ID from common.py/.env.
        output_filename (str): The name for the output text file (created in project's output/ dir).
    """
    cv_id_to_use = custom_view_id or QUALIFICATION_CUSTOM_VIEW_ID

    if not cv_id_to_use:
        error_msg = "Custom View ID is required for qualification. Provide --cvid or set QUALIFICATION_CUSTOM_VIEW_ID in .env."
        print(f"❌ Error: {error_msg}")
        logger.error(f"Qualification failed: {error_msg}")
        return # Stop execution

    print("=" * 60)
    print(f"LEAD QUALIFICATION PROCESS - Custom View ID: {cv_id_to_use}")
    print("=" * 60)
    logger.info(f"Starting qualification process for leads from Custom View ID: {cv_id_to_use}")

    ops = RecordOperations(MODULE) # Pass the module name
    qualified_leads_cv = []
    page = 1
    more_records = True # Assume there are records initially
    records_processed = 0

    # --- REMOVE param_instance creation from here ---
    # param_instance = ParameterMap()
    # param_instance.add(GetRecordsParam.cvid, cv_id_to_use)
    # param_instance.add(GetRecordsParam.fields, ",".join(QUALIFY_FIELDS))
    # param_instance.add(GetRecordsParam.per_page, 200)

    print("Starting data retrieval from Custom View...")

    while more_records:
        # --- CREATE param_instance INSIDE the loop ---
        param_instance = ParameterMap()
        param_instance.add(GetRecordsParam.cvid, cv_id_to_use)
        param_instance.add(GetRecordsParam.fields, ",".join(QUALIFY_FIELDS))
        param_instance.add(GetRecordsParam.per_page, 200) # Use max per page
        param_instance.add(GetRecordsParam.page, page) # Set current page

        print(f"Fetching page {page}...")
        # Log the parameters being used for this specific page request
        # Note: ParameterMap doesn't have a standard __str__ or __repr__, logging its internal map might be complex.
        # Logging key info is sufficient.
        logger.info(f"Fetching page {page} from CV {cv_id_to_use} with fields: {', '.join(QUALIFY_FIELDS)}")

        try:
            # Execute the request
            response = ops.get_records(param_instance, HeaderMap())

            if response is not None:
                status_code = response.get_status_code()
                logger.debug(f"API call status code for CV {cv_id_to_use}, page {page}: {status_code}")

                if status_code == 204: # No Content
                    print("No more records found in Custom View (Status 204).")
                    logger.info(f"Received 204 No Content for CV {cv_id_to_use} on page {page}, stopping pagination.")
                    more_records = False # Stop the loop

                elif status_code == 200: # OK
                    response_object = response.get_object()

                    # get_records for CV usually returns ResponseWrapper directly
                    if isinstance(response_object, ResponseWrapper):
                        records = response_object.get_data() # List of Record objects
                        info = response_object.get_info()     # Info object

                        if not records:
                            print(f"No records found on page {page} (Status 200, empty data list).")
                            logger.info(f"No records returned on page {page} for CV {cv_id_to_use}, though status was 200.")
                            if info is None or not isinstance(info, RecordInfo) or info.get_more_records() is not True:
                                more_records = False
                                print("No more records indicated by API info.")
                                logger.info("No more records indicated by API info object on empty page.")
                            else:
                                print("API indicates more records exist, but current page is empty. Stopping.")
                                logger.warning(f"Empty data on page {page} for CV {cv_id_to_use}, but info.get_more_records()=True. Stopping loop.")
                                more_records = False

                        else: # Records found on this page
                            current_page_count = len(records)
                            records_processed += current_page_count
                            print(f"Processing {current_page_count} records from page {page} (Total processed: {records_processed})...")

                            for index, record in enumerate(records):
                                try:
                                    lead_id = record.get_id()
                                    first_name = extract_field_value(record, "First_Name")
                                    last_name = extract_field_value(record, "Last_Name")
                                    email = extract_field_value(record, "Email")
                                    notes = extract_field_value(record, "Additional_Relocation_Notes")
                                    status = extract_field_value(record, "Lead_Status")

                                    if index < 5:
                                        logger.debug(f"CV Record {index+1}/{current_page_count} - ID: {lead_id}, Status: '{status}', Email: '{email}'")

                                    full_name = ' '.join(filter(None, [first_name, last_name]))
                                    qualified_leads_cv.append({
                                        'id': lead_id,
                                        'name': full_name.strip() or 'N/A',
                                        'email': email or 'N/A',
                                        'status': status or 'N/A',
                                        'notes': notes.strip() if notes else 'N/A'
                                    })

                                except Exception as inner_ex:
                                    lead_id_str = str(getattr(record, 'id', 'UNKNOWN_ID'))
                                    print(f"Error processing individual record {lead_id_str} from CV: {inner_ex}")
                                    logger.error(f"Error processing individual record {lead_id_str} from CV {cv_id_to_use} on page {page}", exc_info=True)

                            # Check for more records AFTER processing the current page
                            if info is not None and isinstance(info, RecordInfo) and info.get_more_records() is True:
                                page += 1
                                more_records = True
                                logger.info("More records indicated by API, proceeding to next page.")
                            else:
                                print("No more records indicated by API after processing page.")
                                logger.info("No more records indicated by API info object.")
                                more_records = False # Stop the loop

                    elif isinstance(response_object, APIException):
                        ex = response_object
                        status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
                        code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
                        message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
                        details_val = ex.get_details()
                        print(f"❌ API Exception during get_records (Page {page}): Code: {code_val}, Status: {status_val}, Message: {message_val}")
                        logger.error(f"API Exception getting records page {page} for CV {cv_id_to_use}: Code={code_val}, Status={status_val}, Msg={message_val}, Details={details_val}")
                        more_records = False

                    else:
                        print(f"⚠️ Unexpected response object type for get_records (Status 200): {type(response_object)}")
                        logger.warning(f"Unexpected response object type for get_records page {page} (Status 200): {type(response_object)}")
                        more_records = False

                else: # Handle other non-200, non-204 status codes
                    error_message = f"Unexpected HTTP status code {status_code} received."
                    try:
                        if isinstance(response.get_object(), APIException):
                           ex = response.get_object()
                           status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
                           code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
                           message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
                           details_val = ex.get_details()
                           error_message = f"API Error Details: Code: {code_val}, Status: {status_val}, Message: {message_val}"
                           logger.error(f"API Exception on page {page} for CV {cv_id_to_use}: Code={code_val}, Status={status_val}, Msg={message_val}, Details={details_val}")
                        else:
                            logger.error(f"Unexpected HTTP status {status_code} received for get_records page {page}, Response Obj: {response.get_object()}")
                    except Exception as log_ex:
                        logger.error(f"Could not parse error response object for status {status_code}: {log_ex}")

                    print(f"❌ {error_message}")
                    more_records = False

            else: # response is None
                print("❌ API call failed: No response received.")
                logger.error(f"API call failed for get_records page {page}: No response received.")
                more_records = False

        except APIException as ex:
            status_val = ex.get_status().get_value() if ex.get_status() else 'N/A'
            code_val = ex.get_code().get_value() if ex.get_code() else 'N/A'
            message_val = ex.get_message().get_value() if ex.get_message() else 'N/A'
            details_val = ex.get_details()
            print(f"❌ An SDK APIException occurred during pagination: {status_val} - {code_val} - {message_val}")
            logger.error(f"Outer APIException during get_records page {page} for CV {cv_id_to_use}: Status={status_val}, Code={code_val}, Msg={message_val}, Details={details_val}", exc_info=True)
            more_records = False
        except Exception as e:
            print(f"❌ An unexpected error occurred during pagination: {e}")
            logger.error(f"Unexpected error during get_records page {page} for CV {cv_id_to_use}", exc_info=True)
            more_records = False

    # --- Process and Write Results ---
    print("\n" + "=" * 60)
    print(f"RESULTS: Found {len(qualified_leads_cv)} Leads from Custom View {cv_id_to_use} (Processed {records_processed} total records)")
    print("=" * 60 + "\n")

    output_dir = PROJECT_ROOT / "output"
    try:
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"RESULTS: Found {len(qualified_leads_cv)} Leads from Custom View ID {cv_id_to_use}\n")
            f.write(f"(Processed {records_processed} total records across fetched pages)\n")
            f.write("=" * 60 + "\n\n")

            if qualified_leads_cv:
                print(f"Writing {len(qualified_leads_cv)} qualified leads to {output_path}...")
                for lead in qualified_leads_cv:
                    f.write(f"Lead ID: {lead.get('id', 'N/A')}\n")
                    f.write(f"Name:    {lead.get('name', 'N/A')}\n")
                    f.write(f"Email:   {lead.get('email', 'N/A')}\n")
                    f.write(f"Status:  {lead.get('status', 'N/A')}\n")
                    f.write(f"Notes:   {lead.get('notes', 'N/A')}\n")
                    f.write("-" * 80 + "\n")
            else:
                f.write("No leads found or processed successfully from this Custom View.\n")
                print("  No leads were found or processed successfully from the Custom View.")

        print(f"Results successfully written to {output_path}")
        logger.info(f"Results successfully written to {output_path}")

    except Exception as e:
        print(f"❌ Error writing results to file {output_filename}: {e}")
        logger.error(f"Error writing results to file {output_path}: {e}", exc_info=True)

    print("--- Custom View Qualification Process Finished ---")
    logger.info(f"Custom View qualification process finished for CV ID: {cv_id_to_use}.")

# --- End of src/api/leads/qualify.py ---