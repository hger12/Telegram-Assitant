from telethon import TelegramClient, events  # Telegram bot framework
import os
from dotenv import load_dotenv  # To load secrets from .env file
import dateparser  # Natural language time parser
from datetime import datetime
import json  # For saving messages and reminders
from dateutil.relativedelta import relativedelta  # For time differences
import re
import asyncio
from telethon.tl.functions.messages import GetHistoryRequest  # For history access (unused here)
from langchain.llms import OpenAI  # ChatGPT connection

# === Load secrets from .env ===
load_dotenv(dotenv_path='/Users/user/bot_env.env')

api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
openai_api_key = os.getenv('OPENAI_API_KEY')

# === Set up Telegram bot ===
client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

# === Message logging ===
MESSAGE_FILE = "messages.json"
seen_messages = []

if not os.path.exists(MESSAGE_FILE):
    with open(MESSAGE_FILE, "w") as f:
        json.dump([], f)

with open(MESSAGE_FILE, "r") as f:
    raw = json.load(f)
    seen_messages = [m for m in raw if isinstance(m, dict) and "text" in m and "timestamp" in m]

def save_messages():
    with open(MESSAGE_FILE, "w") as f:
        json.dump(seen_messages, f)

# === Helpers for time ===
def parse_timeframe_arg(arg):
    match = re.match(r"^(\d+)([mhd])$", arg)
    if not match:
        return relativedelta(hours=1)  # default 1h
    value, unit = int(match[1]), match[2]
    return {
        'm': relativedelta(minutes=value),
        'h': relativedelta(hours=value),
        'd': relativedelta(days=value)
    }[unit]

def parse_natural_time(text):
    return dateparser.parse(
        text,
        settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now(),
            'PARSERS': ['relative-time', 'absolute-time'],
        }
    )

# === Reminder storage ===
REMINDER_FILE = "reminders.json"

if not os.path.exists(REMINDER_FILE):
    with open(REMINDER_FILE, "w") as f:
        json.dump([], f)

def load_reminders():
    with open(REMINDER_FILE, "r") as f:
        data = json.load(f)
        return [r for r in data if isinstance(r, dict) and "chat_id" in r and "text" in r and "time" in r]

def save_reminders(reminders):
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f)

# === LangChain GPT integration ===
llm = OpenAI(api_key=openai_api_key)

async def get_chatgpt_response(prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, llm.invoke, prompt)

async def summarize_messages(messages):
    prompt = "Summarize the following messages:\n" + "\n".join(messages)
    return await get_chatgpt_response(prompt)

# === /summarize command ===
@client.on(events.NewMessage(pattern='/summarize'))
async def summarize_handler(event):
    args = event.raw_text.strip().split()
    delta = parse_timeframe_arg(args[1]) if len(args) > 1 else relativedelta(hours=1)
    if not seen_messages:
        await event.reply("No messages seen yet.")
        return

    cutoff = datetime.now() - delta
    filtered = [m["text"] for m in seen_messages if "timestamp" in m and datetime.fromisoformat(m["timestamp"]) >= cutoff]
    if not filtered:
        filtered = [m["text"] for m in seen_messages]

    await event.reply(f"Summarizing {len(filtered)} messages...")
    try:
        summary = await summarize_messages(filtered)
        await event.reply(f"📝 Summary:\n\n{summary}")
    except Exception as e:
        await event.reply(f"Error during summarization: {str(e)}")

# === /ask command ===
@client.on(events.NewMessage(pattern='/ask'))
async def ask_handler(event):
    user_input = event.raw_text[len('/ask '):].strip()
    if not user_input:
        await event.reply("Type a question after /ask.")
        return
    await event.reply("Processing...")
    response = await get_chatgpt_response(user_input)
    await event.reply(response)

# === /ping command ===
@client.on(events.NewMessage(pattern="/ping"))
async def ping_handler(event):
    await event.reply("pong!")

# === Reminder system ===
pending_reminders = {}  # For missing time follow-ups

@client.on(events.NewMessage(pattern=r"/reminder\s+(.*)"))
async def reminder_handler(event):
    chat_id = event.chat_id
    text = event.pattern_match.group(1)
    time = parse_natural_time(text)

    if time:
        await schedule_reminder(chat_id, text, time)
        await event.reply(f"✅ Reminder set for {time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        pending_reminders[chat_id] = text
        await event.reply("⏱ When should I remind you? (e.g. 'in 30 minutes')")

@client.on(events.NewMessage(pattern=r"^/reminders$"))
async def list_reminders(event):
    reminders = load_reminders()
    chat_reminders = [r for r in reminders if r["chat_id"] == event.chat_id]
    if not chat_reminders:
        await event.reply("📭 No reminders.")
    else:
        msg = "📌 Reminders:\n"
        for i, r in enumerate(chat_reminders):
            time = datetime.fromisoformat(r["time"]).strftime('%Y-%m-%d %H:%M:%S')
            msg += f"{i+1}. {r['text']} — at {time}\n"
        await event.reply(msg)

@client.on(events.NewMessage(pattern=r"^/cancel(?:\s+(\d+|all))?$"))
async def cancel_reminder(event):
    arg = event.pattern_match.group(1)
    reminders = load_reminders()
    chat_reminders = [r for r in reminders if r["chat_id"] == event.chat_id]

    if not arg:
        await event.reply("Usage: `/cancel 1` or `/cancel all`")
        return

    if arg == "all":
        reminders = [r for r in reminders if r["chat_id"] != event.chat_id]
        save_reminders(reminders)
        await event.reply("🗑 All reminders cancelled.")
    else:
        try:
            index = int(arg) - 1
            target = chat_reminders[index]
            reminders.remove(target)
            save_reminders(reminders)
            await event.reply(f"❌ Removed: {target['text']}")
        except (IndexError, ValueError):
            await event.reply("⚠ Invalid number.")

# === Store new reminders ===
async def schedule_reminder(chat_id, text, time):
    reminders = load_reminders()
    reminders.append({"chat_id": chat_id, "text": text, "time": time.isoformat()})
    save_reminders(reminders)

# === Fire reminders on time ===
async def reminder_checker():
    while True:
        await asyncio.sleep(5)
        reminders = load_reminders()
        now = datetime.now()
        updated = []
        for r in reminders:
            if datetime.fromisoformat(r["time"]) <= now:
                await client.send_message(r["chat_id"], f"🔔 Reminder: {r['text']}")
            else:
                updated.append(r)
        save_reminders(updated)

# === Log all chat messages ===
@client.on(events.NewMessage)
async def catch_all_messages(event):
    chat_id = event.chat_id
    msg_text = event.raw_text.strip()

    if msg_text and not msg_text.startswith("/"):
        seen_messages.append({"text": msg_text, "timestamp": datetime.now().isoformat()})
        save_messages()

    if chat_id in pending_reminders and not msg_text.startswith("/"):
        time = parse_natural_time(msg_text)
        if time:
            text = pending_reminders.pop(chat_id)
            await schedule_reminder(chat_id, text, time)
            await event.reply(f"✅ Reminder set for {time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            await event.reply("❌ I couldn't understand that time. Try again.")

# === Start bot ===
print("Bot is running...")
client.loop.create_task(reminder_checker())
client.run_until_disconnected()
