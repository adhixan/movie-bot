# main.py
import sys
import asyncio
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

from config import Config
from handlers import MovieHandlers
from channel_index import init_channel_index, get_channel_index

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MovieBot:
    """Main bot application class"""
    
    def __init__(self):
        self.app = None
        self.handlers = MovieHandlers()
        self.initialized = False
    
    def setup_handlers(self):
        """Register all handlers with the application"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        self.app.add_handler(CommandHandler("search", self.handlers.search))
        self.app.add_handler(CommandHandler("stats", self.handlers.stats))
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
        
        # Handler for direct uploads (when user sends a file directly)
        self.app.add_handler(
            MessageHandler(
                (filters.Document.VIDEO | filters.VIDEO | filters.AUDIO) & ~filters.FORWARDED,
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
    
    async def initialize_index(self):
        """Initialize the channel index"""
        try:
            logger.info("📂 Initializing channel index...")
            init_channel_index(self.app)
            
            index = get_channel_index()
            if index:
                await index.build_index()
                self.initialized = True
                logger.info(f"✅ Bot initialized! Index has {len(index.index)} movies")
                
                if len(index.index) == 0:
                    logger.info("💡 No movies in index. To add movies:")
                    logger.info("   Forward a movie from your channel to this bot")
            else:
                logger.error("❌ Failed to initialize channel index")
                self.initialized = True
                
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            self.initialized = True
    
    def run(self):
        """Start the bot"""
        try:
            # Verify configuration
            if not Config.TELEGRAM_TOKEN:
                raise ValueError("TELEGRAM_TOKEN is required in .env file")
            
            if not Config.OMDB_API_KEY:
                raise ValueError("OMDB_API_KEY is required in .env file")
            
            if not Config.CHANNEL_ID:
                raise ValueError("CHANNEL_ID is required in .env file")
            
            # Create application
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
            
            # Setup handlers
            self.setup_handlers()
            
            # Add error handler
            self.app.add_error_handler(self.error_handler)
            
            # Start the bot
            print("=" * 60)
            print("🤖 Movie Bot is starting...")
            print(f"📊 Active APIs: {', '.join(Config.get_active_apis())}")
            print(f"📁 Channel ID: {Config.CHANNEL_ID}")
            print("🔧 Press Ctrl+C to stop")
            print("=" * 60)
            print("")
            print("📁 *How to add movies to the index:*")
            print("1. Forward a movie file from your channel to this bot")
            print("2. The bot will automatically index it")
            print("3. Users can then search for it")
            print("")
            print("📌 The bot will also auto-index any new posts in your channel")
            print("")
            
            # Create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Initialize index
            loop.run_until_complete(self.initialize_index())
            
            # Run the bot
            self.app.run_polling(drop_pending_updates=True)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            print("\n👋 Bot stopped.")
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            print(f"\n❌ Error: {e}")
            print("\n💡 Please check:")
            print("1. Your TELEGRAM_TOKEN is correct in .env file")
            print("2. Your OMDB_API_KEY is correct in .env file")
            print("3. Your CHANNEL_ID is correct in .env file")
            print("4. Bot is an admin in your private channel")
            print("5. Your internet connection is working")
            sys.exit(1)

def main():
    bot = MovieBot()
    bot.run()

if __name__ == "__main__":
    main()