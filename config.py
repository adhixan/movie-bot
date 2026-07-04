# config.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration management"""
    
    # Telegram Bot Token
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN not found in .env file!")
    
    # Channel ID for movie storage
    CHANNEL_ID = os.getenv("CHANNEL_ID")
    if not CHANNEL_ID:
        raise ValueError("❌ CHANNEL_ID not found in .env file!")
    CHANNEL_ID = int(CHANNEL_ID)  # Convert to integer
    
    # API Keys
    OMDB_API_KEY = os.getenv("OMDB_API_KEY")
    if not OMDB_API_KEY:
        raise ValueError("❌ OMDB_API_KEY not found in .env file!")
    
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
    
    # API Endpoints
    OMDB_URL = "http://www.omdbapi.com/"
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    TMDB_SEARCH_URL = f"{TMDB_BASE_URL}/search/movie"
    TMDB_MOVIE_URL = f"{TMDB_BASE_URL}/movie"
    RAPIDAPI_URL = "https://imdb8.p.rapidapi.com/auto-complete"
    
    # Request settings
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    CACHE_TTL = 3600  # 1 hour
    
    # Index settings
    INDEX_FILE = "index.json"
    AUTO_UPDATE_INTERVAL = int(os.getenv("AUTO_UPDATE_INTERVAL", 86400))  # 24 hours in seconds
    
    # Logging
    LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))
    
    @classmethod
    def get_active_apis(cls):
        """Return list of active APIs"""
        apis = ["Channel Index"]
        if cls.OMDB_API_KEY:
            apis.append("OMDb")
        if cls.TMDB_API_KEY:
            apis.append("TMDB")
        if cls.RAPIDAPI_KEY:
            apis.append("RapidAPI")
        return apis

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=Config.LOG_LEVEL
)
logger = logging.getLogger(__name__)
