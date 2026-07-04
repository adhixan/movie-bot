# main.py - Works with python-telegram-bot 13.15
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
    port = int(os.environ.get("PORT", 5000))
    
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
        self.updater = None
        self.handlers = MovieHandlers()
    
    def run(self):
        """Start the bot using Updater (version 13.15)"""
        try:
            # Import from version 13.15
            from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
            
            if not Config.TELEGRAM_TOKEN:
                raise ValueError("TELEGRAM_TOKEN is required")
            if not Config.OMDB_API_KEY:
                raise ValueError("OMDB_API_KEY is required")
            if not Config.CHANNEL_ID:
                raise ValueError("CHANNEL_ID is required")
            
            # Start HTTP server in background for Render
            server_thread = threading.Thread(target=run_health_server, daemon=True)
            server_thread.start()
            time.sleep(1)  # Give server time to start
            
            # Create updater with version 13.15 (no bug)
            self.updater = Updater(token=Config.TELEGRAM_TOKEN, use_context=True)
            dispatcher = self.updater.dispatcher
            
            # Initialize index
            init_channel_index(None)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.handlers.initialize_index())
            
            # Register handlers
            dispatcher.add_handler(CommandHandler("start", self.handlers.start))
            dispatcher.add_handler(CommandHandler("help", self.handlers.help_command))
            dispatcher.add_handler(CommandHandler("search", self.handlers.search))
            dispatcher.add_handler(CommandHandler("stats", self.handlers.stats))
            dispatcher.add_handler(CommandHandler("update", self.handlers.update_index))
            dispatcher.add_handler(CommandHandler("about", self.handlers.about))
            dispatcher.add_handler(
                MessageHandler(
                    Filters.text & ~Filters.command,
                    self.handlers.handle_movie_query
                )
            )
            dispatcher.add_handler(
                MessageHandler(
                    Filters.forwarded,
                    self.handlers.handle_forwarded_movie
                )
            )
            dispatcher.add_handler(
                MessageHandler(
                    Filters.chat_type.channel,
                    self.handlers.handle_channel_post
                )
            )
            
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
            self.updater.start_polling()
            self.updater.idle()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            print(f"\n❌ Error: {e}")
            sys.exit(1)

def main():
    bot = MovieBot()
    bot.run()

if __name__ == "__main__":
    main()
