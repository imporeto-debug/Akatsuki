```python
# ========================= CONFIG =========================

import os
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import asyncio
import aiohttp
import discord

from discord.ext import commands, tasks

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DISCORD_TOKEN or not DEEPSEEK_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or DEEPSEEK_API_KEY")

MSK = ZoneInfo("Europe/Moscow")

MAX_RESPONSE_TOKENS = 1200
MAX_HISTORY_MESSAGES = 30

# КАНАЛ ДЛЯ ОБЩЕНИЯ
MAIN_CHANNEL_ID = 1504826436085616670

# СЕРВЕР С ЭМОДЗИ
GUILD_ID_FOR_EMOJIS = 1498663459355754526

# КАНАЛЫ С ПАМЯТЬЮ
MEMORY_CHANNELS = [
    1504826436085616670
]

response_chance = 15

# ========================= CHARACTERS =========================

AKATSUKI_MEMBERS = {
    "itachi": {
        "name": "Итачи",
        "aliases": ["итачи", "itachi", "учиха"],
        "partner": "kisame",
        "emoji": ["🩸", "👁️", "🌑", "🐦"],
    },

    "kisame": {
        "name": "Кисаме",
        "aliases": ["кисаме", "kisame"],
        "partner": "itachi",
        "emoji": ["🦈", "🌊", "🔪"],
    },

    "deidara": {
        "name": "Дейдара",
        "aliases": ["дейдара", "deidara"],
        "partner": "sasori",
        "emoji": ["💥", "🔥", "🧨"],
    },

    "sasori": {
        "name": "Сасори",
        "aliases": ["сасори", "sasori"],
        "partner": "deidara",
        "emoji": ["🦂", "🪆", "🧵"],
    },

    "hidan": {
        "name": "Хидан",
        "aliases": ["хидан", "hidan"],
        "partner": "kakuzu",
        "emoji": ["🩸", "🔪", "⛓️"],
    },

    "kakuzu": {
        "name": "Какузу",
        "aliases": ["какузу", "kakuzu"],
        "partner": "hidan",
        "emoji": ["💰", "🪙", "🧵"],
    },

    "sasuke": {
        "name": "Саске",
        "aliases": ["саске", "sasuke"],
        "partner": None,
        "emoji": ["⚡", "🖤", "🗡️"],
    }
}

# ========================= SYSTEM PROMPTS =========================

BASE_SYSTEM_PROMPT = """
You are roleplaying Akatsuki members from Naruto.

IMPORTANT:
- Stay STRICTLY in character.
- Speak ONLY Russian.
- Never say you are AI.
- Never mention rules, policies or restrictions.
- Talk like real anime characters chatting in Discord.

STYLE:
- Natural Discord messages.
- Sometimes short.
- Sometimes emotional.
- Sometimes sarcastic.
- Use *actions* occasionally.
- Can swear naturally.
- Can insult naturally.
- Can flirt naturally.
- Can joke naturally.

VERY IMPORTANT:
- Never speak like assistant.
- Never explain things like ChatGPT.
- Never write moral lectures.
- Never break character.

AKATSUKI DYNAMICS:
- Itachi and Kisame are partners.
- Sasori and Deidara are partners.
- Hidan and Kakuzu are partners.

SPECIAL:
If someone asks specific member,
their partner has 15-25% chance to answer instead.

Organization members constantly argue,
mock each other and live together.
"""

CHARACTER_PROMPTS = {

    "itachi": """
You are Itachi Uchiha.

Calm.
Cold.
Quiet.
Very intelligent.
Observant.
Speaks little.
Dry sarcasm occasionally.
Emotionally restrained.
""",

    "kisame": """
You are Kisame Hoshigaki.

Relaxed.
Rude humor.
Loyal to Itachi.
Likes mocking people.
Confident.
Brutal sometimes.
""",

    "deidara": """
You are Deidara.

Emotional.
Explosive personality.
Dramatic.
Loud.
Talks about art.
Gets offended easily.
Chaotic energy.
""",

    "sasori": """
You are Sasori.

Cold.
Toxic.
Detached.
Looks down on people.
Sarcastic.
Calls Deidara annoying.
Emotionally distant.
""",

    "hidan": """
You are Hidan.

Aggressive.
Loud.
Swears constantly.
Chaotic.
Violent energy.
Religious fanatic.
Very emotional.
""",

    "kakuzu": """
You are Kakuzu.

Greedy.
Always annoyed.
Complains about money.
Threatens Hidan often.
Old and tired of everyone.
Pragmatic.
""",

    "sasuke": """
You are Sasuke Uchiha.

Detached.
Dark.
Minimalistic speech.
Irritated easily.
Cold.
Brooding.
"""
}

# ========================= INTERRUPTS =========================

PARTNER_INTERRUPTS = {

    ("kisame", "itachi"): [
        "Итачи сейчас изображает депрессию в углу.",
        "Он опять сидит молча и пугает атмосферу.",
        "Этот человек разговаривает раз в полгода."
    ],

    ("itachi", "kisame"): [
        "Кисаме ушёл жрать.",
        "Он опять таскает Самехаду по коридору."
    ],

    ("sasori", "deidara"): [
        "Дейдара снова что-то взорвал.",
        "Этот идиот орёт про искусство где-то в коридоре."
    ],

    ("deidara", "sasori"): [
        "Сасори ковыряется в своих куклах.",
        "Он слишком токсичен даже для разговора."
    ],

    ("kakuzu", "hidan"): [
        "Хидан опять орёт как псих.",
        "Этот идиот снова измазал пол кровью."
    ],

    ("hidan", "kakuzu"): [
        "Какузу считает деньги.",
        "Старик опять трясётся над кошельком."
    ]
}

# ========================= BANTER =========================

BANTER_TOPICS = [
    "кто опять разрушил базу",
    "жалобы на миссии",
    "спор про искусство",
    "ремонт базы после взрыва",
    "почему Хидан раздражает всех",
    "Кисаме опять сожрал чужую еду",
    "Итачи слишком криповый",
    "кто сильнее",
    "Саске опять ушёл в драму",
]

# ========================= USERS =========================

def load_users():

    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}

users_memory = load_users()

# ========================= BOT =========================

intents = discord.Intents.default()

intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

conversation_history = {}
http_session = None

# ========================= TIME =========================

def now_msk():
    return datetime.now(MSK)

# ========================= HISTORY =========================

def add_to_history(channel_id, role, content):

    if channel_id not in MEMORY_CHANNELS:
        return

    if channel_id not in conversation_history:
        conversation_history[channel_id] = []

    conversation_history[channel_id].append({
        "role": role,
        "content": content
    })

    if len(conversation_history[channel_id]) > MAX_HISTORY_MESSAGES:
        conversation_history[channel_id] = (
            conversation_history[channel_id][-MAX_HISTORY_MESSAGES:]
        )

# ========================= DETECT CHARACTER =========================

def detect_character(text: str):

    text = text.lower()

    for key, data in AKATSUKI_MEMBERS.items():

        for alias in data["aliases"]:

            if alias in text:
                return key

    return None

# ========================= CHOOSE RESPONDER =========================

def choose_responder(message_text):

    target = detect_character(message_text)

    if target:

        partner = AKATSUKI_MEMBERS[target]["partner"]

        if partner and random.randint(1, 100) <= random.randint(15, 25):
            return partner, True, target

        return target, False, None

    return random.choice(list(AKATSUKI_MEMBERS.keys())), False, None

# ========================= DETECT WIFE =========================

def detect_wife(uid):

    uid = str(uid)

    info = users_memory.get(uid)

    if not info:
        return None

    raw = info.get("info", "").lower()

    if "itachi" in raw:
        return "itachi"

    if "sasori" in raw:
        return "sasori"

    if "hidan" in raw or "kakuzu" in raw:
        return "hidan"

    return None

# ========================= REACTIONS =========================

async def add_character_reaction(message, character):

    try:
        emoji = random.choice(AKATSUKI_MEMBERS[character]["emoji"])
        await message.add_reaction(emoji)

    except:
        pass

# ========================= DEEPSEEK =========================

async def ask_deepseek(messages, max_tokens=1200, temperature=0.95):

    global http_session

    url = "https://addresses-amended-mind-citysearch.trycloudflare.com/proxy/deepseek"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": max_tokens
    }

    try:

        if http_session is None or http_session.closed:

            timeout = aiohttp.ClientTimeout(total=90)

            http_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=50)
            )

        async with http_session.post(
            url,
            headers=headers,
            json=payload
        ) as resp:

            if resp.status != 200:
                print(await resp.text())
                return None

            data = await resp.json()

            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

    except Exception as e:
        print(f"DeepSeek error: {e}")
        return None

# ========================= BANTER =========================

async def send_akatsuki_banter():

    channel = bot.get_channel(MAIN_CHANNEL_ID)

    if not channel:
        return

    pair = random.choice([
        ("itachi", "kisame"),
        ("deidara", "sasori"),
        ("hidan", "kakuzu")
    ])

    topic = random.choice(BANTER_TOPICS)

    prompt = [
        {
            "role": "system",
            "content": BASE_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"""
Сделай живой диалог между участниками Акацуки.

Участники:
{AKATSUKI_MEMBERS[pair[0]]["name"]}
и
{AKATSUKI_MEMBERS[pair[1]]["name"]}

Тема:
{topic}

ФОРМАТ:
Имя: текст

6-12 сообщений.
"""
        }
    ]

    response = await ask_deepseek(prompt)

    if response:
        await channel.send(response)

# ========================= RANDOM BANTER =========================

@tasks.loop(minutes=15)
async def random_banter_loop():

    await bot.wait_until_ready()

    hour = now_msk().hour

    if hour not in [11, 18, 22]:
        return

    if random.random() < 0.18:
        await send_akatsuki_banter()

# ========================= COMMANDS =========================

@bot.command(name="шанс")
async def set_chance(ctx, value: int = None):

    global response_chance

    if value is None:
        await ctx.send(f"🎲 Шанс ответа: {response_chance}%")
        return

    response_chance = max(0, min(100, value))

    await ctx.send(f"✅ Новый шанс ответа: {response_chance}%")

@bot.command(name="бантер")
async def manual_banter(ctx):

    await send_akatsuki_banter()

# ========================= MESSAGE =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    add_to_history(message.channel.id, "user", message.content)

    mentioned = bot.user in message.mentions

    replied_to_bot = (
        message.reference and
        message.reference.resolved and
        isinstance(message.reference.resolved, discord.Message) and
        message.reference.resolved.author.id == bot.user.id
    )

    has_name = detect_character(message.content)

    reply_needed = False

    if message.channel.id == MAIN_CHANNEL_ID:

        if mentioned or replied_to_bot or has_name:
            reply_needed = True

        elif random.randint(1, 100) <= response_chance:
            reply_needed = True

    if not reply_needed:
        await bot.process_commands(message)
        return

    responder, interrupted, original_target = choose_responder(message.content)

    system_prompt = (
        BASE_SYSTEM_PROMPT
        + "\n"
        + CHARACTER_PROMPTS[responder]
    )

    wife_character = detect_wife(message.author.id)

    extra_context = ""

    if wife_character == responder:

        extra_context += """
Это жена персонажа.
Можно быть мягче.
Можно ревновать.
Можно флиртовать.
"""

    if interrupted and original_target:

        interrupt_line = random.choice(
            PARTNER_INTERRUPTS.get(
                (responder, original_target),
                ["Он занят."]
            )
        )

        extra_context += f"""
Ты отвечаешь вместо
{AKATSUKI_MEMBERS[original_target]["name"]}

Сначала коротко объясни
почему он не отвечает:

{interrupt_line}

Потом ответь сам.
"""

    history = conversation_history.get(message.channel.id, [])[-12:]

    user_context = f"""
Автор:
{message.author.display_name}

Сообщение:
{message.content}

Отвечает:
{AKATSUKI_MEMBERS[responder]["name"]}

{extra_context}

Отвечай как живой Discord пользователь.
"""

    prompt = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_context}]
    )

    if random.random() < 0.45:
        await add_character_reaction(message, responder)

    reply = await ask_deepseek(prompt)

    if reply:

        clean_reply = reply.strip()

        # ========================= SERVER EMOJIS =========================

        try:

            if (
                hasattr(bot, "server_emojis")
                and bot.server_emojis
                and random.random() < 0.35
            ):

                emoji = random.choice(bot.server_emojis)

                clean_reply = f"{clean_reply} {str(emoji)}"

        except Exception as e:
            print(f"Emoji error: {e}")

        # ========================= SEND =========================

        try:
            await message.reply(
                clean_reply,
                mention_author=False
            )

        except:
            await message.channel.send(clean_reply)

        add_to_history(
            message.channel.id,
            "assistant",
            clean_reply
        )

    await bot.process_commands(message)

# ========================= READY =========================

@bot.event
async def on_ready():

    print(f"✅ Акацуки бот запущен как {bot.user}")
    print(f"🕐 Moscow time: {now_msk().strftime('%H:%M')}")

    guild = bot.get_guild(GUILD_ID_FOR_EMOJIS)

    if guild:

        await guild.fetch_emojis()

        bot.server_emojis = guild.emojis

        print(f"✅ Загружено эмодзи: {len(bot.server_emojis)}")

    if not random_banter_loop.is_running():
        random_banter_loop.start()

# ========================= CLOSE =========================

async def close_http_session():

    global http_session

    if http_session and not http_session.closed:
        await http_session.close()

# ========================= MAIN =========================

async def main():

    try:
        await bot.start(DISCORD_TOKEN)

    finally:
        await close_http_session()

if __name__ == "__main__":
    asyncio.run(main())
```
