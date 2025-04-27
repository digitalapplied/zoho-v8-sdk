# src/cli.py
import sys
import os
from pathlib import Path
import argparse
import traceback # Keep traceback for unexpected errors

# Ensure the src directory is in the Python path
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent # Assuming cli.py is in src/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT)) # Add project root for 'from src...'

# --- Early Core Imports (Logging) ---
# Import the application logger configured in initialize.py
# This MUST run before the SDK initialization attempt.
try:
    # Import the logger instance directly from the initialize module
    from src.core.initialize import logger
    logger.info("CLI script started.")
except ImportError as e:
    # This implies a fundamental problem with paths or initialize.py structure
    print(f"Critical Error: Failed to import logger from src.core.initialize: {e}")
    # Attempt basic logging if possible
    try:
        import logging
        logging.basicConfig(level=logging.ERROR)
        logging.critical(f"Failed to import logger from src.core.initialize: {e}", exc_info=True)
    except Exception:
        pass # Cannot log if logging itself fails
    sys.exit(1)
except Exception as e:
    print(f"Critical Error during initial logger import: {e}")
    sys.exit(1)

# --- SDK Initialization Import & Check ---
# This import *triggers* the initialization logic in core/initialize.py
# It must happen *after* logging is ready.
try:
    # Import the initialize module itself to ensure its code runs
    from src.core import initialize
    # Import the SDK's Initializer class *specifically* to check the status
    from zohocrmsdk.src.com.zoho.crm.api.initializer import Initializer

    # Check if initialization was successful (Initializer will hold the instance)
    if Initializer.get_initializer():
        print("✅ Zoho CRM SDK Initialized Successfully!") # User feedback
        logger.info("Zoho CRM SDK Initialization confirmed in cli.py.")
    else:
        # If get_initializer() is None, initialization failed inside initialize.py
        # The error should have been logged and raised there by initialize.py
        # This is a fallback message in case the script somehow continues unexpectedly.
        print("❌ Zoho CRM SDK Initialization failed. Check logs/app.log and logs/sdk.log.")
        logger.error("Initialization check in cli.py failed: Initializer.get_initializer() returned None.")
        sys.exit(1) # Ensure exit if initialization somehow failed silently

except RuntimeError as e:
    # Catch the RuntimeError explicitly raised by our initialize.py on failure
    print(f"{e}") # Print the user-friendly error message from initialize.py
    # Detailed logging already done in initialize.py
    sys.exit(1)
except ImportError as e:
    # Handle cases where SDK components themselves cannot be imported
    print(f"Critical Error: Failed to import SDK components needed for initialization: {e}")
    logger.critical(f"Failed to import SDK components: {e}", exc_info=True)
    sys.exit(1)
except Exception as e:
    # Catch any other unexpected error during the SDK initialization import/check phase
    print(f"Critical Error during SDK initialization phase: {e}")
    logger.critical(f"Unexpected error during SDK initialization phase: {e}", exc_info=True)
    sys.exit(1)


# --- Late API Imports ---
# Import API functions *after* SDK is confirmed initialized.
try:
    from src.api.leads import update_single_lead_mobile, qualify_leads_from_custom_view
    # Import constants needed for argument parsing or default values
    from src.api.leads.common import (
        TARGET_LEAD_ID_FOR_UPDATE, NEW_MOBILE_FOR_UPDATE,
        QUALIFICATION_CUSTOM_VIEW_ID
    )
except ImportError as e:
     print(f"Error: Failed to import API functions (check src/api/leads/*): {e}")
     logger.error(f"Failed to import API functions: {e}", exc_info=True)
     sys.exit(1)

