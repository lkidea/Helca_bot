import json
import os
import sys
import asyncio
import discord
from aiohttp import web
import random
# import re
from ufal.morphodita import Tagger, Forms, TaggedLemmas, TokenRanges

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
SL_TRIGGERS = [t for t in TRIGGERS if t.get("trigger_type") == "SL"]






# ---------------------------------------------------------
# MorphoDiTa Setup & Lemmatization Helper
# ---------------------------------------------------------
TAGGER_MODEL_PATH = "czech-morfflex-pdt-161115.tagger" # Ensure this file is in your directory

if not os.path.exists(TAGGER_MODEL_PATH):
    print(f"Fatal Error: MorphoDiTa model '{TAGGER_MODEL_PATH}' was not found.")
    sys.exit(1)

print("Loading MorphoDiTa tagger (this may take a few seconds)...")
tagger = Tagger.load(TAGGER_MODEL_PATH)
if not tagger:
    print("Fatal Error: Could not load the MorphoDiTa tagger model.")
    sys.exit(1)

# Pre-fetch the Morpho dictionary to avoid calling it repeatedly in the loop
morpho = tagger.getMorpho()

def get_lemmas_with_polarity(text: str) -> list:
    """
    Tokenizes and lemmatizes Czech text natively.
    Critically, it checks the PDT tag for polarity and prepends 'ne' 
    to the lemma if the word is grammatically negated.
    """
    if not text.strip():
        return []

    tokenizer = tagger.newTokenizer()
    tokenizer.setText(text)
    
    forms = Forms()
    lemmas = TaggedLemmas()
    tokens = TokenRanges()
    
    result_lemmas = []
    
    while tokenizer.nextSentence(forms, tokens):
        tagger.tag(forms, lemmas)
        for i in range(len(lemmas)):
            raw_lemma = lemmas[i].lemma
            tag = lemmas[i].tag
            
            # 1. Use MorphoDiTa's native method to perfectly clean the lemma
            clean_lemma = morpho.rawLemmaToLemma(raw_lemma).lower()

            # Filter out punctuation and symbols right away
            if clean_lemma.isalnum():

                # 2. Check for negation in the PDT tag (11th position, index 10)
                if len(tag) > 10 and tag[10] == 'N':
                    # Prepend 'ne' if it's not already there
                    if not clean_lemma.startswith("ne"):
                        clean_lemma = "ne" + clean_lemma
                    
                result_lemmas.append(clean_lemma)
            
    return result_lemmas
    



