# chatgpt-telegram-bot

A Telegram bot that lets users chat with OpenAI's ChatGPT (`gpt-3.5-turbo`) directly from Telegram. It tracks a per-user token quota and cumulative token usage in a MySQL database, and ships with Docker/Docker Compose configs for running the bot and database together.

## Features

- **Chat with ChatGPT from Telegram**, any plain-text message (that isn't a command or a menu button) is sent to OpenAI's `gpt-3.5-turbo` chat completion endpoint, with the previous bot reply included as context for continuity.
- **Per-user quota tracking**, each Telegram user gets a `quota` and `token_usage` counter stored in a MySQL `users` table; every completed request debits the quota by the number of tokens used and no requests are served once quota reaches zero.
- **Usage history**, every input/output pair is logged to a `tasks` table (truncated to 5000 characters).
- **Simple reply-keyboard menu** with two buttons:
  - 💰 **Quota**, shows remaining tokens (`/get_user_quota`)
  - 📈 **Usage**, shows total tokens used so far (`/get_user_usage`)
- **Typing indicator**, the bot sends a "typing…" chat action while waiting on the OpenAI response.
- **Message length guard**, incoming messages longer than 500 characters are rejected with a notice.
- **Dockerized**, a bot container (Python 3.11, auto-restarts on file changes via `watchmedo`) plus a MySQL container, wired together with Docker Compose.

## Tech stack

- Python 3.11
- [`python-telegram-bot`](https://pypi.org/project/python-telegram-bot/) for the Telegram integration
- [`openai`](https://pypi.org/project/openai/) Python SDK (legacy `openai.ChatCompletion` API)
- `mysql-connector-python` for persistence
- `python-dotenv` for environment configuration
- Docker / Docker Compose, MySQL

## Project structure

```
main.py                     # Bot entrypoint: handlers, OpenAI calls, quota/usage logic
Pipfile / Pipfile.lock       # Python dependencies (pipenv)
docker-compose.yml           # Dev compose file (bot + mysql services)
docker-compose.prod.yml      # Production compose overrides
docker/Dockerfile-bot        # Bot image (installs deps from Pipfile, auto-restarts on changes)
docker/Dockerfile-mysql      # MySQL image
docker/mysql/my.cnf          # MySQL configuration
.env.example                 # Required environment variables
```

## Setup & usage

1. Copy the example environment file and fill in your credentials:

   ```bash
   cp .env.example .env
   ```

   Required variables (see `.env.example`):

   ```
   TELEGRAM_BOT_TOKEN=
   OPENAI_API_KEY=

   DB_DATABASE=telegram_bot
   DB_USERNAME=user
   DB_PASSWORD=password
   DB_HOST=mysql
   DB_PORT=3306
   ```

2. Build and start the bot and MySQL database with Docker Compose:

   ```bash
   docker-compose up --build
   ```

   The bot container installs dependencies from the `Pipfile`, waits for MySQL to become healthy, and runs `main.py` (auto-restarting on code changes during development). A production override is available via `docker-compose.prod.yml`.

3. On startup, the bot automatically creates the `users` and `tasks` tables in MySQL if they don't already exist.

4. Message your bot on Telegram, send `/start` to get the welcome message and keyboard, then send any text to chat with ChatGPT. Use the **💰 Quota** and **📈 Usage** keyboard buttons to check your remaining/used tokens.

Note: new users start with a quota of `0`, so quota values need to be set in the `users` table (e.g. directly in MySQL) before a user can send chat messages.
