This is a Telegram bot built with Python using the Telethon library. It can:
- Set reminders using natural language
- List and cancel reminders
- Summarize recent messages
- Ask questions to ChatGPT (via OpenAI API)

---

## ✅ Features

### 🔔 Reminders
Set reminders using simple phrases like:
```
/reminder in 10 minutes walk the dog
/reminder at 6pm meeting with team
```

List them:
```
/reminders
```

Cancel one or all:
```
/cancel 1
/cancel all
```

### 📋 Summarize Chat
Summarize messages from the last hour (default) or a custom time:
```
/summarize
/summarize 3h
```

### 💬 Ask ChatGPT
Ask any question using:
```
/ask What is the capital of Japan?
```

---

## ⚙️ Installation
1. Clone the repository and install dependencies:
```bash
git clone https://github.com/yourusername/telegram-bot.git
cd telegram-bot
pip install -r requirements.txt
```

2. Create a `.env` file and fill it with your credentials:
```
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
```

3. Run the bot:
```bash
python your_bot_script.py
```

---

## 📁 Project Structure
```
├── reminders.json         # Stores scheduled reminders
├── messages.json          # Stores seen messages
├── bot_env.env            # Your environment variables
├── telegram_bot.py        # Main bot script
```

---

## 🧠 AI Usage
This bot uses the OpenAI GPT model via LangChain to:
- Summarize messages
- Answer questions from users

---

## ✍️ Author
**Mateo Brunet-Debaines, Armando Trivellato and Jaime Arrabal**

---

## 📝 License
This project is open-source for educational purposes.
