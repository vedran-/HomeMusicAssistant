import unittest
import os
import shutil
from src.config.settings import load_settings
from src.memory.memory_manager import MemoryManager

class TestMemoryManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        cls.test_memory_dir = "./test_memory_data"
        # Start with a clean directory
        if os.path.exists(cls.test_memory_dir):
            shutil.rmtree(cls.test_memory_dir, ignore_errors=True)
        os.makedirs(cls.test_memory_dir, exist_ok=True)
        
        cls.settings = load_settings()
        if not cls.settings.mem0_config:
            raise unittest.SkipTest("Mem0 config not found, skipping memory manager tests.")
        cls.settings.mem0_config.data_path = cls.test_memory_dir
        
        cls.memory_manager = MemoryManager(cls.settings.mem0_config)
        cls.user_id = "test_user"
        cls.session_id = "test_session_123"

    @classmethod
    def tearDownClass(cls):
        """Clean up the test environment after all tests."""
        if cls.memory_manager:
            cls.memory_manager.close()
        # Clean up the test directory
        if os.path.exists(cls.test_memory_dir):
            shutil.rmtree(cls.test_memory_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh state for each test by clearing memories."""
        self.memory_manager.clear_session(user_id=self.user_id, session_id=self.session_id)

    def test_01_initialization(self):
        """Test if MemoryManager initializes correctly."""
        self.assertIsNotNone(self.memory_manager, "MemoryManager should not be None")
        self.assertTrue(self.memory_manager.enabled, "MemoryManager should be enabled")
        self.assertIsNotNone(self.memory_manager.mem0, "mem0 instance should be created")

    def test_02_add_and_search_memory(self):
        """Test adding to and searching memory."""
        # 1. Add some data
        messages_to_add = [
            {"role": "user", "content": "My favorite color is blue."},
            {"role": "assistant", "content": "I will remember that your favorite color is blue."}
        ]
        self.memory_manager.add(messages=messages_to_add, user_id=self.user_id, session_id=self.session_id)
        
        # 2. Search for the data
        query = "What is my favorite color?"
        search_results = self.memory_manager.search(query=query, user_id=self.user_id, session_id=self.session_id)
        
        # 3. Verify the results
        self.assertIsNotNone(search_results, "Search results should not be None")
        self.assertIsInstance(search_results, list, "Search results should be a list")
        self.assertGreater(len(search_results), 0, "Should find at least one relevant memory")

        # Check the content of the results
        found_match = any("blue" in result.get('memory', '').lower() for result in search_results)
        self.assertTrue(found_match, "The retrieved memory should contain the favorite color 'blue'")

    def test_03_search_with_no_results(self):
        """Test a search that should yield no results."""
        query = "What is the capital of Mars?"
        search_results = self.memory_manager.search(query=query, user_id=self.user_id, session_id=self.session_id)
        
        self.assertEqual(len(search_results), 0, "Search for irrelevant info should return no results")


if __name__ == '__main__':
    print("Running MemoryManager tests...")
    print("Ensure your configured embedder service (e.g., LM Studio) is running.")
    unittest.main()
