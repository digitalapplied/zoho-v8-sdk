import unittest
import time

# Use absolute import from the src package
from src.core.initialize import Initializer


class TestSDKInitialization(unittest.TestCase):
    def test_initialization_singleton(self):
        """Test that Initializer is available and is a singleton."""
        # First call initializes (triggered by the import)
        init1 = Initializer.get_initializer()
        self.assertIsNotNone(init1, "Initializer should be available after import.")

        # Wait a bit (optional)
        time.sleep(0.1)

        # Second call should return the same instance
        init2 = Initializer.get_initializer()
        self.assertIs(init1, init2, "Second call should return the same singleton instance.")


if __name__ == '__main__':
    unittest.main()
