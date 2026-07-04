# api_clients.py
import time
import requests
from typing import Optional
from cachetools import TTLCache

from config import Config, logger
from models import MovieInfo

# Cache for movie data
movie_cache = TTLCache(maxsize=100, ttl=Config.CACHE_TTL)

class MovieAPIError(Exception):
    """Custom exception for API errors"""
    pass

class BaseMovieAPI:
    """Base class for movie APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'MovieBot/1.0'})
        self.name = "BaseAPI"
    
    def _make_request(self, url: str, params: dict = None) -> dict:
        """Make HTTP request with retry logic"""
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=Config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"API request failed (attempt {attempt + 1}): {e}")
                if attempt == Config.MAX_RETRIES - 1:
                    raise MovieAPIError(f"Failed after {Config.MAX_RETRIES} attempts")
                time.sleep(1 * (attempt + 1))
        return {}

class OMDbAPI(BaseMovieAPI):
    """OMDb API implementation"""
    
    def __init__(self):
        super().__init__()
        self.name = "OMDb API"
        if not Config.OMDB_API_KEY:
            raise ValueError("OMDb API key not configured")
    
    def get_movie(self, title: str) -> Optional[MovieInfo]:
        """Fetch movie from OMDb API"""
        try:
            params = {
                't': title,
                'apikey': Config.OMDB_API_KEY,
                'plot': 'short',
                'r': 'json'
            }
            data = self._make_request(Config.OMDB_URL, params)
            
            if data.get('Response') == 'True':
                return MovieInfo(
                    title=data.get('Title', 'N/A'),
                    year=data.get('Year', 'N/A'),
                    rating=data.get('imdbRating', 'N/A'),
                    plot=data.get('Plot', 'N/A'),
                    actors=data.get('Actors', 'N/A'),
                    director=data.get('Director', 'N/A'),
                    genre=data.get('Genre', 'N/A'),
                    poster=data.get('Poster', 'N/A'),
                    imdb_id=data.get('imdbID', 'N/A'),
                    runtime=data.get('Runtime', 'N/A'),
                    source=self.name
                )
            return None
        except Exception as e:
            logger.error(f"OMDb API error: {e}")
            return None

class MovieAPIManager:
    """Manages multiple movie APIs with fallback"""
    
    def __init__(self):
        self.apis = []
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize available APIs"""
        try:
            if Config.OMDB_API_KEY:
                self.apis.append(OMDbAPI())
        except ValueError as e:
            logger.warning(f"API initialization warning: {e}")
    
    def get_movie(self, title: str) -> Optional[MovieInfo]:
        """Fetch movie information with caching"""
        # Check cache first
        cache_key = title.lower().strip()
        if cache_key in movie_cache:
            logger.info(f"Cache hit for: {title}")
            return movie_cache[cache_key]
        
        # Try each API
        for api in self.apis:
            try:
                logger.info(f"Trying {api.name} for: {title}")
                result = api.get_movie(title)
                if result:
                    movie_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.warning(f"{api.name} failed: {e}")
                continue
        return None

# Global API manager instance
api_manager = MovieAPIManager()