# get_channel_id.py
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Channel ID: {chat_id}")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", get_id))
app.run_polling()