# utils.py
import re
import html
from typing import Optional

def sanitize_text(text: str) -> str:
    """Sanitize text for safe display"""
    if not text:
        return ""
    return html.escape(text.strip())

def extract_year(title: str) -> Optional[str]:
    """Extract year from movie title if present"""
    match = re.search(r'\((\d{4})\)$', title)
    if match:
        return match.group(1)
    return None

def clean_movie_title(title: str) -> str:
    """Clean movie title by removing year"""
    return re.sub(r'\s*\(\d{4}\)$', '', title).strip()

def format_duration(minutes: int) -> str:
    """Format duration in hours and minutes"""
    if not minutes or minutes <= 0:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"

def is_valid_movie_name(name: str) -> bool:
    """Validate movie name"""
    if not name or len(name.strip()) < 2:
        return False
    invalid_patterns = [
        r'^[0-9]+$',
        r'^[^\w\s]+$',
    ]
    for pattern in invalid_patterns:
        if re.match(pattern, name):
            return False
    return True

def truncate_text(text: str, max_length: int = 400) -> str:
    """Truncate text to max length with ellipsis"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + "..."