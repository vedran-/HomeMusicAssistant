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
    
    def __init__(self, api_key: str, llm_client=None):
        """
        Initialize the Tavily manager.
        
        Args:
            api_key: Tavily API key
            llm_client: LiteLLMClient instance for multi-step processing (can be None, injected later)
        """
        if not api_key:
            raise ValueError("Tavily API key is required")
        
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=api_key)
            self.llm_client = llm_client  # Can be None initially, injected later
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
    
    def search_and_answer(self, query: str, user_question: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Multi-step agentic workflow:
        1. Perform web search
        2. Get search results
        3. Call LLM to synthesize answer from results
        4. Return synthesized answer
        
        This demonstrates the reusable multi-step pattern!
        
        Args:
            query: The search query
            user_question: The original user question (if different from query)
            
        Returns:
            Tuple of (success, message, synthesized_answer)
        """
        # Step 1: Perform the search
        success, message, results = self.search(query)
        
        if not success:
            return False, message, None
        
        if not results:
            return True, "No results found", "I couldn't find any information about that."
        
        # Step 2: Format results for LLM
        app_logger.info(f"Formatting {len(results)} search results for LLM synthesis...")
        
        results_text = ""
        for i, result in enumerate(results[:5], 1):  # Use top 5 results
            title = result.get('title', 'N/A')
            content = result.get('content', 'N/A')
            url = result.get('url', 'N/A')
            results_text += f"\n{i}. {title}\n   {content}\n   Source: {url}\n"
        
        # Step 3: Call LLM to synthesize answer
        if not self.llm_client:
            # No LLM client available, return first result content
            app_logger.warning("No LLM client available for synthesis. Returning first result.")
            first_content = results[0].get('content', 'No content available')
            return True, message, first_content[:500]
        
        app_logger.info("Calling LLM to synthesize answer from search results...")
        
        question_to_answer = user_question or query
        
        llm_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions based on web search results. Provide concise, accurate answers in 1-3 sentences."
            },
            {
                "role": "user",
                "content": f"""Here are web search results:

{results_text}

User's question: {question_to_answer}

Please answer their question based on the search results. Be concise (1-3 sentences) and factual."""
            }
        ]
        
        answer = self.llm_client.get_completion(llm_messages, temperature=0.3, max_tokens=300)
        
        if not answer:
            # LLM failed, fallback to first result
            app_logger.warning("LLM completion failed. Falling back to first result.")
            first_content = results[0].get('content', 'No content available')
            return True, message, first_content[:500]
        
        app_logger.info(f"Multi-step workflow complete. Answer: {len(answer)} characters")
        
        return True, message, answer

