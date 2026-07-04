# models.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MovieInfo:
    """Movie information data class"""
    title: str
    year: str
    rating: str
    plot: str
    actors: str
    director: str
    genre: str
    poster: str
    imdb_id: str
    runtime: str
    source: str
    fetched_at: datetime = None
    
    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now()
    
    def format_message(self) -> str:
        """Format movie info for Telegram message"""
        if not self.title:
            return "⚠️ No movie information available."
        
        message = (
            f"🎬 *{self.title}* ({self.year})\n"
            f"⭐ Rating: {self.rating}\n"
            f"⏱ Runtime: {self.runtime}\n"
            f"🎭 Genre: {self.genre}\n"
            f"👨‍💼 Director: {self.director}\n"
            f"🎭 Actors: {self.actors}\n\n"
            f"📝 *Plot:*\n{self.plot[:400]}..." if self.plot and len(self.plot) > 400 else f"📝 *Plot:*\n{self.plot}\n\n"
            f"🔗 Source: {self.source}"
        )
        return message