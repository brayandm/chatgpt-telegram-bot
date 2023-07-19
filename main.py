from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
from functools import wraps
import mysql.connector
import threading
import logging
import openai
import time
import os

load_dotenv()

markup = ReplyKeyboardMarkup([["💰 Quota"]])

config = {
    "user": os.environ.get("DB_USERNAME"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "database": os.environ.get("DB_DATABASE"),
    "port": os.environ.get("DB_PORT"),
}

init_conn = mysql.connector.connect(**config)

init_conn.cursor().execute(
    "CREATE TABLE IF NOT EXISTS users (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, user_id BIGINT, quota BIGINT, token_usage BIGINT)"
)

init_conn.cursor().execute(
    "CREATE TABLE IF NOT EXISTS tasks (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, user_id BIGINT, input VARCHAR(5000), output VARCHAR(5000))"
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

openai.api_key = os.environ.get("OPENAI_API_KEY")

def manage_db_connection(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        conn = mysql.connector.connect(**config)
        try:
            result = await func(conn, *args, **kwargs)
        finally:
            conn.close()
        return result
    return wrapper

def get_quota(conn, user_id):

    cursor = conn.cursor()

    cursor.execute("SELECT quota FROM users WHERE user_id = %s", (user_id,))

    result = cursor.fetchone()

    if result is None:
        
        cursor.execute("INSERT INTO users (user_id, quota, token_usage) VALUES (%s, %s, %s)", (user_id, 0, 0))
        
        conn.commit()

        return 0
    
    return result[0]

def get_token_usage(conn, user_id):

    cursor = conn.cursor()

    cursor.execute("SELECT token_usage FROM users WHERE user_id = %s", (user_id,))

    result = cursor.fetchone()

    if result is None:
        
        cursor.execute("INSERT INTO users (user_id, quota, token_usage) VALUES (%s, %s, %s)", (user_id, 0, 0))
        
        conn.commit()

        return 0
    
    return result[0]
    
    
def set_quota(conn, user_id, quota):

    cursor = conn.cursor()

    cursor.execute("UPDATE users SET quota = %s WHERE user_id = %s", (quota, user_id))

    conn.commit()

def set_token_usage(conn, user_id, token_usage):
    
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET token_usage = %s WHERE user_id = %s", (token_usage, user_id))

    conn.commit()
    

def shrink_text(text, max_length=5000):
    
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    
    return text

def create_task(conn, user_id, input, output):

    cursor = conn.cursor()

    cursor.execute("INSERT INTO tasks (user_id, input, output) VALUES (%s, %s, %s)", (user_id, shrink_text(input), shrink_text(output)))

    conn.commit()

def get_last_bot_message(conn, user_id):

    cursor = conn.cursor()

    cursor.execute("SELECT output FROM tasks WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))

    result = cursor.fetchone()

    if result is None:
        return None
    
    return result[0]

async def send_typing_action(context, chat_id):
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

@manage_db_connection
async def chatgpt(conn, update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    quota = get_quota(conn, update.effective_user.id)

    token_usage = get_token_usage(conn, update.effective_user.id)
    
    if quota <= 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You have no quota left.", reply_markup=markup)
        return
    
    if len(update.message.text) > 500:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Your message is too long.", reply_markup=markup)
        return
    
    response = None

    def get_chatgpt_response(conn, user_id, text):

        nonlocal response

        last_bot_message = get_last_bot_message(conn, user_id)
        
        chat = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Also your answers are brief and to the point."
            }
        ]

        if last_bot_message is not None:

            chat.append({
                "role": "assistant",
                "content": last_bot_message
            })

        chat.append({
            "role": "user",
            "content": text
        })

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat,
        )

    thread = threading.Thread(target=get_chatgpt_response, args=(conn, update.effective_user.id, update.message.text))

    thread.start()

    start_time = None

    while True:

        if not thread.is_alive():
            break

        if start_time is None or time.time() - start_time > 5:

            start_time = time.time()

            await send_typing_action(context, update.effective_chat.id)

        time.sleep(0.1)

    thread.join()
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response["choices"][0]["message"]["content"], reply_markup=markup)
    
    quota -= response["usage"]["total_tokens"]

    token_usage += response["usage"]["total_tokens"]
    
    create_task(conn, update.effective_user.id, update.message.text, response["choices"][0]["message"]["content"])
    
    set_quota(conn, update.effective_user.id, quota)   

    set_token_usage(conn, update.effective_user.id, token_usage) 


@manage_db_connection
async def get_user_quota(conn, update: Update, context: ContextTypes.DEFAULT_TYPE):
        
        quota = get_quota(conn, update.effective_user.id)
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have {quota} tokens left.", reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm ChatGPT, please talk to me!", reply_markup=markup)

if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()
    
    start_handler = CommandHandler('start', start)
    quota_handler = MessageHandler(filters.Regex('💰 Quota'), get_user_quota)
    chatgpt_handler = MessageHandler(filters.TEXT & (~filters.COMMAND) & (~filters.Regex('💰 Quota')), chatgpt)

    application.add_handler(start_handler)
    application.add_handler(chatgpt_handler)
    application.add_handler(quota_handler)
    
    application.run_polling()