# --- Argument Parsing & Main Execution ---
def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(description="Zoho CRM Leads CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # --- Qualify Command ---
    parser_qualify = subparsers.add_parser('qualify', help='Qualify leads based on a Custom View')
    parser_qualify.add_argument(
        '--cvid',
        type=str,
        default=QUALIFICATION_CUSTOM_VIEW_ID, # Default from .env via common.py
        help=f'Zoho CRM Custom View ID (default from .env: {QUALIFICATION_CUSTOM_VIEW_ID or "Not Set"})'
    )
    parser_qualify.add_argument(
        '--output',
        type=str,
        default="lead_qualification_results.txt",
        help='Output filename for qualification results (in output/ dir)'
    )
    # Removed '--status' argument as qualify function doesn't use it currently

    # --- Update Command ---
    parser_update = subparsers.add_parser('update', help='Update a single lead\'s mobile number')
    parser_update.add_argument(
        '--id',
        type=int,
        default=TARGET_LEAD_ID_FOR_UPDATE, # Default from .env via common.py
        help=f'Lead ID to update (default from .env: {TARGET_LEAD_ID_FOR_UPDATE or "Not Set"})'
    )
    parser_update.add_argument(
        '--mobile',
        type=str,
        default=NEW_MOBILE_FOR_UPDATE, # Default from .env via common.py
        help=f'New mobile number (default from .env: {"*" * (len(NEW_MOBILE_FOR_UPDATE) - 4) + NEW_MOBILE_FOR_UPDATE[-4:] if NEW_MOBILE_FOR_UPDATE and len(NEW_MOBILE_FOR_UPDATE)>4 else "Not Set"})' # Mask default in help
    )

    args = parser.parse_args()

    # --- Execute Command ---
    try:
        if args.command == 'qualify':
            cvid_used = args.cvid or QUALIFICATION_CUSTOM_VIEW_ID # Ensure we use the final ID
            if not cvid_used:
                 print("❌ Error: Custom View ID is required for qualification. Provide --cvid or set QUALIFICATION_CUSTOM_VIEW_ID in .env.")
                 logger.error("Qualify command failed: Missing Custom View ID.")
                 return # Exit main function, avoids sys.exit()

            logger.info(f"Executing 'qualify' command with CV ID: {cvid_used} and Output: {args.output}")
            qualify_leads_from_custom_view(
                custom_view_id=cvid_used,
                output_filename=args.output
            )
            # Qualify function handles its own success/failure reporting

        elif args.command == 'update':
            # Use resolved arguments
            lead_id_to_update = args.id
            mobile_to_set = args.mobile

            # Mask mobile in logs for privacy
            masked_mobile = '*' * (len(mobile_to_set) - 4) + mobile_to_set[-4:] if mobile_to_set and len(mobile_to_set) > 4 else mobile_to_set
            logger.info(f"Executing 'update' command for Lead ID: {lead_id_to_update} with Mobile: {masked_mobile}")

            if not lead_id_to_update or lead_id_to_update <= 0:
                print("❌ Error: Invalid or missing Lead ID for update. Provide --id or set LEAD_ID > 0 in .env.")
                logger.error("Update command failed: Invalid or missing --id.")
            elif not mobile_to_set:
                 print("❌ Error: Missing mobile number for update. Provide --mobile or set NEW_MOBILE in .env.")
                 logger.error("Update command failed: Missing --mobile.")
            else:
                success = update_single_lead_mobile(target_lead_id=lead_id_to_update, new_mobile=mobile_to_set)
                # Success/failure message is printed within update_single_lead_mobile now
                # if success:
                #     print(f"✅ Lead {lead_id_to_update} successfully updated with new mobile number.")
                # else:
                #     print(f"❌ Failed to update Lead {lead_id_to_update}. Check logs for details.")

    except Exception as e:
        # Catch-all for unexpected errors during command execution
        logger.error(f"An unexpected error occurred executing command '{args.command}': {e}", exc_info=True)
        print(f"❌ An unexpected error occurred: {e}")
        print(f"   Check logs/app.log for details.")
        # traceback.print_exc() # Optional: uncomment for console stack trace

    finally:
        logger.info(f"CLI command '{args.command}' finished execution.")

if __name__ == "__main__":
    main()

# --- End of src/cli.py ---