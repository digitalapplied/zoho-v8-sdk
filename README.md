# Zoho CRM Python SDK v8 Implementation

A field-tested implementation of the Zoho CRM Python SDK v8 (`zohocrmsdk8_0`), following best practices for authentication, initialization, and API operations.

## Features

- Automatic DataCenter detection based on account URL
- Proper token management with FileStore for automatic renewals
- Safe Lead update pattern that pre-fetches mandatory fields
- Complete implementation of OAuth flow

## Project Structure

- `src/initialize_zcrmv8.py` - SDK initializer with automatic DataCenter detection
- `src/update_lead.py` - Lead update example with safe update pattern
- `src/test_init.py` - Test script for SDK initialization
- `CHECKLIST.md` - Implementation progress tracking

## Setup

1. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

2. Install dependencies:
   ```
   pip install --upgrade pip
   pip install zohocrmsdk8_0==2.0.0 python-dotenv
   ```

3. Configure your `.env` file with your Zoho CRM credentials (see `.env.template`).

4. Run the test initialization script:
   ```
   python src/test_init.py
   ```

## Lead Update Example

The `update_lead.py` script demonstrates a safe pattern for updating Leads in Zoho CRM, avoiding the common `MANDATORY_NOT_FOUND` error by pre-fetching required fields.

## License

Private repository - All rights reserved.
