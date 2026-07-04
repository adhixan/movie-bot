# main.py - Using Application (works with python-telegram-bot 20.0)
import sys
import os
import asyncio
import logging
import threading
import http.server
import socketserver
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

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

def run_health_server():
    """Run a simple HTTP server for Render health checks"""
    port = int(os.environ.get("PORT", 5000))
    with socketserver.TCPServer(("", port), HealthHandler) as httpd:
        print(f"✅ Health server running on port {port}")
        httpd.serve_forever()

# ============ BOT APPLICATION ============
class MovieBot:
    """Main bot application class"""
    
    def __init__(self):
        self.app = None
        self.handlers = MovieHandlers()
        self.index_update_task = None
        self.initialized = False
    
    def setup_handlers(self):
        """Register all handlers with the application"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        self.app.add_handler(CommandHandler("search", self.handlers.search))
        self.app.add_handler(CommandHandler("stats", self.handlers.stats))
        self.app.add_handler(CommandHandler("update", self.handlers.update_index))
        self.app.add_handler(CommandHandler("about", self.handlers.about))
        
        # Message handler - handle text messages as movie queries
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handlers.handle_movie_query
            )
        )
        
        # Handler for forwarded messages (to build index)
        self.app.add_handler(
            MessageHandler(
                filters.FORWARDED,
                self.handlers.handle_forwarded_movie
            )
        )
        
        # Handler for channel posts (when bot is in channel)
        self.app.add_handler(
            MessageHandler(
                filters.ALL & filters.ChatType.CHANNEL,
                self.handlers.handle_channel_post
            )
        )
    
    async def error_handler(self, update, context):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again later."
                )
            except:
                pass
    
    async def auto_update_index(self):
        """Auto-update channel index every 24 hours"""
        while not self.initialized:
            await asyncio.sleep(5)
        
        while True:
            try:
                index = get_channel_index()
                if index is None:
                    await asyncio.sleep(60)
                    continue
                    
                logger.info("🔄 Running auto-update for channel index...")
                success = await index.build_index()
                if success:
                    stats = index.get_stats()
                    logger.info(f"✅ Auto-update completed: {stats['total_movies']} movies indexed")
            except Exception as e:
                logger.error(f"Auto-update error: {e}")
            
            await asyncio.sleep(Config.AUTO_UPDATE_INTERVAL)
    
    async def initialize_index(self):
        """Initialize the channel index"""
        try:
            logger.info("📂 Initializing channel index...")
            init_channel_index(self.app)
            
            index = get_channel_index()
            if index:
                logger.info("📂 Building initial channel index...")
                await index.build_index()
                self.initialized = True
                logger.info("✅ Bot initialization complete!")
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            self.initialized = True
    
    def run(self):
        """Start the bot"""
        try:
            if not Config.TELEGRAM_TOKEN:
                raise ValueError("TELEGRAM_TOKEN is required")
            if not Config.OMDB_API_KEY:
                raise ValueError("OMDB_API_KEY is required")
            if not Config.CHANNEL_ID:
                raise ValueError("CHANNEL_ID is required")
            
            # Start HTTP server in background
            server_thread = threading.Thread(target=run_health_server, daemon=True)
            server_thread.start()
            
            # Create application
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
            
            # Setup handlers
            self.setup_handlers()
            
            # Add error handler
            self.app.add_error_handler(self.error_handler)
            
            # Initialize index
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.initialize_index())
            loop.create_task(self.auto_update_index())
            
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
            
            # Start the bot
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
