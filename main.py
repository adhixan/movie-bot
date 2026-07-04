# main.py - Complete working version for Render
import sys
import os
import logging
import threading
import time
import http.server
import socketserver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from config import Config
from handlers import MovieHandlers
from channel_index import init_channel_index, get_channel_index

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ SIMPLE HTTP SERVER FOR RENDER ============
class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def run_health_server():
    """Run a simple HTTP server for Render health checks"""
    port = int(os.environ.get("PORT", 8080))
    
    try:
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            print(f"✅ Health server running on port {port}")
            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"⚠️ Port {port} busy, trying {port + 1}")
            port += 1
            try:
                with socketserver.TCPServer(("", port), HealthHandler) as httpd:
                    print(f"✅ Health server running on port {port}")
                    httpd.serve_forever()
            except Exception as e2:
                print(f"❌ Could not start health server: {e2}")
        else:
            print(f"❌ Could not start health server: {e}")

# ============ BOT APPLICATION ============
class MovieBot:
    """Main bot application class"""
    
    def __init__(self):
        self.app = None
        self.handlers = MovieHandlers()
        self.initialized = False
    
    def run(self):
        """Start the bot"""
        try:
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
            
            if not Config.TELEGRAM_TOKEN:
                raise ValueError("TELEGRAM_TOKEN is required")
            if not Config.OMDB_API_KEY:
                raise ValueError("OMDB_API_KEY is required")
            if not Config.CHANNEL_ID:
                raise ValueError("CHANNEL_ID is required")
            
            # Start HTTP server in background for Render
            server_thread = threading.Thread(target=run_health_server, daemon=True)
            server_thread.start()
            time.sleep(1)
            
            # Create application
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
            
            # Add handlers
            self.app.add_handler(CommandHandler("start", self.handlers.start))
            self.app.add_handler(CommandHandler("help", self.handlers.help_command))
            self.app.add_handler(CommandHandler("search", self.handlers.search))
            self.app.add_handler(CommandHandler("stats", self.handlers.stats))
            self.app.add_handler(CommandHandler("update", self.handlers.update_index))
            self.app.add_handler(CommandHandler("about", self.handlers.about))
            self.app.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    self.handlers.handle_movie_query
                )
            )
            self.app.add_handler(
                MessageHandler(
                    filters.FORWARDED,
                    self.handlers.handle_forwarded_movie
                )
            )
            self.app.add_handler(
                MessageHandler(
                    filters.ALL & filters.ChatType.CHANNEL,
                    self.handlers.handle_channel_post
                )
            )
            
            # Initialize index
            init_channel_index(self.app)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.handlers.initialize_index())
            
            print("=" * 60)
            print("🤖 Movie Bot is starting...")
            print(f"📊 Active APIs: {', '.join(Config.get_active_apis())}")
            print(f"📁 Channel ID: {Config.CHANNEL_ID}")
            print("=" * 60)
            print("")
            print("💡 How to add movies:")
            print("1. Forward a movie from your channel to this bot")
            print("2. The bot will automatically index it")
            print("3. Users can then search for it")
            print("")
            print("✅ Bot is running!")
            print("=" * 60)
            print("")
            
            # Start polling
            self.app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            print(f"\n❌ Error: {e}")
            sys.exit(1)

def main():
    bot = MovieBot()
    bot.run()

if __name__ == "__main__":
    main()