'''
# ---------------------------------------------------------
# MorphoDiTa Setup & Lemmatization Helper
# ---------------------------------------------------------
TAGGER_MODEL_PATH = "czech-morfflex-pdt-161115.tagger" # Ensure this file is in your directory

if not os.path.exists(TAGGER_MODEL_PATH):
    print(f"Fatal Error: MorphoDiTa model '{TAGGER_MODEL_PATH}' was not found.")
    sys.exit(1)

print("Loading MorphoDiTa tagger (this may take a few seconds)...")
tagger = Tagger.load(TAGGER_MODEL_PATH)
if not tagger:
    print("Fatal Error: Could not load the MorphoDiTa tagger model.")
    sys.exit(1)

def get_lemmas_with_polarity(text: str) -> list:
    """
    Tokenizes and lemmatizes Czech text. 
    Critically, it checks the PDT tag for polarity and prepends 'ne' 
    to the lemma if the word is grammatically negated.
    """
    if not text.strip():
        return []

    tokenizer = tagger.newTokenizer()
    tokenizer.setText(text)
    
    forms = Forms()
    lemmas = TaggedLemmas()
    tokens = TokenRanges()
    
    result_lemmas = []
    
    while tokenizer.nextSentence(forms, tokens):
        tagger.tag(forms, lemmas)
        for i in range(len(lemmas)):
            # 1. Get the raw PDT lemma (which often contains derivation info like 'stát-1_^(stát_se_něco)')
            pdt_lemma = lemmas[i].lemma
            tag = lemmas[i].tag
            
            # 2. Clean the lemma to get just the base word.
            # We strip anything after '_' or '`', and remove trailing numbers like '-1' or '-2'
            clean_lemma = re.sub(r'[_`].*', '', pdt_lemma)
            clean_lemma = re.sub(r'-\d+$', '', clean_lemma)
            
            # 3. Check for negation in the PDT tag (11th position, index 10)
            if len(tag) > 10 and tag[10] == 'N':
                # Prepend 'ne' if it's not already there (safety check)
                if not clean_lemma.startswith("ne"):
                    clean_lemma = "ne" + clean_lemma

            # NEW: Only keep the lemma if it's a word or number (strips punctuation)
            if clean_lemma.isalnum():
                result_lemmas.append(clean_lemma.lower())
            
    return result_lemmas
'''
    

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
    if ALLOWED_CHANNEL_IDS:
        # Check if the channel is actually a thread
        if isinstance(message.channel, discord.Thread):
            # If it's a thread, check if its parent channel is on the allowed list
            if message.channel.parent_id not in ALLOWED_CHANNEL_IDS:
                return
        # If it's a standard text channel, check its ID normally
        elif message.channel.id not in ALLOWED_CHANNEL_IDS:
            return

    

    content_lower = message.content.lower()

    # Step A: Check 'S' (Exact Substring) Triggers
    for rule in S_TRIGGERS:
        target_str = rule["trigger"].lower()
        if target_str in content_lower:
            await execute_response(message, rule)
            return





    # Step B: If no 'S' trigger hit, process 'L' and 'SL' Triggers
    if L_TRIGGERS or SL_TRIGGERS:
        # 1. Tokenize and lemmatize using MorphoDiTa ONCE for both trigger types
        message_lemmas = get_lemmas_with_polarity(message.content)

        # --- Process 'L' (Strict Sliding Window) Triggers ---
        for rule in L_TRIGGERS:
            trigger_lemmas = get_lemmas_with_polarity(rule["trigger"])
            
            trigger_len = len(trigger_lemmas)
            msg_len = len(message_lemmas)
            match_found = False
            
            if trigger_len > 0 and trigger_len <= msg_len:
                for i in range(msg_len - trigger_len + 1):
                    if message_lemmas[i:i+trigger_len] == trigger_lemmas:
                        match_found = True
                        break
                        
            if match_found:
                await execute_response(message, rule)
                return

        # --- NEW Step C: Process 'SL' (Substring Lemmatized) Triggers ---
        if SL_TRIGGERS:
            # Re-join the lemmas into a single string to recreate the flexible substring behavior
            lemmatized_message_string = " ".join(message_lemmas)

            for rule in SL_TRIGGERS:
                trigger_lemmas = get_lemmas_with_polarity(rule["trigger"])
                lemmatized_trigger_string = " ".join(trigger_lemmas)

                # Use the Python 'in' operator to check for any substring overlap
                if lemmatized_trigger_string in lemmatized_message_string:
                    await execute_response(message, rule)
                    return
                    






    '''
    # Step B: If no 'S' trigger hit, process 'L' and 'SL' Triggers
    if L_TRIGGERS or SL_TRIGGERS:
        # 1. Tokenize and lemmatize the user's message ONCE for both trigger types
        tokens = simplemma.simple_tokenizer(message.content)
        message_lemmas = [simplemma.lemmatize(token, lang="cs").lower() for token in tokens]

        # --- Process 'L' (Strict Sliding Window) Triggers ---
        for rule in L_TRIGGERS:
            trigger_tokens = simplemma.simple_tokenizer(rule["trigger"])
            trigger_lemmas = [simplemma.lemmatize(t, lang="cs").lower() for t in trigger_tokens]
            
            trigger_len = len(trigger_lemmas)
            msg_len = len(message_lemmas)
            match_found = False
            
            if trigger_len > 0 and trigger_len <= msg_len:
                for i in range(msg_len - trigger_len + 1):
                    if message_lemmas[i:i+trigger_len] == trigger_lemmas:
                        match_found = True
                        break
                        
            if match_found:
                await execute_response(message, rule)
                return

        # --- NEW Step C: Process 'SL' (Substring Lemmatized) Triggers ---
        if SL_TRIGGERS:
            # Re-join the lemmas into a single string to recreate the old, flexible substring behavior
            lemmatized_message_string = " ".join(message_lemmas)

            for rule in SL_TRIGGERS:
                trigger_tokens = simplemma.simple_tokenizer(rule["trigger"])
                trigger_lemmas = [simplemma.lemmatize(t, lang="cs").lower() for t in trigger_tokens]
                lemmatized_trigger_string = " ".join(trigger_lemmas)

                # Use the Python 'in' operator to check for any substring overlap
                if lemmatized_trigger_string in lemmatized_message_string:
                    await execute_response(message, rule)
                    return
    '''

    """
    # Step B: If no 'S' trigger hit, process 'L' (Lemmatized) Triggers
    if L_TRIGGERS:
        # 1. Tokenize the user's message
        tokens = simplemma.simple_tokenizer(message.content)
        
        # 2. Lemmatize each word but KEEP the original sentence order
        message_lemmas = [simplemma.lemmatize(token, lang="cs").lower() for token in tokens]

        # 3. (Removed) We no longer join the lemmas into a flat string to preserve word boundaries.

        for rule in L_TRIGGERS:
            # 4. Lemmatize the trigger phrase itself
            trigger_tokens = simplemma.simple_tokenizer(rule["trigger"])
            trigger_lemmas = [simplemma.lemmatize(t, lang="cs").lower() for t in trigger_tokens]
            
            # 5. Check if the sequence of trigger lemmas exists in the message lemmas
            trigger_len = len(trigger_lemmas)
            msg_len = len(message_lemmas)
            
            match_found = False
            
            # Ensure the trigger is not empty and isn't longer than the message itself
            if trigger_len > 0 and trigger_len <= msg_len:
                # Slide a "window" over the message lemmas to check for exact sequence matches
                for i in range(msg_len - trigger_len + 1):
                    if message_lemmas[i:i+trigger_len] == trigger_lemmas:
                        match_found = True
                        break
                        
            if match_found:
                await execute_response(message, rule)
                return
    """


async def execute_response(message: discord.Message, rule: dict):
    # Fetch "quantity" from the rule. If it's missing, default to 1. 
    # max(1, ...) ensures the bot won't crash if you accidentally type a 0 or negative number in the JSON.
    quantity = max(1, int(rule.get("quantity", 1)))
    
    # If quantity is greater than 1, roll a metaphorical die.
    # random.randint(1, quantity) picks a random number between 1 and the quantity.
    # If the result is NOT 1, we exit the function immediately without replying.
    if quantity > 1 and random.randint(1, quantity) != 1:
        return
    
    
    response_data = rule["response"]
    
    # Check if the response is a list of multiple options
    if isinstance(response_data, list):
        # Pick one random response from the list
        text = random.choice(response_data)
    else:
        # Fallback for older triggers that only have a single string
        text = response_data

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
