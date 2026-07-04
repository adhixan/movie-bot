# channel_index.py
import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from telegram import Message, Document, Video, Audio, PhotoSize

from config import Config, logger

class ChannelIndex:
    """Manages movie index from private channel"""
    
    def __init__(self, app=None):
        self.app = app
        self.index = {}
        self.is_ready = False
        self.load_index()
        self.last_update = None
    
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
                self.is_ready = False
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            self.index = {}
            self.last_update = None
            self.is_ready = False
    
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
            self.is_ready = True
            return True
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            return False
    
    async def build_index(self, context=None):
        """Build index by scanning channel messages"""
        try:
            logger.info("🔄 Building channel index...")
            logger.info("ℹ️ Note: Bots cannot read channel history.")
            logger.info("ℹ️ Movies are added by forwarding them to the bot.")
            
            if self.index:
                logger.info(f"✅ Index already has {len(self.index)} movies")
                self.is_ready = True
                return True
            
            logger.info("💡 No movies found. To add movies:")
            logger.info("💡 Forward them from your channel to this bot.")
            self.is_ready = True
            return True
            
        except Exception as e:
            logger.error(f"Error building index: {e}")
            self.is_ready = True
            return False
    
    def add_movie_manually(self, movie_name: str, file_name: str, message_id: int, 
                          file_type: str = None, file_size: int = None, file_id: str = None):
        """Add a movie to the index manually (used by forward handler)"""
        try:
            clean_name = self.clean_filename(file_name)
            if not clean_name:
                logger.warning(f"Could not clean movie name: {file_name}")
                return False
            
            if clean_name in self.index:
                logger.info(f"Movie already exists: {clean_name}")
                return False
            
            self.index[clean_name] = {
                'clean_name': clean_name,
                'file_name': file_name,
                'message_id': message_id,
                'file_id': file_id,
                'file_type': file_type,
                'file_size': file_size,
                'date': datetime.now().isoformat(),
                'source_channel': Config.CHANNEL_ID
            }
            self.save_index()
            logger.info(f"✅ Manually added: {clean_name} → {file_name} (msg_id: {message_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding movie manually: {e}")
            return False
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename to get movie name"""
        try:
            name = os.path.splitext(filename)[0]
            name = re.sub(r'\b(19[0-9]{2}|20[0-9]{2})\b', '', name)
            
            quality_patterns = [
                r'\b(1080p|720p|480p|2160p|4K|HD|SD|HDRip|WEB-DL|BluRay|BRRip|DVDRip|CAM|TS|TC|WEBRip|HDR)\b',
                r'[\(\[]\s*(1080p|720p|480p|2160p|4K|HD|SD)\s*[\)\]]',
                r'[\(\[]\s*(HDRip|WEB-DL|BluRay|BRRip|DVDRip)\s*[\)\]]',
                r'[\(\[]\s*(x264|x265|HEVC|H264|H265)\s*[\)\]]',
                r'[\(\[]\s*(DTS|AC3|AAC|MP3|FLAC)\s*[\)\]]',
            ]
            for pattern in quality_patterns:
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            
            name = re.sub(r'[._-]', ' ', name)
            name = re.sub(r'[^\w\s]', '', name)
            name = re.sub(r'\s+', ' ', name).strip()
            name = name.lower()
            
            return name
            
        except Exception as e:
            logger.warning(f"Error cleaning filename '{filename}': {e}")
            return None
    
    def search_movie(self, query: str) -> List[Dict]:
        """Search for movies by name"""
        try:
            if not self.is_ready:
                logger.warning("⚠️ Index not ready, returning empty results")
                return []
            
            cleaned_query = self.clean_filename(query)
            if not cleaned_query:
                return []
            
            results = []
            
            for movie_name, data in self.index.items():
                if movie_name == cleaned_query:
                    results.append({'movie_name': movie_name, **data, 'match_type': 'exact'})
            
            if not results:
                for movie_name, data in self.index.items():
                    if cleaned_query in movie_name or movie_name in cleaned_query:
                        results.append({'movie_name': movie_name, **data, 'match_type': 'contains'})
            
            if not results:
                query_words = set(cleaned_query.split())
                for movie_name, data in self.index.items():
                    movie_words = set(movie_name.split())
                    if query_words & movie_words:
                        results.append({'movie_name': movie_name, **data, 'match_type': 'partial'})
            
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
            'last_update_days': (datetime.now() - self.last_update).days if self.last_update else None,
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
