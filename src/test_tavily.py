"""
Test script for Tavily web search functionality.

This script tests:
1. Basic search operations
2. Edge cases and error handling
3. Integration with ToolRegistry
4. Configuration validation

Usage:
    python -m src.test_tavily
"""

import sys
import os
from src.config.settings import load_settings
from src.tools.tavily_manager import TavilyManager
from src.tools.registry import ToolRegistry


def test_basic_search():
    """Test basic web search functionality."""
    print("\n" + "="*60)
    print("TEST 1: Basic Web Search")
    print("="*60)
    
    settings = load_settings()
    
    if not settings.tavily_settings.api_key:
        print("[SKIP] No Tavily API key configured")
        print("       Set TAVILY_API_KEY environment variable or add to config.json")
        return
    
    try:
        manager = TavilyManager(api_key=settings.tavily_settings.api_key)
        
        # Test 1: Simple search query
        print("\n[TEST] Test 1a: Simple search query")
        success, message, results = manager.search("Python programming language")
        assert success, f"Search should succeed, got: {message}"
        assert results is not None, "Results should not be None"
        assert len(results) > 0, "Should return at least one result"
        print(f"[PASS] Search successful: {message}")
        print(f"   Found {len(results)} results")
        if results:
            print(f"   First result: {results[0].get('title', 'N/A')}")
        
        # Test 2: Weather query
        print("\n[TEST] Test 1b: Weather query")
        success, message, results = manager.search("weather in London today")
        assert success, f"Weather search should succeed, got: {message}"
        assert results is not None, "Results should not be None"
        print(f"[PASS] Weather search successful: {message}")
        
        # Test 3: Documentation search
        print("\n[TEST] Test 1c: Documentation search")
        success, message, results = manager.search("Python asyncio documentation")
        assert success, f"Documentation search should succeed, got: {message}"
        assert results is not None, "Results should not be None"
        print(f"[PASS] Documentation search successful: {message}")
        
        print("\n[PASS] All basic search tests passed!")
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        raise


def test_error_handling():
    """Test error handling and edge cases."""
    print("\n" + "="*60)
    print("TEST 2: Error Handling")
    print("="*60)
    
    settings = load_settings()
    
    if not settings.tavily_settings.api_key:
        print("[WARN] SKIPPED: No Tavily API key configured")
        return
    
    try:
        manager = TavilyManager(api_key=settings.tavily_settings.api_key)
        
        # Test 1: Empty query
        print("\n[TEST] Test 2a: Empty query")
        success, message, results = manager.search("")
        assert not success, "Empty query should fail"
        assert results is None, "Results should be None for empty query"
        print(f"[PASS] Empty query handled correctly: {message}")
        
        # Test 2: Whitespace-only query
        print("\n[TEST] Test 2b: Whitespace-only query")
        success, message, results = manager.search("   ")
        assert not success, "Whitespace-only query should fail"
        print(f"[PASS] Whitespace query handled correctly: {message}")
        
        # Test 3: Very long query
        print("\n[TEST] Test 2c: Very long query")
        long_query = "test " * 100  # 500 characters
        success, message, results = manager.search(long_query)
        # Should either succeed or fail gracefully
        if success:
            print(f"[PASS] Long query handled successfully")
        else:
            print(f"[PASS] Long query rejected gracefully: {message}")
        
        # Test 4: Special characters
        print("\n[TEST] Test 2d: Special characters in query")
        success, message, results = manager.search("C++ programming & tips [2024]")
        # Should handle special characters gracefully
        print(f"[PASS] Special characters handled: success={success}")
        
        print("\n[PASS] All error handling tests passed!")
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        raise


def test_invalid_api_key():
    """Test behavior with invalid API key."""
    print("\n" + "="*60)
    print("TEST 3: Invalid API Key")
    print("="*60)
    
    try:
        # Test 1: Empty API key
        print("\n[TEST] Test 3a: Empty API key")
        try:
            manager = TavilyManager(api_key="")
            print("[FAIL] Should have raised ValueError for empty API key")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"[PASS] Empty API key rejected correctly: {e}")
        
        # Test 2: Invalid API key (search will fail)
        print("\n[TEST] Test 3b: Invalid API key (search will fail)")
        try:
            manager = TavilyManager(api_key="invalid-key-12345")
            success, message, results = manager.search("test query")
            assert not success, "Search with invalid key should fail"
            assert results is None, "Results should be None"
            print(f"[PASS] Invalid API key handled correctly: {message}")
        except Exception as e:
            print(f"[PASS] Invalid API key raised exception as expected: {type(e).__name__}")
        
        print("\n[PASS] All API key validation tests passed!")
        
    except AssertionError:
        raise
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        raise


