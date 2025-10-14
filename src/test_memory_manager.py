import unittest
import os
import shutil
from src.config.settings import load_settings
from src.memory.memory_manager import MemoryManager
from src.utils.ollama_manager import OllamaManager

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
        
        # Initialize OllamaManager for testing
        try:
            cls.ollama_manager = OllamaManager(idle_timeout_seconds=180)
            print("✅ OllamaManager initialized for testing")
        except Exception as e:
            print(f"⚠️ OllamaManager initialization failed: {e}")
            cls.ollama_manager = None
        
        cls.memory_manager = MemoryManager(cls.settings.mem0_config, ollama_manager=cls.ollama_manager)
        cls.user_id = "test_user"
        cls.session_id1 = "test_session_123"
        cls.session_id2 = "test_session_456"

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
        self.memory_manager.clear_session(user_id=self.user_id, session_id=self.session_id1)
        self.memory_manager.clear_session(user_id=self.user_id, session_id=self.session_id2)
        # Clear long-term by searching and deleting without session filter if needed
        all_memories = self.memory_manager.mem0.get_all(user_id=self.user_id)
        for mem in all_memories.get('results', []):
            self.memory_manager.mem0.delete(memory_id=mem['id'])

    def test_01_initialization(self):
        """Test if MemoryManager initializes correctly."""
        self.assertIsNotNone(self.memory_manager, "MemoryManager should not be None")
        self.assertTrue(self.memory_manager.enabled, "MemoryManager should be enabled")
        self.assertIsNotNone(self.memory_manager.mem0, "mem0 instance should be created")

    def test_02_add_and_search_session_memory(self):
        """Test adding to and searching session-specific memory."""
        # 1. Add session data
        messages_to_add = [
            {"role": "user", "content": "I prefer blue as my favorite color."},
            {"role": "assistant", "content": "Noted your preference for blue."}
        ]
        self.memory_manager.add(messages_to_add, user_id=self.user_id, session_id=self.session_id1, infer=False)
        
        # 2. Search with session filter
        query = "What is my favorite color?"
        search_results = self.memory_manager.search(query=query, user_id=self.user_id, session_id=self.session_id1)
        
        # 3. Verify the results
        self.assertGreater(len(search_results), 0, "Should find session memory")
        found_match = any("blue" in result.get('memory', '').lower() for result in search_results)
        self.assertTrue(found_match, "Should find session memory about blue")

        # 4. Search without session filter or with different session should not find it (depending on impl)
        search_results_no_session = self.memory_manager.search(query=query, user_id=self.user_id, session_id="different")
        self.assertEqual(len(search_results_no_session), 0, "Should not find in different session")

    def test_03_add_and_search_long_term_memory(self):
        """Test adding to and searching long-term memory (no session)."""
        # 1. Add long-term data (without session_id)
        messages_to_add = [
            {"role": "user", "content": "My long-term favorite food is pizza."},
            {"role": "assistant", "content": "Remembered your preference for pizza."}
        ]
        # Add without session_id - modify add to allow None session_id
        self.memory_manager.add(messages_to_add, user_id=self.user_id, session_id=None, infer=True)  # Assuming code allows None
        
        # 2. Search without session filter
        query = "What is my favorite food?"
        search_results = self.memory_manager.search(query=query, user_id=self.user_id, session_id=None)  # None for long-term
        
        # 3. Verify
        self.assertGreater(len(search_results), 0, "Should find long-term memory")
        found_match = any("pizza" in result.get('memory', '').lower() for result in search_results)
        self.assertTrue(found_match, "Should find long-term memory about pizza")

    def test_04_clear_session_does_not_affect_long_term(self):
        """Test clearing session memory doesn't affect long-term."""
        # Add session and long-term
        self.test_02_add_and_search_session_memory()
        self.test_03_add_and_search_long_term_memory()
        
        # Clear session
        self.memory_manager.clear_session(user_id=self.user_id, session_id=self.session_id1)
        
        # Session search should be empty
        search_results_session = self.memory_manager.search("favorite color", self.user_id, self.session_id1)
        self.assertEqual(len(search_results_session), 0, "Session memory should be cleared")
        
        # Long-term should still be there
        search_results_long = self.memory_manager.search("favorite food", self.user_id, None)
        self.assertGreater(len(search_results_long), 0, "Long-term memory should remain")

    def test_05_multiple_sessions(self):
        """Test memories in different sessions are isolated."""
        # Add to session1
        messages1 = [{"role": "user", "content": "I like apples in session1."}]
        self.memory_manager.add(messages1, self.user_id, self.session_id1, infer=False)
        
        # Add to session2
        messages2 = [{"role": "user", "content": "I like bananas in session2."}]
        self.memory_manager.add(messages2, self.user_id, self.session_id2, infer=False)
        
        # Search session1
        results1 = self.memory_manager.search("like", self.user_id, self.session_id1)
        self.assertTrue(any("apples" in r['memory'].lower() for r in results1))
        self.assertFalse(any("bananas" in r['memory'].lower() for r in results1))
        
        # Search session2
        results2 = self.memory_manager.search("like", self.user_id, self.session_id2)
        self.assertTrue(any("bananas" in r['memory'].lower() for r in results2))
        self.assertFalse(any("apples" in r['memory'].lower() for r in results2))

if __name__ == '__main__':
    print("Running MemoryManager tests...")
    print("Ollama will be automatically started if needed.")
    print("Note: First run will download the embedding model (~274MB).")
    unittest.main()
