from mem0 import Memory
from typing import List, Dict, Any, Optional
from ..config.settings import Mem0Config
from ..utils.logger import app_logger
import os

class MemoryManager:
    def __init__(self, config: Optional[Mem0Config]):
        self.enabled = bool(config and config.enabled)
        if self.enabled and config:
            try:
                # Convert Pydantic config to dict for mem0, using model_dump for Pydantic v2
                if hasattr(config, 'model_dump'):
                    mem0_config_dict = config.model_dump(exclude_unset=True)
                else:
                    mem0_config_dict = config.dict(exclude_unset=True)

                # Handle data path specifically for the vector store
                # Always honor the configured default, even if excluded by model_dump(exclude_unset=True)
                data_path = getattr(config, 'data_path', None) or mem0_config_dict.pop("data_path", None)
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


                self.mem0 = Memory.from_config(mem0_config_dict)
                app_logger.info("MemoryManager initialized successfully with mem0.")
            except Exception as e:
                app_logger.error("Failed to initialize mem0 from config: {}", e, exc_info=True)
                app_logger.warning("Disabling MemoryManager due to initialization error.")
                self.enabled = False
        else:
            self.mem0 = None
            app_logger.info("MemoryManager is disabled.")

    def add(self, messages: List[Dict[str, Any]], user_id: str, session_id: Optional[str] = None, infer: bool = True):
        if not self.enabled:
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
        except Exception as e:
            app_logger.error("Failed to add memory for user '{}': {}", user_id, e, exc_info=True)

    def search(self, query: str, user_id: str, session_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
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
