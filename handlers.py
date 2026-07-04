# handlers.py - Fixed version
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
        
        index = MovieHandlers.get_index()
        movie_count = len(index.index) if index else 0
        
        welcome_message = (
            f"🎬 *Welcome to Movie Bot, {user_name}!*\n\n"
            f"📊 Index has *{movie_count}* movies\n\n"
            "Send me any movie name and I'll search for it!\n\n"
            "📌 *Commands:*\n"
            "/start - Show this message\n"
            "/help - Show help\n"
            "/search <movie_name> - Search for a movie\n"
            "/stats - Show bot statistics\n"
            "/about - About this bot\n\n"
            "📁 *How to add movies:*\n"
            "1️⃣ Forward a movie file from your channel to this bot\n"
            "2️⃣ Or send a movie file directly to this bot\n"
            "3️⃣ The bot will index it\n\n"
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
            "📌 *Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/search <movie_name> - Search for a movie\n"
            "/stats - Show bot statistics\n"
            "/about - About this bot\n\n"
            "📁 *Adding Movies:*\n"
            "1. Forward a movie file from your channel to this bot\n"
            "2. Or send a movie file directly to this bot\n"
            "3. The bot will index it\n\n"
            "📌 *File Types Supported:*\n"
            "• Video files (.mp4, .mkv, .avi, etc.)\n"
            "• Document files\n"
            "• Audio files\n\n"
            "🔍 *Search Tips:*\n"
            "• Try exact movie names\n"
            "• Partial names work too"
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
            
            file_info = MovieHandlers._extract_file_info(channel_post)
            if not file_info:
                logger.info("📨 Channel post has no file, ignoring")
                return
            
            index = MovieHandlers.get_index()
            if index is None:
                logger.warning("Index not initialized")
                return
            
            existing = index.search_movie(file_info['clean_name'])
            if existing:
                logger.info(f"Movie already exists: {file_info['clean_name']}")
                return
            
            # Store the channel message_id for forwarding
            success = index.add_movie_manually(
                movie_name=file_info['clean_name'],
                file_name=file_info['file_name'],
                message_id=channel_post.message_id,  # Original channel message ID
                file_type=file_info['file_type'],
                file_size=file_info['file_size'],
                file_id=file_info['file_id'],
                from_chat_id=channel_post.chat.id
            )
            
            if success:
                logger.info(f"✅ Indexed from channel post: {file_info['clean_name']}")
            
        except Exception as e:
            logger.error(f"Error handling channel post: {e}")
    
    @staticmethod
    async def handle_forwarded_movie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle forwarded movie messages to add to index"""
        try:
            message = update.effective_message
            if not message:
                return
            
            logger.info(f"📨 Received message from user {message.from_user.id}")
            
            # Extract file info from the message
            file_info = MovieHandlers._extract_file_info(message)
            if not file_info:
                await message.reply_text(
                    "❌ This message doesn't contain a file.\n"
                    "Please forward a message with a movie file or send a file directly."
                )
                return
            
            logger.info(f"📁 File detected: {file_info['file_name']} ({file_info['file_type']}, {file_info['file_size']} bytes)")
            
            # Check if it's forwarded from a channel
            is_forwarded = message.forward_from_chat is not None
            
            if is_forwarded:
                source_chat = message.forward_from_chat
                logger.info(f"📨 Forwarded from channel: {source_chat.title if source_chat.title else source_chat.id}")
                
                # IMPORTANT: For forwarded messages, the message_id in the index
                # should be the ORIGINAL message_id in the channel
                # But we can't access it directly. 
                # Instead, we store the file_id and use it directly.
                
                # Store the file_id directly (not message_id)
                success = await MovieHandlers._add_movie_to_index(
                    update, context, message, file_info, 
                    use_file_id=True  # Use file_id instead of message_id
                )
            else:
                # Direct upload - use the current message_id
                logger.info("📨 Direct file upload")
                success = await MovieHandlers._add_movie_to_index(
                    update, context, message, file_info,
                    use_file_id=False
                )
            
        except Exception as e:
            logger.error(f"Error handling forwarded movie: {e}")
            try:
                message = update.effective_message
                if message:
                    await message.reply_text(
                        f"❌ Error: {str(e)}\n\n"
                        "Please make sure you're sending a movie file."
                    )
            except:
                pass
    
    @staticmethod
    def _extract_file_info(message):
        """Extract file info from a message"""
        try:
            file_name = None
            file_id = None
            file_type = None
            file_size = None
            
            # Check document (most common for movie files)
            if message.document:
                file_name = message.document.file_name
                file_id = message.document.file_id
                file_type = "document"
                file_size = message.document.file_size
                logger.info(f"📄 Found document: {file_name}")
            
            # Check video
            elif message.video:
                file_name = message.video.file_name
                file_id = message.video.file_id
                file_type = "video"
                file_size = message.video.file_size
                logger.info(f"🎬 Found video: {file_name}")
            
            # Check audio
            elif message.audio:
                file_name = message.audio.file_name
                file_id = message.audio.file_id
                file_type = "audio"
                file_size = message.audio.file_size
                logger.info(f"🎵 Found audio: {file_name}")
            
            if not file_name:
                return None
            
            # Get clean name
            index = MovieHandlers.get_index()
            if index:
                clean_name = index.clean_filename(file_name)
            else:
                clean_name = file_name.lower().strip()
                if '.' in clean_name:
                    clean_name = clean_name.rsplit('.', 1)[0]
            
            return {
                'file_name': file_name,
                'clean_name': clean_name,
                'file_id': file_id,
                'file_type': file_type,
                'file_size': file_size
            }
        except Exception as e:
            logger.error(f"Error extracting file info: {e}")
            return None
    
    @staticmethod
    async def _add_movie_to_index(update, context, message, file_info, use_file_id=False):
        """Add movie to index and notify user"""
        index = MovieHandlers.get_index()
        if index is None:
            await message.reply_text("❌ Index not initialized yet. Please try again in a moment.")
            return False
        
        if not file_info['clean_name']:
            await message.reply_text(
                f"❌ Could not process filename: {file_info['file_name']}\n"
                "Please make sure the filename contains a movie name."
            )
            return False
        
        # Check if already exists
        existing = index.search_movie(file_info['clean_name'])
        if existing:
            await message.reply_text(
                f"⚠️ Movie already exists in index!\n"
                f"📁 File: `{file_info['file_name']}`\n"
                f"🔍 Search as: `{file_info['clean_name']}`\n\n"
                f"💡 Users can already search for this movie.",
                parse_mode='Markdown'
            )
            return False
        
        # Add to index
        success = index.add_movie_manually(
            movie_name=file_info['clean_name'],
            file_name=file_info['file_name'],
            message_id=message.message_id,  # This is the message ID in the current chat
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            file_id=file_info['file_id'],  # Store the file_id for direct sending
            from_chat_id=message.chat.id
        )
        
        if not success:
            await message.reply_text(
                f"❌ Failed to add movie to index.\n"
                f"File: `{file_info['file_name']}`",
                parse_mode='Markdown'
            )
            return False
        
        # Format file size
        size_text = ""
        if file_info['file_size']:
            size_mb = file_info['file_size'] / (1024 * 1024)
            if size_mb > 1024:
                size_text = f" ({size_mb/1024:.1f} GB)"
            else:
                size_text = f" ({size_mb:.1f} MB)"
        
        await message.reply_text(
            f"✅ *Movie added to index!*\n\n"
            f"📁 File: `{file_info['file_name']}`{size_text}\n"
            f"🔍 Search as: `{file_info['clean_name']}`\n"
            f"📌 Type: {file_info['file_type']}\n\n"
            f"💡 Users can now search for this movie!",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Indexed: {file_info['clean_name']} → {file_info['file_name']}")
        return True
    
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
        await MovieHandlers._perform_search(update, context, query)
    
    @staticmethod
    async def handle_movie_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages as movie queries"""
        message = update.effective_message
        if not message:
            return
        
        query = message.text.strip()
        
        if len(query) < 2:
            await message.reply_text("🤔 Please send a valid movie name (at least 2 characters).")
            return
        
        await message.chat.send_action(action="typing")
        await MovieHandlers._perform_search(update, context, query)
    
    @staticmethod
    async def _perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Perform movie search"""
        message = update.effective_message
        if not message:
            return
        
        try:
            index = MovieHandlers.get_index()
            
            if index is None:
                await message.reply_text(
                    "⏳ Index is still initializing. Please wait a moment and try again."
                )
                return
            
            # Search in channel first
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
                # Not found - try OMDb
                await message.reply_text(
                    f"🔍 Searching OMDb for: *{query}*...\n\n"
                    f"💡 To add this movie, forward it from your channel to this bot.",
                    parse_mode='Markdown'
                )
                
                movie = api_manager.get_movie(query)
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
                        f"❌ Movie not found!\n"
                        f"Query: *{query}*\n\n"
                        "💡 Try:\n"
                        "• Check spelling\n"
                        "• Use exact title\n"
                        "• Forward the movie to this bot to add it",
                        parse_mode='Markdown'
                    )
                
        except Exception as e:
            logger.error(f"Error processing movie query: {e}")
            await message.reply_text(
                "❌ Oops! Something went wrong.\nPlease try again later."
            )
    
    @staticmethod
    async def send_movie_from_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, result: dict):
        """Send movie file from channel"""
        message = update.effective_message
        if not message:
            return
            
        try:
            file_name = result.get('file_name', 'Unknown')
            file_size = result.get('file_size', 0)
            file_id = result.get('file_id')  # Get stored file_id
            message_id = result.get('message_id')
            
            # Format file size
            size_text = ""
            if file_size:
                size_mb = file_size / (1024 * 1024)
                if size_mb > 1024:
                    size_text = f" ({size_mb/1024:.1f} GB)"
                else:
                    size_text = f" ({size_mb:.1f} MB)"
            
            logger.info(f"📤 Sending file: {file_name}")
            
            # Try different methods to send the file
            
            # Method 1: If we have file_id, send it directly
            if file_id:
                try:
                    # Try to send using file_id
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file_id,
                        caption=f"📁 {file_name}{size_text}"
                    )
                    await message.reply_text(
                        f"✅ *{file_name}*{size_text}\n"
                        "📤 File sent successfully!",
                        parse_mode='Markdown'
                    )
                    return
                except Exception as e:
                    logger.warning(f"Send by file_id failed: {e}")
            
            # Method 2: If we have message_id, try to forward from channel
            if message_id:
                try:
                    # Try to forward the message
                    await context.bot.forward_message(
                        chat_id=update.effective_chat.id,
                        from_chat_id=Config.CHANNEL_ID,
                        message_id=message_id
                    )
                    await message.reply_text(
                        f"✅ *{file_name}*{size_text}\n"
                        "📤 File sent successfully!",
                        parse_mode='Markdown'
                    )
                    return
                except Exception as e:
                    logger.warning(f"Forward failed: {e}")
                    
                    # Try to copy
                    try:
                        await context.bot.copy_message(
                            chat_id=update.effective_chat.id,
                            from_chat_id=Config.CHANNEL_ID,
                            message_id=message_id
                        )
                        await message.reply_text(
                            f"✅ *{file_name}*{size_text}\n"
                            "📤 File sent successfully!",
                            parse_mode='Markdown'
                        )
                        return
                    except Exception as e2:
                        logger.warning(f"Copy failed: {e2}")
            
            # Method 3: Ask user to forward again
            await message.reply_text(
                f"❌ Cannot send: *{file_name}*{size_text}\n\n"
                "The file is not accessible. Please forward the movie to the bot again.\n\n"
                "💡 When forwarding, the bot will store the file for future access.",
                parse_mode='Markdown'
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
        
        movie_names = list(index.index.keys())[:5] if index.index else []
        
        stats_text = (
            "📊 *Bot Statistics*\n\n"
            f"📁 Channel Movies: {stats['total_movies']}\n"
            f"🔄 Last Updated: {stats['last_updated'] or 'Never'}\n"
            f"📈 Status: {'🟢 Ready' if stats['is_ready'] else '🟡 Initializing...'}\n\n"
        )
        
        if movie_names:
            stats_text += "📽️ *Sample Movies:*\n"
            for name in movie_names:
                stats_text += f"• `{name}`\n"
            stats_text += "\n"
        
        stats_text += (
            "📁 *How to add movies:*\n"
            "Forward them from your channel to this bot!"
        )
        await message.reply_text(stats_text, parse_mode='Markdown')
    
    @staticmethod
    async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /about command"""
        message = update.effective_message
        if not message:
            return
            
        about_text = (
            "🤖 *Movie Bot*\n"
            "Version: 2.0.0\n\n"
            "📁 *How it works:*\n"
            "• Forward movies to the bot to index them\n"
            "• The bot stores file IDs for direct access\n"
            "• Search any movie name to get it\n\n"
            "📤 *Adding Movies:*\n"
            "Forward any movie from your channel to this bot\n\n"
            "✨ *Features:*\n"
            "• Smart filename matching\n"
            "• Direct file sending\n"
            "• OMDb fallback\n\n"
            "Made with ❤️ using Python"
        )
        await message.reply_text(about_text, parse_mode='Markdown')