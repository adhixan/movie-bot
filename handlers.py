# handlers.py - Using Application (works with python-telegram-bot 20.0)
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from api_clients import api_manager
from config import Config
from channel_index import get_channel_index

logger = logging.getLogger(__name__)

class MovieHandlers:
    """Handlers for movie-related commands and messages"""
    
    @staticmethod
    def get_index():
        """Get channel index with proper error handling"""
        index = get_channel_index()
        if index is None:
            logger.warning("⚠️ Channel index not initialized")
        return index
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        message = update.effective_message
        if not message:
            return
            
        user = update.effective_user
        user_name = user.first_name if user else "Friend"
        
        welcome_message = (
            f"🎬 *Welcome to Movie Bot, {user_name}!*\n\n"
            "Send me any movie name and I'll try to find it!\n\n"
            "📌 *Commands:*\n"
            "/start - Show this message\n"
            "/help - Show help\n"
            "/search <movie_name> - Search for a movie\n"
            "/stats - Show bot statistics\n"
            "/update - Manually update channel index\n"
            "/about - About this bot\n\n"
            "💡 *How to add movies:*\n"
            "1️⃣ Forward a movie from your channel to this bot\n"
            "2️⃣ Bot will automatically index it\n"
            "3️⃣ Users can then search for it\n\n"
            "🔍 *Search:* Just type a movie name!"
        )
        await message.reply_text(welcome_message, parse_mode='Markdown')
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        message = update.effective_message
        if not message:
            return
            
        help_text = (
            "📚 *Help*\n\n"
            "Just type any movie name to search!\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/search <movie_name> - Search for a movie\n"
            "/stats - Show bot statistics\n"
            "/update - Manually update channel index\n"
            "/about - About this bot\n\n"
            "📁 *Adding Movies:*\n"
            "Forward any movie from your channel to this bot\n"
            "The bot will automatically index it for search\n\n"
            "🔍 *Search Tips:*\n"
            "• Try exact movie names\n"
            "• Partial names work too\n"
            "• Example: 'Inception' or 'Dark Knight'"
        )
        await message.reply_text(help_text, parse_mode='Markdown')
    
    @staticmethod
    async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle channel posts (when bot receives messages from channel)"""
        try:
            channel_post = update.channel_post
            if not channel_post:
                return
            
            logger.info(f"📨 Received channel post from {channel_post.chat.title}")
            
            file_name = None
            message_id = channel_post.message_id
            file_type = None
            file_size = None
            file_id = None
            
            if channel_post.document:
                file_name = channel_post.document.file_name
                file_type = "document"
                file_size = channel_post.document.file_size
                file_id = channel_post.document.file_id
            elif channel_post.video:
                file_name = channel_post.video.file_name
                file_type = "video"
                file_size = channel_post.video.file_size
                file_id = channel_post.video.file_id
            elif channel_post.audio:
                file_name = channel_post.audio.file_name
                file_type = "audio"
                file_size = channel_post.audio.file_size
                file_id = channel_post.audio.file_id
            else:
                return
            
            index = MovieHandlers.get_index()
            if index is None:
                return
            
            clean_name = index.clean_filename(file_name)
            if not clean_name:
                return
            
            existing = index.search_movie(clean_name)
            if existing:
                return
            
            success = index.add_movie_manually(
                movie_name=clean_name,
                file_name=file_name,
                message_id=message_id,
                file_type=file_type,
                file_size=file_size,
                file_id=file_id
            )
            
            if success:
                logger.info(f"✅ Indexed from channel post: {clean_name} → {file_name}")
            
        except Exception as e:
            logger.error(f"Error handling channel post: {e}")
    
    @staticmethod
    async def handle_forwarded_movie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle forwarded movie messages to add to index"""
        try:
            message = update.effective_message
            if not message:
                return
            
            if not message.forward_from_chat:
                return
            
            channel_title = message.forward_from_chat.title or "Unknown Channel"
            logger.info(f"📨 Received forwarded message from channel: {channel_title}")
            
            file_name = None
            message_id = message.message_id
            file_type = None
            file_size = None
            file_id = None
            
            if message.document:
                file_name = message.document.file_name
                file_type = "document"
                file_size = message.document.file_size
                file_id = message.document.file_id
            elif message.video:
                file_name = message.video.file_name
                file_type = "video"
                file_size = message.video.file_size
                file_id = message.video.file_id
            elif message.audio:
                file_name = message.audio.file_name
                file_type = "audio"
                file_size = message.audio.file_size
                file_id = message.audio.file_id
            else:
                await message.reply_text(
                    "❌ This message doesn't contain a file.\n"
                    "Please forward a message with a movie file."
                )
                return
            
            index = MovieHandlers.get_index()
            if index is None:
                await message.reply_text(
                    "❌ Index not initialized yet. Please try again in a moment."
                )
                return
            
            clean_name = index.clean_filename(file_name)
            if not clean_name:
                await message.reply_text(
                    f"❌ Could not process filename: {file_name}\n"
                    "Please make sure the filename contains a movie name."
                )
                return
            
            existing = index.search_movie(clean_name)
            if existing:
                await message.reply_text(
                    f"⚠️ Movie already exists in index!\n"
                    f"📁 File: {file_name}\n"
                    f"🔍 Search as: {clean_name}\n\n"
                    f"💡 Users can already search for this movie."
                )
                return
            
            success = index.add_movie_manually(
                movie_name=clean_name,
                file_name=file_name,
                message_id=message_id,
                file_type=file_type,
                file_size=file_size,
                file_id=file_id
            )
            
            if not success:
                await message.reply_text(
                    f"❌ Failed to add movie to index.\n"
                    f"File: {file_name}"
                )
                return
            
            size_text = ""
            if file_size:
                size_mb = file_size / (1024 * 1024)
                if size_mb > 1024:
                    size_text = f" ({size_mb/1024:.1f} GB)"
                else:
                    size_text = f" ({size_mb:.1f} MB)"
            
            await message.reply_text(
                f"✅ *Movie added to index!*\n\n"
                f"📁 File: {file_name}{size_text}\n"
                f"🔍 Search as: `{clean_name}`\n"
                f"📌 Type: {file_type}\n"
                f"🆔 Message ID: {message_id}\n\n"
                f"💡 Users can now search for this movie!",
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Indexed: {clean_name} → {file_name} (msg_id: {message_id})")
            
        except Exception as e:
            logger.error(f"Error handling forwarded movie: {e}")
            try:
                message = update.effective_message
                if message:
                    await message.reply_text(
                        f"❌ Error: {str(e)}\n\n"
                        "Please make sure you're forwarding a movie file from your channel."
                    )
            except:
                pass
    
    @staticmethod
    async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command"""
        message = update.effective_message
        if not message:
            return
            
        if not context.args:
            await message.reply_text(
                "⚠️ Please provide a movie name.\n"
                "Example: `/search Inception`",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args)
        await message.reply_text(f"🔍 Searching for: *{query}*...", parse_mode='Markdown')
        
        try:
            index = MovieHandlers.get_index()
            
            if index is None:
                await message.reply_text(
                    "❌ Index is still initializing. Please wait a moment and try again."
                )
                return
            
            results = index.search_movie(query)
            
            if results:
                await message.reply_text(
                    f"✅ Found {len(results)} movie(s) in channel!"
                )
                
                for idx, result in enumerate(results, 1):
                    try:
                        await MovieHandlers.send_movie_from_channel(
                            update, context, result
                        )
                        if idx < len(results):
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error sending file {idx}: {e}")
                        await message.reply_text(
                            f"❌ Could not send movie #{idx}: {result.get('file_name', 'Unknown')}"
                        )
            else:
                await message.reply_text(
                    f"❌ Movie '{query}' not found in channel.\n"
                    "📚 Showing movie details from OMDb instead..."
                )
                
                movie = api_manager.get_movie(query)
                if movie:
                    await message.reply_text(
                        movie.format_message(),
                        parse_mode='Markdown'
                    )
                else:
                    await message.reply_text(
                        f"❌ No movie found for: *{query}*\n"
                        "Please check the spelling.",
                        parse_mode='Markdown'
                    )
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            await message.reply_text("❌ An error occurred. Please try again later.")
    
    @staticmethod
    async def send_movie_from_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, result: dict):
        """Send movie file from channel"""
        message = update.effective_message
        if not message:
            return
            
        try:
            message_id = result.get('message_id')
            file_name = result.get('file_name', 'Unknown')
            file_size = result.get('file_size', 0)
            
            size_text = ""
            if file_size:
                size_mb = file_size / (1024 * 1024)
                if size_mb > 1024:
                    size_text = f" ({size_mb/1024:.1f} GB)"
                else:
                    size_text = f" ({size_mb:.1f} MB)"
            
            try:
                forwarded = await context.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=Config.CHANNEL_ID,
                    message_id=message_id
                )
                
                await message.reply_text(
                    f"✅ *{file_name}*{size_text}\n"
                    "📤 File sent successfully!",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Forward failed: {e}")
                await message.reply_text(
                    f"❌ Could not send: {file_name}\n"
                    "The file may be too large or unavailable."
                )
            
        except Exception as e:
            logger.error(f"Error sending movie: {e}")
            await message.reply_text(
                f"❌ Error sending file. Please try again later."
            )
    
    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command"""
        message = update.effective_message
        if not message:
            return
            
        index = MovieHandlers.get_index()
        
        if index is None:
            await message.reply_text(
                "❌ Index is still initializing. Please wait a moment."
            )
            return
        
        stats = index.get_stats()
        
        stats_text = (
            "📊 *Bot Statistics*\n\n"
            f"📁 Channel Movies: {stats['total_movies']}\n"
            f"🔄 Last Updated: {stats['last_updated'] or 'Never'}\n"
            f"📈 Status: {'🟢 Ready' if stats['is_ready'] else '🟡 Initializing...'}\n\n"
            "🔗 *Sources:*\n"
            "• Channel Index (Primary)\n"
            "• OMDb API (Fallback)\n\n"
            "💡 *To add movies:*\n"
            "Forward them from your channel to this bot!"
        )
        await message.reply_text(stats_text, parse_mode='Markdown')
    
    @staticmethod
    async def update_index(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /update command - manually update index"""
        message = update.effective_message
        if not message:
            return
            
        await message.reply_text("🔄 Updating channel index... Please wait.")
        
        try:
            index = MovieHandlers.get_index()
            
            if index is None:
                await message.reply_text(
                    "❌ Index is still initializing. Please wait a moment and try again."
                )
                return
            
            success = await index.build_index(context)
            if success:
                stats = index.get_stats()
                await message.reply_text(
                    f"✅ Index updated successfully!\n\n"
                    f"📁 Total Movies: {stats['total_movies']}\n"
                    f"🔄 Last Updated: {stats['last_updated']}"
                )
            else:
                await message.reply_text(
                    "❌ Failed to update index. Please check:\n"
                    "1. Bot is admin in the channel\n"
                    "2. Channel ID is correct in .env\n"
                    "3. Bot has read permissions\n\n"
                    "💡 Alternatively, forward movies manually to this bot."
                )
        except Exception as e:
            logger.error(f"Update index error: {e}")
            await message.reply_text(f"❌ Error updating index: {str(e)}")
    
    @staticmethod
    async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /about command"""
        message = update.effective_message
        if not message:
            return
            
        about_text = (
            "🤖 *Movie Bot*\n"
            "Version: 2.0.0\n\n"
            "📁 *Channel Integration*\n"
            "• Searches your private channel first\n"
            "• Sends movie files directly\n"
            "• Falls back to OMDb API\n\n"
            "📤 *Adding Movies:*\n"
            "Forward any movie from your channel to this bot\n"
            "The bot will automatically index it\n\n"
            "✨ *Features:*\n"
            "• Smart filename matching\n"
            "• Auto-update every 24 hours\n"
            "• Manual update with /update\n"
            "• Multiple file format support\n\n"
            "Made with ❤️ using Python"
        )
        await message.reply_text(about_text, parse_mode='Markdown')
    
    @staticmethod
    async def handle_movie_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages as movie queries"""
        message = update.effective_message
        if not message:
            return
            
        movie_name = message.text.strip()
        
        if len(movie_name) < 2:
            await message.reply_text("🤔 Please send a valid movie name (at least 2 characters).")
            return
        
        await message.chat.send_action(action="typing")
        
        try:
            index = MovieHandlers.get_index()
            
            if index is None:
                await message.reply_text(
                    "⏳ Index is still initializing. Please wait a moment and try again."
                )
                return
            
            results = index.search_movie(movie_name)
            
            if results:
                await message.reply_text(
                    f"✅ Found {len(results)} movie(s) in channel!"
                )
                
                for idx, result in enumerate(results, 1):
                    try:
                        await MovieHandlers.send_movie_from_channel(
                            update, context, result
                        )
                        if idx < len(results):
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error sending file {idx}: {e}")
                        await message.reply_text(
                            f"❌ Could not send movie #{idx}: {result.get('file_name', 'Unknown')}"
                        )
            else:
                await message.reply_text(
                    f"🔍 Searching OMDb for: *{movie_name}*...\n"
                    "(Not found in channel)\n\n"
                    "💡 To add this movie, forward it from your channel to this bot.",
                    parse_mode='Markdown'
                )
                
                movie = api_manager.get_movie(movie_name)
                if movie:
                    if movie.poster and movie.poster.startswith('http') and movie.poster != 'N/A':
                        try:
                            await message.reply_photo(
                                photo=movie.poster,
                                caption=movie.format_message(),
                                parse_mode='Markdown'
                            )
                        except Exception:
                            await message.reply_text(
                                movie.format_message(),
                                parse_mode='Markdown'
                            )
                    else:
                        await message.reply_text(
                            movie.format_message(),
                            parse_mode='Markdown'
                        )
                else:
                    await message.reply_text(
                        f"❌ Movie not found anywhere!\n"
                        f"Query: *{movie_name}*\n\n"
                        "💡 Try:\n"
                        "• Check spelling\n"
                        "• Use exact title\n"
                        "• Add year (e.g., 'Inception 2010')\n"
                        "• Forward the movie to this bot to add it",
                        parse_mode='Markdown'
                    )
                
        except Exception as e:
            logger.error(f"Error processing movie query: {e}")
            await message.reply_text(
                "❌ Oops! Something went wrong.\nPlease try again later."
            )
