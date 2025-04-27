# src/api/leads/__init__.py

# Expose the core functions for external use (e.g., by cli.py)
from .update import update_single_lead_mobile
from .qualify import qualify_leads_from_custom_view

# Import the SDK initialization to ensure it's triggered if this package is the first point of contact
# Also import the application logger configured there.
# This assumes core.initialize has run successfully before this is imported,
# which is typically true when cli.py is the entry point.
try:
    from src.core.initialize import logger
except ImportError:
    # Fallback basic logger if somehow initialize hasn't run or failed silently
    # This shouldn't happen if cli.py runs first and handles errors
    import logging
    logger = logging.getLogger('zoho_app_fallback')
    logger.warning("Could not import logger from src.core.initialize in api.leads init.")

# No main() function or if __name__ == "__main__": block here

# --- End of src/api/leads/__init__.py ---