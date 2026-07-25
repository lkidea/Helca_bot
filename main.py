import json
import os
import sys
import asyncio
import discord
from aiohttp import web
import simplemma

# ---------------------------------------------------------
# 1. Environment & Configuration Setup
# ---------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_CHANNELS_RAW = os.getenv("ALLOWED_CHANNEL_IDS", "")

ALLOWED_CHANNEL_IDS = set()
if ALLOWED_CHANNELS_RAW.strip():
    for channel_id in ALLOWED_CHANNELS_RAW.split(","):
        clean_id = channel_id.strip()
        if clean_id.isdigit():
            ALLOWED_CHANNEL_IDS.add(int(clean_id))

# Pre-load Czech language data for Simplemma in RAM
LANG_DATA = simplemma.load_data("cs")

# Load Triggers from triggers.json
TRIGGERS_FILE = "triggers.json"
if not os.path.exists(TRIGGERS_FILE):
    print(f"Error: Required file '{TRIGGERS_FILE}' was not found.")
    sys.exit(1)

with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
    TRIGGERS = json.load(f)

# Split into S and L lists at startup to optimize execution speed
S_TRIGGERS = [t for t in TRIGGERS if t.get("trigger_type") == "S"]
L_TRIGGERS = [t for t in TRIGGERS if t.get("trigger_type") == "L"]


# ---------------------------------------------------------
# 2. Discord Client Setup
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    if ALLOWED_CHANNEL_IDS:
        print(f"Listening exclusively to channel IDs: {list(ALLOWED_CHANNEL_IDS)}")
    else:
        print("Warning: ALLOWED_CHANNEL_IDS not set. Listening to ALL accessible channels.")


@client.event
async def on_message(message: discord.Message):
    # Ignore messages sent by bots (including self)
    if message.author.bot:
        return

    # Restrict to specified channels if configured
    if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    content_lower = message.content.lower()

    # Step A: Check 'S' (Exact Substring) Triggers
    for rule in S_TRIGGERS:
        target_str = rule["trigger"].lower()
        if target_str in content_lower:
            await execute_response(message, rule)
            return

    # Step B: If no 'S' trigger hit, process 'L' (Lemmatized) Triggers
    if L_TRIGGERS:
        tokens = simplemma.simple_tokenizer(message.content)
        extracted_lemmas = {
            simplemma.lemmatize(token, LANG_DATA).lower() for token in tokens
        }

        for rule in L_TRIGGERS:
            target_lemma = rule["trigger"].lower()
            if target_lemma in extracted_lemmas:
                await execute_response(message, rule)
                return


async def execute_response(message: discord.Message, rule: dict):
    text = rule["response"]
    resp_type = rule.get("response_type", "M").upper()

    if resp_type == "R":
        await message.reply(text)
    else:
        await message.channel.send(text)


# ---------------------------------------------------------
# 3. Dummy Web Server & Application Entry Point
# ---------------------------------------------------------
async def handle_health_check(request):
    return web.Response(text="Bot web service is active.")


async def main():
    if not DISCORD_TOKEN:
        print("Fatal Error: DISCORD_TOKEN environment variable is not defined.")
        sys.exit(1)

    # Start aiohttp HTTP server for Render / UptimeRobot pinging
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Dummy web server running on port {port}")

    # Start Discord Bot
    async with client:
        await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
