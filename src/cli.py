# FILE: src/cli.py
import os
import sys
import argparse
import traceback

# Ensure the project root is in the path for finding 'src'
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import Core and API Functions ---
# This MUST come after adjusting sys.path if running as top-level script
try:
    from src.core import initialize # Trigger SDK initialization
    from src.core.initialize import logger # Get configured logger
    from src.api.leads.qualify import qualify_leads_from_custom_view
    from src.api.leads.update import update_single_lead_mobile
    from src.api.leads.common import TARGET_LEAD_ID_FOR_UPDATE, NEW_MOBILE_FOR_UPDATE # Get defaults from common
    SDK_INITIALIZED = True
except ImportError as e:
    print(f"[ERROR] Failed to import necessary modules: {e}")
    print("Please ensure you are running this script from the project root directory")
    print(f"Current sys.path: {sys.path}")
    traceback.print_exc()
    # Define dummy logger if import fails
    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def critical(self, msg): print(f"CRITICAL: {msg}")
    logger = DummyLogger()
    SDK_INITIALIZED = False
    # Define dummy functions to prevent NameErrors later if imports failed
    def qualify_leads_from_custom_view(*args, **kwargs): logger.error("Qualification function not available due to import error.")
    def update_single_lead_mobile(*args, **kwargs): logger.error("Update function not available due to import error.")
    TARGET_LEAD_ID_FOR_UPDATE = 0
    NEW_MOBILE_FOR_UPDATE = ""


def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Zoho CRM Leads CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # --- Qualify Command ---
    parser_qualify = subparsers.add_parser('qualify', help='Qualify leads based on a Custom View')
    parser_qualify.add_argument(
        '--cvid',
        type=str,
        default=None, # Default handled by the function using env var
        help='Zoho CRM Custom View ID (overrides value in .env)'
    )
    parser_qualify.add_argument(
        '--output',
        type=str,
        default="lead_qualification_results.txt",
        help='Output filename for qualification results (in output/ dir)'
    )

    # --- Update Command ---
    parser_update = subparsers.add_parser('update', help='Update a single lead\'s mobile number')
    parser_update.add_argument(
        '--id',
        type=int,
        default=TARGET_LEAD_ID_FOR_UPDATE, # Default from .env via common.py
        help='Lead ID to update (overrides value in .env)'
    )
    parser_update.add_argument(
        '--mobile',
        type=str,
        default=NEW_MOBILE_FOR_UPDATE, # Default from .env via common.py
        help='New mobile number (overrides value in .env)'
    )

    args = parser.parse_args()

    # --- SDK Initialization Check ---
    if not SDK_INITIALIZED:
        logger.critical("Exiting: SDK failed to initialize due to import errors.")
        sys.exit(1) # Exit if imports failed

    # Explicitly check if initializer is available AFTER attempting imports
    # The import of 'src.core.initialize' should have run the initialization code
    if initialize.Initializer.get_initializer():
        logger.info("SDK Initialized Successfully. Proceeding with command.")
        # Optionally print to console here instead of in initialize.py
        # print("✅ SDK Initialized Successfully!") 
    else:
        logger.critical("Exiting: SDK Initializer is not available after import. Check logs/sdk.log")
        sys.exit(1)

    # --- Execute Command ---
    try:
        if args.command == 'qualify':
            logger.info(f"Executing 'qualify' command with CV ID: {args.cvid or 'Default from .env'} and Output: {args.output}")
            qualify_leads_from_custom_view(custom_view_id=args.cvid, output_filename=args.output)

        elif args.command == 'update':
            logger.info(f"Executing 'update' command for Lead ID: {args.id} with Mobile: {'*' * (len(args.mobile) - 4) + args.mobile[-4:] if args.mobile else 'N/A'}") # Mask mobile in log
            if not args.id or args.id <= 0:
                print("❌ Error: Invalid or missing Lead ID for update.")
                logger.error("Update command failed: Invalid or missing --id.")
            elif not args.mobile:
                 print("❌ Error: Missing mobile number for update.")
                 logger.error("Update command failed: Missing --mobile.")
            else:
                update_single_lead_mobile(target_lead_id=args.id, new_mobile=args.mobile)

    except Exception as e:
        logger.error(f"An unexpected error occurred executing command '{args.command}': {e}", exc_info=True)
        print(f"❌ An unexpected error occurred: {e}")
        traceback.print_exc()

    finally:
        logger.info(f"CLI command '{args.command}' finished execution.")


if __name__ == "__main__":
    main()
