from initialize_zcrmv8 import Initializer
import os
from dotenv import load_dotenv

load_dotenv()

# Check if initialization was successful
if Initializer.get_initializer():
    print("✅ SDK initialization successful!")
    print(f"Environment: {Initializer.get_initializer().environment.url}")
    print(f"User email: {os.getenv('USER_EMAIL')}")
    print("Token store path:", Initializer.get_initializer().store.file_path)
else:
    print("❌ SDK initialization failed!")
    print("Check logs/sdk.log for more details")
