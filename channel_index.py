# channel_index.py - Updated to store file_id
import os
import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from telegram import Message

from config import Config, logger

class ChannelIndex:
    """Manages movie index from private channel"""
    
    def __init__(self, app=None):
        self.app = app
        self.index = {}
        self.is_ready = False
        self.last_update = None
        self.load_index()
    
    def load_index(self):
        """Load index from JSON file"""
        try:
            if os.path.exists(Config.INDEX_FILE):
                with open(Config.INDEX_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.index = data.get('movies', {})
                    self.last_update = data.get('last_updated')
                    logger.info(f"✅ Loaded index with {len(self.index)} movies")
                    self.is_ready = True
            else:
                logger.info("📝 No existing index found. Creating new one...")
                self.index = {}
                self.last_update = None
                self.is_ready = True
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            self.index = {}
            self.last_update = None
            self.is_ready = True
    
    def save_index(self):
        """Save index to JSON file"""
        try:
            data = {
                'movies': self.index,
                'last_updated': datetime.now().isoformat(),
                'total_movies': len(self.index),
                'channel_id': Config.CHANNEL_ID
            }
            with open(Config.INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved index with {len(self.index)} movies")
            return True
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            return False
    
    async def build_index(self, context=None):
        """Build index by scanning channel messages (limited capability)"""
        logger.info("ℹ️ Bots cannot read channel history automatically.")
        logger.info("ℹ️ Movies must be added by forwarding them to the bot.")
        logger.info(f"📊 Current index has {len(self.index)} movies")
        self.is_ready = True
        return True
    
    def add_movie_manually(self, movie_name: str, file_name: str, message_id: int, 
                          file_type: str = None, file_size: int = None, file_id: str = None,
                          from_chat_id: int = None):
        """Add a movie to the index manually"""
        try:
            clean_name = self.clean_filename(movie_name)
            if not clean_name:
                logger.warning(f"Could not clean movie name: {movie_name}")
                return False
            
            if clean_name in self.index:
                logger.info(f"Movie already exists: {clean_name}")
                return False
            
            self.index[clean_name] = {
                'clean_name': clean_name,
                'file_name': file_name,
                'message_id': message_id,
                'file_id': file_id,  # Store file_id for direct sending
                'file_type': file_type,
                'file_size': file_size,
                'date': datetime.now().isoformat(),
                'source_channel': from_chat_id or Config.CHANNEL_ID
            }
            self.save_index()
            logger.info(f"✅ Added: {clean_name} → {file_name} (file_id: {file_id[:20] if file_id else 'N/A'}...)")
            return True
            
        except Exception as e:
            logger.error(f"Error adding movie manually: {e}")
            return False
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename to get movie name"""
        try:
            if not filename:
                return None
            
            name = os.path.splitext(filename)[0]
            
            patterns_to_remove = [
                r'[\(\[]\s*(1080p|720p|480p|2160p|4K|HD|SD|HDRip|WEB-DL|BluRay|BRRip|DVDRip|CAM|TS|TC|WEBRip|HDR|SDR)\s*[\)\]]',
                r'[\(\[]\s*(x264|x265|HEVC|H264|H265|AVC|VP9|AV1)\s*[\)\]]',
                r'[\(\[]\s*(DTS|AC3|AAC|MP3|FLAC|TrueHD|Atmos|EAC3)\s*[\)\]]',
                r'[\(\[]\s*(10bit|8bit|HDR10|DolbyVision|DV)\s*[\)\]]',
                r'[\(\[]\s*(REMUX|REPACK|PROPER|RERIP|FINAL|COMPLETE)\s*[\)\]]',
                r'\b(19[0-9]{2}|20[0-9]{2})\b',
                r'[\(\[]\s*[A-Za-z0-9]+\s*[\)\]]',
            ]
            
            for pattern in patterns_to_remove:
                name = re.sub(pattern, ' ', name, flags=re.IGNORECASE)
            
            name = re.sub(r'[._\-+]', ' ', name)
            name = re.sub(r'\s+', ' ', name).strip()
            
            if len(name) < 2:
                name = os.path.splitext(filename)[0]
                name = re.sub(r'[._\-+]', ' ', name)
                name = re.sub(r'\s+', ' ', name).strip()
            
            return name.lower()
            
        except Exception as e:
            logger.warning(f"Error cleaning filename '{filename}': {e}")
            return None
    
    def search_movie(self, query: str) -> List[Dict]:
        """Search for movies by name"""
        try:
            if not self.is_ready:
                return []
            
            cleaned_query = self.clean_filename(query)
            if not cleaned_query:
                return []
            
            results = []
            
            # Exact match
            for movie_name, data in self.index.items():
                if movie_name == cleaned_query:
                    results.append({'movie_name': movie_name, **data, 'match_type': 'exact'})
            
            # Contains match
            if not results:
                for movie_name, data in self.index.items():
                    if cleaned_query in movie_name or movie_name in cleaned_query:
                        results.append({'movie_name': movie_name, **data, 'match_type': 'contains'})
            
            # Word match
            if not results:
                query_words = set(cleaned_query.split())
                for movie_name, data in self.index.items():
                    movie_words = set(movie_name.split())
                    for q_word in query_words:
                        if len(q_word) >= 3:
                            for m_word in movie_words:
                                if len(m_word) >= 3 and (q_word in m_word or m_word in q_word):
                                    results.append({'movie_name': movie_name, **data, 'match_type': 'partial'})
                                    break
                            if results:
                                break
            
            priority = {'exact': 0, 'contains': 1, 'partial': 2}
            results.sort(key=lambda x: priority.get(x.get('match_type', 'partial'), 3))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        return {
            'total_movies': len(self.index),
            'last_updated': self.last_update,
            'is_ready': self.is_ready
        }

# Global instance
_channel_index = None

def init_channel_index(app):
    """Initialize the channel index"""
    global _channel_index
    if _channel_index is None:
        _channel_index = ChannelIndex(app)
    return _channel_index

def get_channel_index():
    """Get the channel index instance"""
    return _channel_index