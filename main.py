from dotenv import load_dotenv
from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
import mysql.connector
import logging
import openai
import os

load_dotenv()

config = {
    "user": os.environ.get("DB_USERNAME"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "database": os.environ.get("DB_DATABASE"),
    "port": os.environ.get("DB_PORT"),
}

conn = mysql.connector.connect(**config)

cursor = conn.cursor()

cursor.execute(
    "CREATE TABLE IF NOT EXISTS users (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, user_id BIGINT, quota BIGINT)"
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

openai.api_key = os.environ.get("OPENAI_API_KEY")

def get_usage():

    with open("usage.txt", "r") as f:
        return f.read()
    
def set_usage(usage):

    with open("usage.txt", "w") as f:
        f.write(usage)

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
    
    if len(update.message.text) > 500:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Your message is too long.")
        return
    
    usage = get_usage()

    if usage == "":
        usage = "0"
    
    if int(usage) > 50000:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You have exceeded the usage limit.")
        return
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": update.message.text,
            },
        ],
    )
    
    usage = int(usage) + response["usage"]["total_tokens"]

    set_usage(str(usage))

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response["choices"][0]["message"]["content"])

if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()
    
    start_handler = CommandHandler('start', start)
    chatgpt_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), chatgpt)

    application.add_handler(start_handler)
    application.add_handler(chatgpt_handler)
    
    application.run_polling()