"""
YouTube Music Controller using YouTube Music Server API

This module provides a wrapper around the YouTube Music Server API
for controlling music playback, searching for music, and other music-related operations.
"""

import logging
import json
import requests
from typing import Dict, Any, Optional, List
import os
import time
import subprocess
import os # Keep os for path manipulation if not already present for it
from .utils import run_ahk_script
from src.config.settings import AppSettings

logger = logging.getLogger(__name__)

class YouTubeMusicAPIController:
    """Controller for YouTube Music using the YouTube Music Server API."""
    
    def __init__(self, settings: AppSettings, host: str = "localhost", port: int = 26538):
        """Initialize the controller with the server host and port."""
        self.settings = settings
        self.base_url = f"http://{host}:{port}/api/v1"
        logger.info(f"Initialized YouTube Music API controller with base URL: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the YouTube Music API server.
        
        Args:
            method: HTTP method to use (GET, POST, etc.)
            endpoint: API endpoint to call
            data: Optional JSON data to send with the request
            
        Returns:
            Response from the API server as a dictionary
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        try:
            response = None
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data if data else {})
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data if data else {})
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, json=data if data else {})
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # If response has no content (204)
            if response.status_code == 204:
                return {"success": True}
            
            # Otherwise parse JSON response
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"success": False, "error": str(e)}
    
    # === Music Playback Controls ===
    
    def play(self) -> Dict[str, Any]:
        """Start or resume playback."""
        return self._make_request("POST", "play")
    
    def pause(self) -> Dict[str, Any]:
        """Pause playback."""
        return self._make_request("POST", "pause")
    
    def toggle_playback(self) -> Dict[str, Any]:
        """Toggle between play and pause."""
        return self._make_request("POST", "toggle-play")
    
    def next(self, count: int = 1) -> Dict[str, Any]:
        """
        Skip to the next song.
        
        Args:
            count: Number of songs to skip forward
            
        Returns:
            API response
        """
        result = {"success": True}
        
        # Make multiple next requests if count > 1
        for _ in range(count):
            current_result = self._make_request("POST", "next")
            if not current_result.get("success", False):
                result = current_result
                break
        
        return result
    
    def previous(self, count: int = 1) -> Dict[str, Any]:
        """
        Go to the previous song.
        
        Args:
            count: Number of songs to skip backward
            
        Returns:
            API response
        """
        result = {"success": True}
        
        # Make multiple previous requests if count > 1
        for _ in range(count):
            current_result = self._make_request("POST", "previous")
            if not current_result.get("success", False):
                result = current_result
                break
        
        return result
    
    # === Time Navigation Controls ===
    
    def forward(self, seconds: int = 10) -> Dict[str, Any]:
        """
        Skip forward in the current song.
        
        Args:
            seconds: Number of seconds to skip forward
            
        Returns:
            API response
        """
        return self._make_request("POST", "go-forward", {"seconds": seconds})
    
    def rewind(self, seconds: int = 10) -> Dict[str, Any]:
        """
        Skip backward in the current song.
        
        Args:
            seconds: Number of seconds to skip backward
            
        Returns:
            API response
        """
        return self._make_request("POST", "go-back", {"seconds": seconds})
    
    def seek_to(self, seconds: int) -> Dict[str, Any]:
        """
        Seek to a specific position in the current song.
        
        Args:
            seconds: Position in seconds to seek to
            
        Returns:
            API response
        """
        return self._make_request("POST", "seek-to", {"seconds": seconds})
    
    # === Volume Controls ===
    
    def set_volume(self, volume: int) -> Dict[str, Any]:
        """
        Set the volume.
        
        Args:
            volume: Volume level (0-100)
            
        Returns:
            API response
        """
        # Ensure volume is within valid range (0-100)
        volume = max(0, min(100, volume))
        return self._make_request("POST", "volume", {"volume": volume})
    
    def get_volume(self) -> Optional[int]:
        """
        Get the current volume level.
        
        Returns:
            Current volume (0-100) or None if request failed
        """
        response = self._make_request("GET", "volume")
        if response.get("success", True) and "state" in response:
            return response["state"]
        return None
    
    def volume_up(self, amount: int = 10) -> Dict[str, Any]:
        """
        Increase the volume.
        
        Args:
            amount: Amount to increase the volume by
            
        Returns:
            API response with new volume level
        """
        current_volume = self.get_volume()
        if current_volume is not None:
            new_volume = min(100, current_volume + amount)
            result = self.set_volume(new_volume)
            result["new_volume"] = new_volume
            return result
        return {"success": False, "error": "Failed to get current volume"}
    
    def volume_down(self, amount: int = 10) -> Dict[str, Any]:
        """
        Decrease the volume.
        
        Args:
            amount: Amount to decrease the volume by
            
        Returns:
            API response with new volume level
        """
        current_volume = self.get_volume()
        if current_volume is not None:
            new_volume = max(0, current_volume - amount)
            result = self.set_volume(new_volume)
            result["new_volume"] = new_volume
            return result
        return {"success": False, "error": "Failed to get current volume"}
    
    def toggle_mute(self) -> Dict[str, Any]:
        """Toggle mute state."""
        return self._make_request("POST", "toggle-mute")
    
    # === Song Interaction Controls ===
    
    def like(self) -> Dict[str, Any]:
        """Like the current song."""
        return self._make_request("POST", "like")
    
    def dislike(self) -> Dict[str, Any]:
        """Dislike the current song."""
        return self._make_request("POST", "dislike")
    
    # === Playlist Controls ===
    
    def toggle_shuffle(self) -> Dict[str, Any]:
        """Toggle shuffle mode."""
        return self._make_request("POST", "shuffle")
    
    def get_shuffle_state(self) -> Optional[bool]:
        """
        Get the current shuffle state.
        
        Returns:
            True if shuffle is enabled, False if disabled, None if request failed
        """
        response = self._make_request("GET", "shuffle")
        if response.get("success", True) and "state" in response:
            return response["state"]
        return None
    
    def toggle_repeat(self, iterations: int = 1) -> Dict[str, Any]:
        """
        Toggle repeat mode.
        
        Args:
            iterations: Number of times to toggle the repeat mode
                       (YouTube Music cycles through: no repeat → repeat all → repeat one)
                       
        Returns:
            API response
        """
        return self._make_request("POST", "switch-repeat", {"iteration": iterations})
    
    def get_repeat_mode(self) -> Optional[str]:
        """
        Get the current repeat mode.
        
        Returns:
            Repeat mode ("NONE", "ALL", "ONE") or None if request failed
        """
        response = self._make_request("GET", "repeat-mode")
        if response.get("success", True) and "mode" in response:
            return response["mode"]
        return None
    
    # === Queue Management ===
    
    def get_queue(self) -> Optional[Dict[str, Any]]:
        """
        Get the current queue information.
        
        Returns:
            Queue information or None if request failed
        """
        response = self._make_request("GET", "queue")
        if response.get("success", True) and not isinstance(response, dict):
            return response
        return None
    
    def clear_queue(self) -> Dict[str, Any]:
        """Clear the queue."""
        return self._make_request("DELETE", "queue")
    
    def add_to_queue(self, video_id: str) -> Dict[str, Any]:
        """
        Add a song to the end of the queue.
        The API defaults to inserting at the end if 'insertPosition' is not provided.

        Args:
            video_id: YouTube video ID to add
            
        Returns:
            API response
        """
        data = {"videoId": video_id}
        # By not specifying 'insertPosition', we rely on the API's default
        # behavior, which is 'INSERT_AT_END' according to AddSongToQueueSchema.
        return self._make_request("POST", "queue", data)
    
    # === Current Song Information ===
    
    def get_current_song(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently playing song.
        
        Returns:
            Song information or None if request failed
        """
        response = self._make_request("GET", "song")
        if response.get("success", True) and not isinstance(response, dict):
            return response
        return None
    
    # === Search ===
    
    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for music and return results.
        
        Args:
            query: Search query
            
        Returns:
            Search results or None if request failed
        """
        response = self._make_request("POST", "search", {"query": query})
        if response.get("success", True):
            return response
        return None
    
    def set_queue_index(self, index: int) -> Dict[str, Any]:
        """
        Set the current playing song in the queue by its index.
        Uses PATCH /api/v1/queue with body {'index': index}.

        Args:
            index: The 0-based index in the queue to set.
            
        Returns:
            Result of the operation.
        """
        try:
            # API definition: PATCH /api/v1/queue with body {'index': index}
            response = self._make_request("PATCH", "queue", {"index": index})
            
            # A successful call to set-index usually returns a 204 No Content.
            # self._make_request returns {"success": True} for 204.
            if response and response.get("success"):
                logger.info(f"Successfully set queue index to {index} via PATCH /api/v1/queue")
                return {"success": True, "message": f"Queue index set to {index}"}
            else:
                error_message = response.get('error', 'Unknown error while setting queue index') if isinstance(response, dict) else 'Received non-dict or unsuccessful response'
                logger.error(f"Failed to set queue index via PATCH /api/v1/queue: {error_message}")
                return {"success": False, "error": error_message}
        except Exception as e:
            logger.error(f"Exception in set_queue_index: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    ### OLD METHODS START HERE ###
    def play_music(self, search_term: str) -> Dict[str, Any]:
        """
        Search for music, clear the queue, add the first result, and play it.
        
        Args:
            search_term: Search query for music to play
            
        Returns:
            Result of the operation
        """
        try:
            # Search for the music
            search_results = self.search(search_term)
            
            if not search_results:
                return {"success": False, "error": f"No results found for '{search_term}'"}
            
            # Extract the first video ID from the results
            # Assuming self.extract_video_id_from_search exists and works correctly
            video_id = self.extract_video_id_from_search(search_results)
            
            if not video_id:
                return {"success": False, "error": "Could not find a playable song in search results"}
            
            # Sequence of operations to play the new song
            #pause_result = self.pause()
            #if not pause_result.get("success"):
            #    # Log warning but continue, as pausing might fail if already paused or not critical
            #    logger.warning(f"Attempt to pause before playing returned: {pause_result.get('error', 'Unknown error')}")

            clear_result = self.clear_queue()
            if not clear_result.get("success"):
                return {"success": False, "error": f"Failed to clear queue: {clear_result.get('error', 'Unknown error')}"}

            add_song_result = self.add_to_queue(video_id)
            if not add_song_result.get("success"):
                return {"success": False, "error": f"Failed to add song '{video_id}' to queue: {add_song_result.get('error', 'Unknown error')}"}

            # After clearing and adding one song, it should be at index 0
            set_index_result = self.set_queue_index(0)
            if not set_index_result.get("success"):
                return {"success": False, "error": f"Failed to set queue index to 0: {set_index_result.get('error', 'Unknown error')}"}

            #play_result = self.play()
            #if not play_result.get("success"):
            #    return {"success": False, "error": f"Failed to play music: {play_result.get('error', 'Unknown error')}"}
                
            return {"success": True, "message": f"Successfully started playing song for '{search_term}' (Video ID: {video_id})"}
            
        except Exception as e:
            logger.error(f"Error in play_music for search term '{search_term}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def extract_video_id_from_search(self, search_results: Dict[str, Any]) -> Optional[str]:
        """
        Extract a video ID from YouTube Music search results.
        
        Handles different possible response structures from the API.
        
        Args:
            search_results: Search results from the YouTube Music API
            
        Returns:
            Video ID if found, None otherwise
        """
        if not isinstance(search_results, dict):
            return None
        
        try:
            # Check in contents -> tabbedSearchResultsRenderer -> tabs structure
            if "contents" in search_results and "tabbedSearchResultsRenderer" in search_results["contents"]:
                tabs = search_results["contents"]["tabbedSearchResultsRenderer"]["tabs"]
                
                # Look for selected tab
                for tab in tabs:
                    if "tabRenderer" in tab and tab["tabRenderer"].get("selected", False):
                        # Navigate to first song result
                        if "content" in tab["tabRenderer"]:
                            section_list = tab["tabRenderer"]["content"].get("sectionListRenderer", {})
                            contents = section_list.get("contents", [])
                            
                            # Look for musicCardShelfRenderer which contains song results
                            for content in contents:
                                if "musicCardShelfRenderer" in content:
                                    shelf_contents = content["musicCardShelfRenderer"].get("contents", [])
                                    
                                    # Get first song
                                    if shelf_contents and "musicResponsiveListItemRenderer" in shelf_contents[0]:
                                        # Check overlay for play button
                                        overlay = shelf_contents[0]["musicResponsiveListItemRenderer"].get("overlay", {})
                                        if "musicItemThumbnailOverlayRenderer" in overlay:
                                            content_renderer = overlay["musicItemThumbnailOverlayRenderer"].get("content", {})
                                            if "musicPlayButtonRenderer" in content_renderer:
                                                play_nav = content_renderer["musicPlayButtonRenderer"].get("playNavigationEndpoint", {})
                                                if "watchEndpoint" in play_nav:
                                                    return play_nav["watchEndpoint"].get("videoId")
            
            # Try simpler locations for video IDs
            # Method 1: Check for a simple list of items with videoId
            if "items" in search_results and search_results["items"]:
                items = search_results["items"]
                for item in items:
                    if "videoId" in item:
                        return item["videoId"]
                    if "id" in item and isinstance(item["id"], dict) and "videoId" in item["id"]:
                        return item["id"]["videoId"]
            
            # Method 2: Check for contents array with videoId
            if "contents" in search_results and isinstance(search_results["contents"], list):
                contents = search_results["contents"]
                if contents and "videoId" in contents[0]:
                    return contents[0]["videoId"]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
            return None
    
    def _extract_multiple_video_ids(self, search_results: Dict[str, Any], max_count: int = 5) -> List[str]:
        """
        Extract multiple video IDs from YouTube Music search results.
        
        Args:
            search_results: The search results from the YouTube Music API
            max_count: Maximum number of video IDs to extract
            
        Returns:
            List of video IDs found in the search results
        """
        video_ids = []
        
        try:
            # Method 1: Look in the tabbed search results structure
            if "contents" in search_results and "tabbedSearchResultsRenderer" in search_results["contents"]:
                tabs = search_results["contents"]["tabbedSearchResultsRenderer"]["tabs"]
                
                # Process each tab
                for tab in tabs:
                    if "tabRenderer" in tab and tab["tabRenderer"].get("selected", False):
                        if "content" in tab["tabRenderer"]:
                            section_list = tab["tabRenderer"]["content"].get("sectionListRenderer", {})
                            contents = section_list.get("contents", [])
                            
                            # Process each content section
                            for content in contents:
                                # Look for shelf renderers
                                if "musicCardShelfRenderer" in content:
                                    shelf_contents = content["musicCardShelfRenderer"].get("contents", [])
                                    
                                    # Process each item in the shelf
                                    for item in shelf_contents:
                                        if len(video_ids) >= max_count:
                                            return video_ids
                                            
                                        if "musicResponsiveListItemRenderer" in item:
                                            renderer = item["musicResponsiveListItemRenderer"]
                                            
                                            # Look for the play button overlay
                                            overlay = renderer.get("overlay", {})
                                            thumbnail_overlay = overlay.get("musicItemThumbnailOverlayRenderer", {})
                                            play_button = thumbnail_overlay.get("content", {}).get("musicPlayButtonRenderer", {})
                                            
                                            if "playNavigationEndpoint" in play_button:
                                                endpoint = play_button["playNavigationEndpoint"]
                                                watch_endpoint = endpoint.get("watchEndpoint", {})
                                                video_id = watch_endpoint.get("videoId")
                                                
                                                if video_id and video_id not in video_ids:
                                                    video_ids.append(video_id)
                                                    
                                # Also check music shelf renderers
                                if "musicShelfRenderer" in content:
                                    shelf_contents = content["musicShelfRenderer"].get("contents", [])
                                    
                                    for item in shelf_contents:
                                        if len(video_ids) >= max_count:
                                            return video_ids
                                            
                                        if "musicResponsiveListItemRenderer" in item:
                                            renderer = item["musicResponsiveListItemRenderer"]
                                            
                                            # Try different paths to find video IDs
                                            # Path 1: Through menu navigation items
                                            if "menu" in renderer:
                                                menu = renderer["menu"].get("menuRenderer", {})
                                                items = menu.get("items", [])
                                                
                                                for menu_item in items:
                                                    if "menuNavigationItemRenderer" in menu_item:
                                                        nav = menu_item["menuNavigationItemRenderer"]
                                                        if "navigationEndpoint" in nav:
                                                            endpoint = nav["navigationEndpoint"]
                                                            if "watchEndpoint" in endpoint:
                                                                video_id = endpoint["watchEndpoint"].get("videoId")
                                                                if video_id and video_id not in video_ids:
                                                                    video_ids.append(video_id)
                                                                    break
                                            
                                            # Path 2: Through playback buttons
                                            if "overlay" in renderer:
                                                overlay = renderer["overlay"].get("musicItemThumbnailOverlayRenderer", {})
                                                if "content" in overlay:
                                                    play_button = overlay["content"].get("musicPlayButtonRenderer", {})
                                                    if "playNavigationEndpoint" in play_button:
                                                        endpoint = play_button["playNavigationEndpoint"]
                                                        if "watchEndpoint" in endpoint:
                                                            video_id = endpoint["watchEndpoint"].get("videoId")
                                                            if video_id and video_id not in video_ids:
                                                                video_ids.append(video_id)
            
            # Method 2: Try simpler locations for video IDs
            if len(video_ids) < max_count and "items" in search_results and search_results["items"]:
                items = search_results["items"]
                for item in items:
                    if len(video_ids) >= max_count:
                        break
                    if "videoId" in item:
                        video_id = item["videoId"]
                        if video_id not in video_ids:
                            video_ids.append(video_id)
                    elif "id" in item and isinstance(item["id"], dict) and "videoId" in item["id"]:
                        video_id = item["id"]["videoId"]
                        if video_id not in video_ids:
                            video_ids.append(video_id)
        except Exception as e:
            logger.error(f"Error extracting multiple video IDs: {e}")
            
        return video_ids
    
    def start_radio(self, search_term: str) -> Dict[str, Any]:
        """
        Search for music, clear the queue, add multiple songs, and start playing the first one.
        
        Args:
            search_term: Search query for music to start playing
        
        Returns:
            Result of the operation
        """
        try:
            logger.info(f"Starting radio by searching for: '{search_term}'")
            
            search_results = self.search(search_term)
            if not search_results:
                return {"success": False, "error": f"No results found for '{search_term}'"}
            
            video_ids = self._extract_multiple_video_ids(search_results, max_count=5)
            if not video_ids:
                return {"success": False, "error": f"Could not extract any playable videos for '{search_term}'"}
            
            logger.info(f"Found {len(video_ids)} playable videos for radio: {video_ids}")

            pause_result = self.pause()
            if not pause_result.get("success"):
                logger.warning(f"Attempt to pause before starting radio returned: {pause_result.get('error', 'Unknown error')}")

            clear_result = self.clear_queue()
            if not clear_result.get("success"):
                return {"success": False, "error": f"Failed to clear queue for radio: {clear_result.get('error', 'Unknown error')}"}

            songs_added_count = 0
            for video_id in video_ids:
                add_song_result = self.add_to_queue(video_id)
                if add_song_result.get("success"):
                    songs_added_count += 1
                else:
                    logger.warning(f"Failed to add song '{video_id}' to queue for radio: {add_song_result.get('error', 'Unknown error')}")
        
            if songs_added_count == 0:
                return {"success": False, "error": f"Failed to add any songs to the queue for radio based on '{search_term}'"}

            set_index_result = self.set_queue_index(0)
            if not set_index_result.get("success"):
                return {"success": False, "error": f"Failed to set queue index to 0 for radio: {set_index_result.get('error', 'Unknown error')}"}

            play_result = self.play()
            if not play_result.get("success"):
                return {"success": False, "error": f"Failed to start radio playback: {play_result.get('error', 'Unknown error')}"}
            
            return {
                "success": True, 
                "message": f"Successfully started radio for '{search_term}'. Added {songs_added_count} songs to the queue. Playing first song: {video_ids[0] if video_ids else 'N/A'}",
                "search_term": search_term,
                "video_ids_added": video_ids[:songs_added_count]
            }
        
        except Exception as e:
            logger.error(f"Error in start_radio for search term '{search_term}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    ### OLD METHODS END HERE ###

    # === AHK Script Controls ===

    def play_music_ahk(self, search_term: str) -> Dict[str, Any]:
        """
        Plays music using an AutoHotkey script (command: "play").
        Searches for the term and then attempts to shuffle/play.

        Args:
            search_term: The song, artist, or album to search for.

        Returns:
            A dictionary indicating success or failure.
        """
        logger.info(f"Attempting to 'play' music via AHK for: {search_term}")

        ahk_scripts_dir = self.settings.paths.autohotkey_scripts_dir
        ahk_exe_path = self.settings.paths.autohotkey_exe
        ahk_script_path = os.path.join(ahk_scripts_dir, "youtube_music_play.ahk")

        result = run_ahk_script(
            script_path=ahk_script_path,
            args=["play", search_term],
            autohotkey_exe_path=ahk_exe_path,
            logger=logger
        )

        # Adapt the result from run_ahk_script
        if result["success"]:
            return {
                "success": True,
                "stdout": result["stdout"],
                "feedback": result["feedback"]
            }
        else:
            error_message_parts = []
            if result.get("error_message"):
                error_message_parts.append(result["error_message"])
            if result["stderr"]:
                error_message_parts.append(f"Script stderr: {result['stderr']}")
            if result["stdout"]:
                 error_message_parts.append(f"Script stdout: {result['stdout']}")
        
            combined_error_message = ". ".join(filter(None, error_message_parts))
            if not combined_error_message:
                combined_error_message = f"AHK script execution failed with exit code {result.get('exit_code', 'N/A')}."

            return {
                "success": False,
                "error": combined_error_message,
                "returncode": result.get("exit_code"),
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "feedback": result["feedback"]
            }

    def start_radio_ahk(self, search_term: str) -> Dict[str, Any]:
        """
        Starts a radio using an AutoHotkey script (command: "radio").
        Searches for the term and then attempts to start a radio.

        Args:
            search_term: The song, artist, or album to base the radio on.

        Returns:
            A dictionary indicating success or failure.
        """
        logger.info(f"Attempting to 'start radio' via AHK for: {search_term}")

        ahk_scripts_dir = self.settings.paths.autohotkey_scripts_dir
        ahk_exe_path = self.settings.paths.autohotkey_exe
        ahk_script_path = os.path.join(ahk_scripts_dir, "youtube_music_play.ahk")

        result = run_ahk_script(
            script_path=ahk_script_path,
            args=["radio", search_term],
            autohotkey_exe_path=ahk_exe_path,
            logger=logger
        )

        # Adapt the result from run_ahk_script (same logic as play_music_ahk)
        if result["success"]:
            return {
                "success": True,
                "stdout": result["stdout"],
                "feedback": result["feedback"]
            }
        else:
            error_message_parts = []
            if result.get("error_message"):
                error_message_parts.append(result["error_message"])
            if result["stderr"]:
                error_message_parts.append(f"Script stderr: {result['stderr']}")
            if result["stdout"]:
                 error_message_parts.append(f"Script stdout: {result['stdout']}")
        
            combined_error_message = ". ".join(filter(None, error_message_parts))
            if not combined_error_message:
                combined_error_message = f"AHK script execution failed with exit code {result.get('exit_code', 'N/A')}."

            return {
                "success": False,
                "error": combined_error_message,
                "returncode": result.get("exit_code"),
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "feedback": result["feedback"]
            }

if __name__ == "__main__":
    # Simple test if this script is run directly
    import sys
    from src.config.settings import load_settings # Added import
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Load settings and create controller
    try:
        settings = load_settings()
        controller = YouTubeMusicAPIController(settings=settings) # Pass settings
    except Exception as e:
        logger.error(f"Failed to initialize controller for testing: {e}")
        sys.exit(1)
        
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python -m src.tools.music_controller_api <command> [args]")
        print("Commands:")
        print("  play [search_term]         - Search and play (shuffle/default) the first result") # Updated description
        # print("  play_music [search_term]   - Search and play the first result") # play_music is now the default for "play"
        print("  radio [search_term]        - Start a radio based on a song/artist")
        print("  pause                      - Pause playback")
        print("  toggle                     - Toggle play/pause")
        print("  next [count]               - Skip to next track")
        print("  previous [count]           - Go to previous track")
        print("  forward [seconds]          - Skip forward")
        print("  back [seconds]             - Skip backward")
        print("  volume-up [amount]         - Increase volume")
        print("  volume-down [amount]       - Decrease volume")
        print("  get-volume                 - Get current volume")
        print("  like                       - Like current song")
        print("  dislike                    - Dislike current song")
        print("  shuffle                    - Toggle shuffle mode")
        print("  repeat                     - Toggle repeat mode")
        print("  search [search_term]       - Search without playing")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Execute command
    # The CLI "play" command will now map to play_music_ahk (which sends "play" to AHK)
    # The CLI "radio" command will map to start_radio_ahk (which sends "radio" to AHK)
    if command == "play" and len(sys.argv) > 2: # Simplified condition
        search_term = sys.argv[2]
        result = controller.play_music_ahk(search_term) # play_music_ahk now sends "play" command
    elif command == "radio" and len(sys.argv) > 2:
        search_term = sys.argv[2]
        result = controller.start_radio_ahk(search_term) # start_radio_ahk sends "radio" command
    elif command == "play": # This 'play' is for resuming playback if no search term is given
        result = controller.play()
    elif command == "pause":
        result = controller.pause()
    elif command == "toggle":
        result = controller.toggle_playback()
    elif command == "next":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        result = controller.next(count)
    elif command == "previous" or command == "prev":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        result = controller.previous(count)
    elif command == "forward":
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = controller.forward(seconds)
    elif command == "back" or command == "rewind":
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = controller.rewind(seconds)
    elif command == "volume-up":
        amount = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = controller.volume_up(amount)
    elif command == "volume-down":
        amount = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = controller.volume_down(amount)
    elif command == "get-volume":
        volume = controller.get_volume()
        print(volume if volume is not None else "Error getting volume")
        sys.exit(0)
    elif command == "like":
        result = controller.like()
    elif command == "dislike":
        result = controller.dislike()
    elif command == "shuffle":
        result = controller.toggle_shuffle()
    elif command == "repeat":
        result = controller.toggle_repeat()
    elif command == "search" and len(sys.argv) > 2:
        search_term = sys.argv[2]
        result = controller.search(search_term)
        print("\nSearch results for: " + search_term)
        
        # Try to extract video ID to show a more useful result
        video_id = controller.extract_video_id_from_search(result)
        if video_id:
            print(f"First result video ID: {video_id}")
            print(f"To play this: python -m src.tools.music_controller_api play \"{search_term}\"")
            print(f"To start radio: python -m src.tools.music_controller_api radio \"{search_term}\"")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    # Print result
    print(json.dumps(result, indent=2))