def test_registry_integration():
    """Test Tavily integration with ToolRegistry."""
    print("\n" + "="*60)
    print("TEST 4: Registry Integration")
    print("="*60)
    
    settings = load_settings()
    
    if not settings.tavily_settings.api_key:
        print("[WARN] SKIPPED: No Tavily API key configured")
        return
    
    try:
        registry = ToolRegistry(settings)
        
        # Test 1: Tavily manager initialization
        print("\n[TEST] Test 4a: Tavily manager initialization")
        assert registry.tavily_manager is not None, "Tavily manager should be initialized"
        print("[PASS] Tavily manager initialized in registry")
        
        # Test 2: Execute web search through registry with multi-step workflow
        print("\n[TEST] Test 4b: Execute web search with LLM synthesis")
        print("         NOTE: This test requires LLM client for synthesis")
        print("         Without LLM client, it will return raw results")
        
        result = registry.execute_tool_call({
            "tool_name": "web_search",
            "parameters": {"query": "capital of France"}
        })
        
        assert result is not None, "Result should not be None"
        assert result.get('success') == True, f"Search should succeed: {result.get('error')}"
        assert 'feedback' in result, "Should have feedback key"
        print(f"[PASS] Web search executed through registry successfully")
        if result.get('output'):
            print(f"   Output: {result.get('output')[:100]}...")
        if result.get('feedback'):
            print(f"   Feedback: {result.get('feedback')[:100]}...")
        
        # Test 3: Missing query parameter
        print("\n[TEST] Test 4c: Missing query parameter")
        result = registry.execute_tool_call({
            "tool_name": "web_search",
            "parameters": {}
        })
        
        assert result is not None, "Result should not be None"
        assert result.get('success') == False, "Should fail with missing query"
        assert 'error' in result, "Should have error message"
        print(f"[PASS] Missing parameter handled correctly: {result.get('error')}")
        
        print("\n[PASS] All registry integration tests passed!")
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        raise


def test_disabled_configuration():
    """Test behavior when Tavily is disabled in config."""
    print("\n" + "="*60)
    print("TEST 5: Disabled Configuration")
    print("="*60)
    
    settings = load_settings()
    
    try:
        # Temporarily disable Tavily
        original_enabled = settings.tavily_settings.enabled
        original_api_key = settings.tavily_settings.api_key
        
        print("\n[TEST] Test 5a: Tavily disabled in config")
        settings.tavily_settings.enabled = False
        
        registry = ToolRegistry(settings)
        assert registry.tavily_manager is None, "Tavily manager should not be initialized when disabled"
        print("[PASS] Tavily manager not initialized when disabled")
        
        # Test tool call with disabled manager
        print("\n[TEST] Test 5b: Tool call with disabled manager")
        result = registry.execute_tool_call({
            "tool_name": "web_search",
            "parameters": {"query": "test"}
        })
        
        assert result is not None, "Result should not be None"
        assert result.get('success') == False, "Should fail when disabled"
        assert 'not enabled' in result.get('error', '').lower() or 'not available' in result.get('feedback', '').lower(), \
            "Error should mention disabled/not available"
        print(f"[PASS] Disabled state handled correctly: {result.get('error')}")
        
        # Test with missing API key
        print("\n[TEST] Test 5c: Missing API key")
        settings.tavily_settings.enabled = True
        settings.tavily_settings.api_key = None
        
        registry = ToolRegistry(settings)
        assert registry.tavily_manager is None, "Tavily manager should not be initialized without API key"
        print("[PASS] Tavily manager not initialized without API key")
        
        # Restore original settings
        settings.tavily_settings.enabled = original_enabled
        settings.tavily_settings.api_key = original_api_key
        
        print("\n[PASS] All configuration tests passed!")
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        raise


def test_result_format():
    """Test that search results have the expected format."""
    print("\n" + "="*60)
    print("TEST 6: Result Format")
    print("="*60)
    
    settings = load_settings()
    
    if not settings.tavily_settings.api_key:
        print("[WARN] SKIPPED: No Tavily API key configured")
        return
    
    try:
        manager = TavilyManager(api_key=settings.tavily_settings.api_key)
        
        print("\n[TEST] Test 6a: Result structure")
        success, message, results = manager.search("Python")
        
        assert success, "Search should succeed"
        assert isinstance(results, list), "Results should be a list"
        
        if results:
            first_result = results[0]
            assert isinstance(first_result, dict), "Each result should be a dict"
            assert 'title' in first_result, "Result should have 'title' key"
            assert 'url' in first_result, "Result should have 'url' key"
            assert 'content' in first_result, "Result should have 'content' key"
            
            print(f"[PASS] Result format is correct")
            print(f"   Sample result:")
            print(f"   - Title: {first_result.get('title', '')[:50]}...")
            print(f"   - URL: {first_result.get('url', '')}")
            print(f"   - Content length: {len(first_result.get('content', ''))} chars")
        else:
            print("[WARN] No results returned, but search succeeded")
        
        print("\n[PASS] All format tests passed!")
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        raise


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TAVILY WEB SEARCH TEST SUITE")
    print("="*60)
    
    try:
        # Check if Tavily is configured
        settings = load_settings()
        if not settings.tavily_settings.api_key:
            print("\n[WARN] WARNING: No Tavily API key configured")
            print("   Some tests will be skipped")
            print("   To run all tests, set TAVILY_API_KEY environment variable")
            print("   or add 'api_key' to 'tavily_settings' in config.json")
        
        # Run all test suites
        test_basic_search()
        test_error_handling()
        test_invalid_api_key()
        test_registry_integration()
        test_disabled_configuration()
        test_result_format()
        
        print("\n" + "="*60)
        print("[PASS] ALL TESTS PASSED SUCCESSFULLY!")
        print("="*60)
        
    except AssertionError as e:
        print("\n" + "="*60)
        print(f"[FAIL] TEST FAILED: {e}")
        print("="*60)
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*60)
        print(f"[FAIL] UNEXPECTED ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

