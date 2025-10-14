"""
Tavily Web Search Manager

This module handles:
1. Web search using Tavily API
2. Formatting search results for LLM consumption
3. Error handling for API failures
"""

from typing import Dict, Any, Optional, List, Tuple
from src.utils.logger import app_logger


class TavilyManager:
    """Manager for Tavily web search operations."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Tavily manager.
        
        Args:
            api_key: Tavily API key
        """
        if not api_key:
            raise ValueError("Tavily API key is required")
        
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=api_key)
            app_logger.info("TavilyManager initialized successfully")
        except ImportError:
            app_logger.error("tavily-python package not installed. Run: pip install tavily-python")
            raise
        except Exception as e:
            app_logger.error(f"Failed to initialize Tavily client: {e}")
            raise
    
    def search(self, query: str) -> Tuple[bool, str, Optional[List[Dict[str, Any]]]]:
        """
        Perform a web search using Tavily.
        
        Args:
            query: The search query
            
        Returns:
            Tuple of (success, message, search_results)
            - success: True if search succeeded
            - message: Human-readable message about the search
            - search_results: List of result dictionaries with 'title', 'url', 'content'
        """
        if not query or not query.strip():
            app_logger.warning("Empty search query provided")
            return False, "Search query cannot be empty", None
        
        try:
            app_logger.info(f"Performing web search for: {query}")
            
            # Perform the search using Tavily
            response = self.client.search(query)
            
            # Extract results
            results = response.get('results', [])
            
            if not results:
                app_logger.info(f"No results found for query: {query}")
                return True, "No results found", []
            
            # Format results for LLM consumption
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', '')
                })
            
            app_logger.info(f"Found {len(formatted_results)} results for query: {query}")
            return True, f"Found {len(formatted_results)} results", formatted_results
            
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            app_logger.error(f"Tavily search error for query '{query}': {e}", exc_info=True)
            return False, error_msg, None

