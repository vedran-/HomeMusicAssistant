from mem0 import Memory
from typing import List, Dict, Any, Optional
from ..config.settings import Mem0Config, AppSettings
from ..utils.logger import app_logger
from ..utils.ollama_manager import OllamaManager
import os

class MemoryManager:
    def __init__(self, config: Optional[Mem0Config], app_settings: Optional[AppSettings] = None, ollama_manager: Optional[OllamaManager] = None):
        """Initialize MemoryManager.

        If app_settings.memory_config is provided (from config.json), build a mem0 config from it.
        Otherwise, fall back to provided Mem0Config (if any).
        
        Args:
            config: Mem0Config object (legacy)
            app_settings: AppSettings with memory_config
            ollama_manager: OllamaManager for automatic Ollama lifecycle management
        """
        self.ollama_manager = ollama_manager
        # Build mem0_config_dict either from simplified memory_config or from Mem0Config
        mem0_config_dict: Optional[Dict[str, Any]] = None
        if app_settings and getattr(app_settings, 'memory_config', None):
            mc = app_settings.memory_config
            # Compose mem0 configuration structure expected by mem0 OSS
            mem0_config_dict = {
                "llm": {
                    "provider": mc.llm_provider or "litellm",
                    "config": {
                        "model": mc.llm_model or (app_settings.litellm_settings.model if app_settings and app_settings.litellm_settings else None),
                        # mem0's litellm integration relies on environment variable for some providers; keep api_key for completeness
                        "api_key": mc.llm_api_key or app_settings.litellm_settings.api_key if app_settings and app_settings.litellm_settings else None,
                    }
                },
                "embedder": {
                    "provider": mc.embedder_provider or "lmstudio",
                    "config": self._build_embedder_config(mc.embedder_provider or "lmstudio", mc.embedder_model, mc.embedder_api_key, app_settings)
                },
                "vector_store": {
                    "provider": mc.vector_store_provider or "qdrant",
                    "config": {
                        "embedding_model_dims": mc.vector_store_embedding_model_dims or 768
                    }
                }
            }
            # Determine enabled flag
            self.enabled = True
            data_path = mc.data_path
        else:
            self.enabled = bool(config and config.enabled)
            data_path = getattr(config, 'data_path', None) if config else None
            if config:
                # Convert Pydantic config to dict
                if hasattr(config, 'model_dump'):
                    mem0_config_dict = config.model_dump(exclude_unset=True)
                else:
                    mem0_config_dict = config.dict(exclude_unset=True)

        # Initialize mem0 using the composed configuration
        if self.enabled and mem0_config_dict:
            try:
                # Handle data path specifically for the vector store
                # Always honor the configured default, even if excluded by model_dump(exclude_unset=True)
                if data_path:
                    abs_data_path = os.path.abspath(data_path)
                    # Ensure directory exists to avoid provider creating a new relative path elsewhere
                    try:
                        os.makedirs(abs_data_path, exist_ok=True)
                    except Exception:
                        pass
                    # mem0 expects the path inside the vector_store config
                    if 'vector_store' not in mem0_config_dict:
                        mem0_config_dict['vector_store'] = {"provider": "qdrant", "config": {}}
                    
                    if 'config' not in mem0_config_dict['vector_store']:
                        mem0_config_dict['vector_store']['config'] = {}
                        
                    mem0_config_dict['vector_store']['config']['path'] = abs_data_path
                    app_logger.info(f"MemoryManager using custom data path: {abs_data_path}")
                else:
                    # Log the default path for user visibility
                    default_path = os.path.join(os.path.expanduser("~"), ".mem0")
                    app_logger.info(f"MemoryManager using default data path: {default_path}")

                # Extra diagnostics for embedder config
                embedder_provider = mem0_config_dict.get('embedder', {}).get('provider')
                app_logger.info(f"Mem0 embedder provider: {embedder_provider}")
                if embedder_provider == 'gemini':
                    app_logger.info(f"GOOGLE_API_KEY present: {bool(os.getenv('GOOGLE_API_KEY'))}")
                # Initialize mem0
                self.mem0 = Memory.from_config(mem0_config_dict)
                app_logger.info("MemoryManager initialized successfully with mem0.")
            except Exception as e:
                app_logger.error("Failed to initialize mem0 from config: {}", e, exc_info=True)
                # If Gemini import failed, fall back to lmstudio embedder automatically
                if 'cannot import name' in str(e).lower() and 'genai' in str(e).lower():
                    try:
                        app_logger.warning("Gemini embedder initialization failed. Falling back to 'lmstudio' embedder.")
                        mem0_config_dict['embedder'] = {
                            'provider': 'lmstudio',
                            'config': {
                                # Defaults are acceptable; LM Studio server should be available if used
                            }
                        }
                        self.mem0 = Memory.from_config(mem0_config_dict)
                        app_logger.info("MemoryManager initialized with fallback 'lmstudio' embedder.")
                    except Exception as fe:
                        app_logger.error("Fallback to 'lmstudio' embedder also failed: {}", fe, exc_info=True)
                        app_logger.warning("Disabling MemoryManager due to initialization error.")
                        self.enabled = False
                        self.mem0 = None
                else:
                    app_logger.warning("Disabling MemoryManager due to initialization error.")
                    self.enabled = False
                    self.mem0 = None
        else:
            self.mem0 = None
            app_logger.info("MemoryManager is disabled.")

    def _build_embedder_config(self, provider: str, model: str, api_key: str, app_settings) -> Dict[str, Any]:
        """Build embedder configuration based on provider type."""
        if provider == "ollama":
            # Ollama embedder config - model is passed differently
            return {"model": model}
        elif provider == "gemini":
            # Gemini embedder config
            return {
                "model": model,
                "api_key": api_key or (app_settings.google_api_key if app_settings else None)
            }
        elif provider == "openai":
            # OpenAI embedder config
            return {
                "model": model,
                "api_key": api_key
            }
        elif provider == "huggingface":
            # HuggingFace embedder config
            return {"model": model}
        elif provider == "lmstudio":
            # LMStudio embedder config (minimal config needed)
            return {}
        else:
            # Default/fallback config
            return {"model": model}

    def add(self, messages: List[Dict[str, Any]], user_id: str, session_id: Optional[str] = None, infer: bool = True):
        if not self.enabled:
            return

        # Ensure Ollama is running before memory operations
        if self.ollama_manager:
            try:
                self.ollama_manager.ensure_running()
            except Exception as e:
                app_logger.error(f"Failed to start Ollama for memory operation: {e}")
                return

        try:
            metadata: Dict[str, Any] = {"type": "long_term"}
            if session_id:
                metadata = {"type": "session", "session_id": session_id}

            # Normalize payload: send only plain user texts to mem0 per OSS quickstart
            user_texts: List[str] = []
            for msg in messages or []:
                if not isinstance(msg, dict):
                    continue
                role = msg.get('role')
                content = msg.get('content')
                if role == 'user' and isinstance(content, str):
                    user_texts.append(content)
            if not user_texts:
                # As a fallback, take any string-like content from input
                for msg in messages or []:
                    if isinstance(msg, dict) and isinstance(msg.get('content'), str):
                        user_texts.append(msg['content'])
            clean_messages = [{"role": "user", "content": t} for t in user_texts]

            app_logger.debug(f"Adding to memory for user '{user_id}': {clean_messages}")
            add_return = self.mem0.add(messages=clean_messages, user_id=user_id, metadata=metadata, infer=infer)
            app_logger.info(f"Add returned: {add_return}")
            if session_id:
                verify_payload = self.mem0.get_all(user_id=user_id, filters={'session_id': session_id})
            else:
                # Call without filters for long-term verification (OSS API)
                verify_payload = self.mem0.get_all(user_id=user_id)
            app_logger.info(f"Successfully added memory for user '{user_id}' {'in session ' + session_id if session_id else 'as long-term'}. Response: {verify_payload}")
            app_logger.debug(f"Added conversation to memory for user '{user_id}' {'in session ' + session_id if session_id else 'as long-term'}.")
            
            # Mark activity after successful memory operation
            if self.ollama_manager:
                self.ollama_manager.mark_activity()
        except Exception as e:
            app_logger.error("Failed to add memory for user '{}': {}", user_id, e, exc_info=True)

    def search(self, query: str, user_id: str, session_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        
        # Ensure Ollama is running before memory operations
        if self.ollama_manager:
            try:
                self.ollama_manager.ensure_running()
            except Exception as e:
                app_logger.error(f"Failed to start Ollama for memory search: {e}")
                return []
            
        try:
            # For robust recall of long-term facts across restarts, perform a global search
            # regardless of the current session. Short-term context is now handled in-memory.
            # Align with OSS API: pass user_id and limit; avoid filters unless needed
            global_memories = self.mem0.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            app_logger.info(f"Raw search results for query '{query}': {global_memories}")
            app_logger.debug(f"Found {len(global_memories.get('results', []))} long-term memories for user '{user_id}'.")
            if global_memories.get('results'):
                app_logger.debug(f"Retrieved memories: {global_memories['results']}")
            results = [r for r in global_memories.get('results', []) if r.get('score', 0) > 0.3]

            # Fallback: if vector search returns nothing (e.g., embedder unavailable),
            # perform a simple keyword match over all stored memories
            if not results:
                try:
                    all_memories = self.mem0.get_all(user_id=user_id)
                    items = all_memories.get('results', []) if isinstance(all_memories, dict) else all_memories
                    q = query.lower()
                    scored = []
                    for item in items:
                        text = item.get('memory', '') or item.get('content', '')
                        if not text:
                            continue
                        t = text.lower()
                        score = 0
                        if q in t:
                            score = 1.0
                        else:
                            # naive token overlap
                            q_tokens = set(q.split())
                            t_tokens = set(t.split())
                            overlap = len(q_tokens & t_tokens)
                            score = overlap / max(1, len(q_tokens))
                        if score > 0:
                            scored.append({**item, 'score': score})
                    scored.sort(key=lambda x: x.get('score', 0), reverse=True)
                    results = scored[:limit]
                    app_logger.info(f"Fallback get_all search returned {len(results)} items for query '{query}'.")
                except Exception as fe:
                    app_logger.warning(f"Fallback memory scan failed: {fe}")

            # Mark activity after successful search
            if self.ollama_manager and results:
                self.ollama_manager.mark_activity()
                
            return results
        except Exception as e:
            app_logger.error("Failed to search memory for user '{}': {}", user_id, e, exc_info=True)
            return []

    def clear_session(self, user_id: str, session_id: str):
        if not self.enabled or not session_id:
            return

        try:
            memories_to_delete = self.mem0.search(
                query="", 
                user_id=user_id,
                limit=1000,
                filters={"session_id": session_id}
            )
            
            deleted_count = 0
            for mem in memories_to_delete.get('results', []):
                if 'id' in mem:
                    self.mem0.delete(memory_id=mem['id'])
                    deleted_count += 1
            
            if deleted_count > 0:
                app_logger.info(f"Cleared {deleted_count} memories for user '{user_id}' in session '{session_id}'.")
            else:
                app_logger.info(f"No memories found to clear for user '{user_id}' in session '{session_id}'.")
        except Exception as e:
            app_logger.error("Failed to clear session memories for user '{}': {}", user_id, e, exc_info=True)
    
    def close(self):
        """Close any open resources, like database connections."""
        if not self.enabled or not self.mem0:
            return
        
        try:
            if hasattr(self.mem0.vector_store, 'close'):
                self.mem0.vector_store.close()
                app_logger.info("Closed mem0 vector store connection.")
        except Exception as e:
            app_logger.error(f"Failed to close mem0 vector store: {e}", exc_info=True)
        
        # Stop Ollama manager if present
        if self.ollama_manager:
            try:
                self.ollama_manager.stop()
            except Exception as e:
                app_logger.error(f"Failed to stop Ollama manager: {e}", exc_info=True)
