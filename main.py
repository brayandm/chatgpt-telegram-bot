from dotenv import load_dotenv
from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
import logging
import os

load_dotenv()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def is_user_allowed(user_id):
    users_allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS").split(",")

    return str(user_id) in users_allowed

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_user_allowed(update.effective_user.id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not allowed to use this bot.")
        return

    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm ChatGPT, please talk to me!")

async def chatgpt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_user_allowed(update.effective_user.id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not allowed to use this bot.")
        return
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Chatgpt: hi")

if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()
    
    start_handler = CommandHandler('start', start)
    chatgpt_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), chatgpt)

    application.add_handler(start_handler)
    application.add_handler(chatgpt_handler)
    
    application.run_polling()