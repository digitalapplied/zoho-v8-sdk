import os
import traceback
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations, APIException, GetRecordsParam, ResponseWrapper, BodyWrapper
)
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

from .common import (
    MODULE, QUALIFY_FIELDS, logger, extract_field_value, QUALIFICATION_CUSTOM_VIEW_ID
)


def qualify_leads_from_custom_view(custom_view_id=None, output_filename="lead_qualification_cv_results.txt"):
    """
    Fetches the first 200 leads from a specified Zoho CRM Custom View and prints relevant details.
    Results are also written to a txt file.

    Args:
        custom_view_id (str, optional): The ID of the Custom View. Defaults to value from .env or None.
        output_filename (str): The name for the output text file.
    """
    cv_id_to_use = custom_view_id or QUALIFICATION_CUSTOM_VIEW_ID

    if not cv_id_to_use:
        print("=" * 60)
        print("❌ Error: Custom View ID is required.")
        print("  Please provide it as an argument or set QUALIFICATION_CUSTOM_VIEW_ID in your .env file.")
        print("=" * 60)
        logger.error("Qualification failed: No Custom View ID provided or found in environment variables.")
        return

    print("=" * 60)
    print(f"LEAD QUALIFICATION PROCESS - Custom View ID: {cv_id_to_use}")
    print("=" * 60)
    logger.info(f"Starting qualification process for leads from Custom View ID: {cv_id_to_use}")

    ops = RecordOperations(MODULE)
    qualified_leads_cv = []
    page = 1

    print("Starting data retrieval from Custom View...")
    print(f"Fetching page {page}...")
    logger.info(f"Fetching page {page} from CV {cv_id_to_use} with fields: {', '.join(QUALIFY_FIELDS)}")

    param_instance = ParameterMap()
    param_instance.add(GetRecordsParam.cvid, cv_id_to_use)
    param_instance.add(GetRecordsParam.fields, ",".join(QUALIFY_FIELDS))
    param_instance.add(GetRecordsParam.per_page, 200)
    param_instance.add(GetRecordsParam.page, page)

    try:
        response = ops.get_records(param_instance, HeaderMap())

        if response is not None:
            status_code = response.get_status_code()
            logger.info(f"API call status code for CV {cv_id_to_use}, page {page}: {status_code}")

            if status_code == 204:
                print(f"No records found in Custom View {cv_id_to_use} (Status 204).")
                logger.info(f"Received 204 No Content for CV {cv_id_to_use}.")

            elif status_code == 200:
                response_object = response.get_object()

                if isinstance(response_object, ResponseWrapper) or isinstance(response_object, BodyWrapper):
                    records = response_object.get_data()

                    if not records:
                        print(f"No records found on this page for CV {cv_id_to_use} (Status 200, empty data).")
                        logger.info(f"No records returned on page {page} for CV {cv_id_to_use}, though status was 200.")
                    else:
                        print(f"Processing {len(records)} records from CV {cv_id_to_use}, page {page}...")
                        for index, record in enumerate(records):
                            try:
                                lead_id = record.get_id()
                                first_name = extract_field_value(record, "First_Name")
                                last_name = extract_field_value(record, "Last_Name")
                                email = extract_field_value(record, "Email")
                                notes = extract_field_value(record, "Additional_Relocation_Notes")
                                status = extract_field_value(record, "Lead_Status")

                                if index < 10:
                                    logger.debug(f"CV Record {index+1}/{len(records)} - ID: {lead_id}, Status: '{status}', Notes: '{notes}'")

                                full_name = ' '.join(filter(None, [first_name, last_name]))
                                qualified_leads_cv.append({
                                    'id': lead_id,
                                    'name': full_name or 'N/A',
                                    'email': email or 'N/A',
                                    'notes': notes.strip() if notes else 'N/A'
                                })
                                logger.debug(f"Added lead from CV: ID {lead_id}")

                            except Exception as inner_ex:
                                lead_id_str = str(getattr(record, 'id', 'UNKNOWN_ID'))
                                print(f"Error processing individual record {lead_id_str} from CV: {inner_ex}")
                                logger.error(f"Error processing individual record {lead_id_str} from CV {cv_id_to_use} on page {page}", exc_info=True)

                elif isinstance(response_object, APIException):
                    status_obj = response_object.get_status()
                    code_obj = response_object.get_code()
                    message_obj = response_object.get_message()
                    details = response_object.get_details()
                    status_val = status_obj.get_value() if status_obj else 'N/A'
                    code_val = code_obj.get_value() if code_obj else 'N/A'
                    message_val = message_obj.get_value() if message_obj else 'N/A'
                    print(f"API Exception received for CV {cv_id_to_use}: Status: {status_val}, Code: {code_val}, Message: {message_val}")
                    if details:
                        print(f"Details: {details}")
                    logger.error(f"API Exception for CV {cv_id_to_use}: Status: {status_val}, Code: {code_val}, Message: {message_val}, Details: {details}")

                else:
                    print(f"Received unexpected response object type: {type(response_object)}")
                    logger.warning(f"Unexpected response type for CV {cv_id_to_use}: {type(response_object)}")

            else:
                print(f"Error fetching records from CV {cv_id_to_use}: HTTP Status Code {status_code}")
                logger.error(f"HTTP Error for CV {cv_id_to_use}: {status_code}. Response: {response.get_string() if hasattr(response, 'get_string') else 'N/A'}")

    except APIException as api_ex:
        status_obj = api_ex.get_status()
        code_obj = api_ex.get_code()
        message_obj = api_ex.get_message()
        details = api_ex.get_details()
        status_val = status_obj.get_value() if status_obj else 'N/A'
        code_val = code_obj.get_value() if code_obj else 'N/A'
        message_val = message_obj.get_value() if message_obj else 'N/A'
        print(f"API Exception occurred during operation for CV {cv_id_to_use}: Status: {status_val}, Code: {code_val}, Message: {message_val}")
        if details:
            print(f"Details: {details}")
        logger.error(f"API Exception during operation for CV {cv_id_to_use}: Status: {status_val}, Code: {code_val}, Message: {message_val}, Details: {details}", exc_info=True)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.error(f"Unexpected error during qualification for CV {cv_id_to_use}: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print(f"RESULTS: Found {len(qualified_leads_cv)} Leads from Custom View {cv_id_to_use}")
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
    logger.info(f"Custom View qualification process finished for CV ID: {cv_id_to_use}.")

    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"RESULTS: Found {len(qualified_leads_cv)} Leads from Custom View ID {cv_id_to_use}\n")
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
