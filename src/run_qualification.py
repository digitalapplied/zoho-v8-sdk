import os
import sys

# Add the project root directory (parent of src) to the Python path
current_file_dir = os.path.dirname(os.path.abspath(__file__)) # d:\zoho_v8\src
project_root = os.path.dirname(current_file_dir) # d:\zoho_v8

# Insert project root into sys.path if not already present
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Optional: Add src directory too, though project_root should suffice for 'from src...' imports
# src_dir = current_file_dir
# if src_dir not in sys.path:
#     sys.path.insert(1, src_dir)

try:
    # Import using the project root as the base
    # Import the new function that uses the Custom View
    from src.api.leads.qualify import qualify_leads_from_custom_view
    # Import the initialize module to trigger SDK setup, and import the logger
    import src.core.initialize 
    from src.core.initialize import logger
    SDK_INITIALIZED = True
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Please ensure the script is run from a location where 'api' and 'common' packages are discoverable, or adjust sys.path accordingly.")
    print(f"Current sys.path: {sys.path}")
    SDK_INITIALIZED = False
    # Define dummy logger and function if imports fail
    class DummyLogger:
        def info(self, msg):
            print(f"INFO: {msg}")
        def error(self, msg, exc_info=False):
            print(f"ERROR: {msg}")
        def debug(self, msg):
            print(f"DEBUG: {msg}") # Add debug for dummy
    logger = DummyLogger()
    # Update dummy function name
    def qualify_leads_from_custom_view(): 
        logger.error("qualify_leads_from_custom_view could not be imported.")


if __name__ == "__main__":
    if SDK_INITIALIZED:
        logger.info("Starting lead qualification process...")
        try:
            # SDK should be initialized by the 'import src.core.initialize' above
            logger.info("SDK initialization should have occurred via import.")

            # Run the qualification function using the Custom View
            logger.info("Calling qualify_leads_from_custom_view...")
            qualify_leads_from_custom_view() # Call the new function
            logger.info("Lead qualification process using Custom View completed successfully.")

        except Exception as e:
            logger.error(f"An error occurred during the qualification process: {e}", exc_info=True)
        finally:
            logger.info("Script finished execution.")
    else:
        logger.error("Script could not start due to import errors. SDK not initialized.")
