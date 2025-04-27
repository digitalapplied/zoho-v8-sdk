# src/api/leads/__init__.py

from .update import update_single_lead_mobile
from .qualify import qualify_leads_from_custom_view
from .common import (
    MODULE, TARGET_LEAD_ID_FOR_UPDATE, NEW_MOBILE_FOR_UPDATE,
    UPDATE_REQ_FIELDS, QUALIFY_FIELDS, logger, QUALIFICATION_CUSTOM_VIEW_ID
)

# Import the SDK initialization to ensure it's available when this package is imported
from src.core import initialize

def main():
    """Main function to run the lead qualification or update functionality"""
    import os
    import sys
    
    # Ensure SDK is initialized
    if initialize.Initializer.get_initializer():
        print("SDK Initialized. Ready to proceed.")
        logger.info("SDK Check: Initializer is available.")

        # Check if the token_store.txt file exists in the expected location
        token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
                                "zoho_data", "tokens", "token_store.txt")
        if not os.path.exists(token_path):
            logger.warning(f"Token file not found at expected path: {token_path}")
            # It might be in the location specified in initialize.py instead
        
        # --- Choose which function to run ---
        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1].lower() == "update":
                # Run the update function
                print("\nRunning Lead Update...")
                if TARGET_LEAD_ID_FOR_UPDATE and TARGET_LEAD_ID_FOR_UPDATE != 0 and NEW_MOBILE_FOR_UPDATE:
                    update_single_lead_mobile(TARGET_LEAD_ID_FOR_UPDATE, NEW_MOBILE_FOR_UPDATE)
                else:
                    print("Skipping update example: LEAD_ID (> 0) or NEW_MOBILE not set correctly in .env")
                    logger.warning("Update example skipped due to missing/invalid .env variables.")
                print("\nLead Update finished.")
            else:
                # Use the first argument as the target status
                target_status = sys.argv[1]
                print(f"\nRunning Lead Qualification with custom status: '{target_status}'...")
                qualify_leads_from_custom_view(target_status)
                print("\nLead Qualification finished.")
        else:
            # Default: Run the qualification function with default status
            print("\nRunning Lead Qualification with default status...")
            qualify_leads_from_custom_view()
            print("\nLead Qualification finished.")

    else:
        print("CRITICAL ERROR: SDK not initialized. Cannot proceed.")
        print("Please check configuration in .env and logs in logs/sdk.log")
        logger.critical("Script aborted: SDK Initializer is not available.")


if __name__ == "__main__":
    main()
