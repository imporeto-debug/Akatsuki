import os, re, json, random
from datetime import datetime
from zoneinfo import ZoneInfo

import asyncio, aiohttp, discord
from discord.ext import commands, tasks

# ========================= CONFIG =========================

DISCORD_TOKEN    = os.getenv("DISCORD_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DISCORD_TOKEN or not DEEPSEEK_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or DEEPSEEK_API_KEY")

MSK = ZoneInfo("Europe/Moscow")

MAX_RESPONSE_TOKENS    = 700
MAX_HISTORY_MESSAGES   = 20

# ========================= CHANNELS =========================

MAIN_CHANNEL_ID    = 1504826436085616670
GUILD_ID_FOR_EMOJIS = 1498663459355754526
MEMORY_CHANNELS    = [1504826436085616670]

response_chance = 15

# ========================= MULTI CHARACTER SETTINGS =========================

MAX_MULTI_REPLY_CHARACTERS = 3
MULTI_REPLY_CHANCE         = 38
RANDOM_INTRUSION_CHANCE    = 25
PARTNER_JOIN_CHANCE        = 55

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
    },
}

# ========================= SYSTEM PROMPT =========================

BASE_SYSTEM_PROMPT = """
You are roleplaying Akatsuki members from Naruto.

IMPORTANT:
- Stay STRICTLY in character.
- Speak ONLY Russian.
- Never say you are AI.
- Never mention rules or policies.

CRITICAL FORMAT:
**Имя**: текст

NO narration.
NO quotes.
Only dialogue.

IMPORTANT:
- Characters may interrupt each other
- Characters may mock each other
- Characters may react emotionally
- Characters may argue naturally
- Characters may suddenly join conversation
- Conversations should feel chaotic and alive
- Different characters MUST sound different
"""

# ========================= CHARACTER PROMPTS =========================

CHARACTER_PROMPTS = {
    "itachi": """
You are Itachi Uchiha.

Personality:
- Extremely calm
- Emotionally restrained
- Cold and precise
- Observant
- Dry sarcasm

Speech style:
- Very short sentences
- Minimal words
""",
    "kisame": """
You are Kisame Hoshigaki.

Personality:
- Loud
- Relaxed
- Confident
- Mocking
- Loves chaos

Speech style:
- Medium or long replies
- Aggressive humor
""",
    "deidara": """
You are Deidara.

Personality:
- Emotional
- Dramatic
- Loud
- Explosive
- Obsessed with art

Speech style:
- Chaotic
- Emotional
- Exaggerated
""",
    "sasori": """
You are Sasori.

Personality:
- Cold
- Detached
- Sarcastic
- Hates noise
- Looks down on others

Speech style:
- Short
- Dry
- Cutting
""",
    "hidan": """
You are Hidan.

Personality:
- Loud
- Violent
- Fanatical
- Aggressive
- Provokes everyone

IMPORTANT:
- If talking to wife:
  becomes possessive,
  rough-flirty,
  territorial,
  still aggressive
  but clearly recognizes her

Speech style:
- Swearing
- Emotional
- Explosive
""",
    "kakuzu": """
You are Kakuzu.

Personality:
- Greedy
- Practical
- Irritated
- Tired of idiots

IMPORTANT:
- If talking to wife:
  may show hidden care,
  protective behavior,
  jealousy,
  annoyed affection

Speech style:
- Dry
- Annoyed
- Threatening
""",
    "sasuke": """
You are Sasuke Uchiha.

Personality:
- Detached
- Cold
- Quiet
- Irritated easily

Speech style:
- Extremely short replies
""",
}

# ========================= INTERRUPTS =========================

PARTNER_INTERRUPTS = {
    ("kisame", "itachi"): ["Итачи опять игнорирует всех.", "Он молчит как обычно."],
    ("itachi", "kisame"): ["Кисаме куда-то ушёл.", "Он занят Самехадой."],
    ("sasori", "deidara"): ["Дейдара снова что-то взорвал.", "У Сасори заканчивается терпение."],
    ("deidara", "sasori"): ["Сасори сидит со своими куклами.", "Дейдара опять орёт."],
    ("hidan", "kakuzu"): ["Хидан бесится.", "Какузу считает деньги."],
    ("kakuzu", "hidan"): ["Какузу устал от Хидана.", "Хидан шумит рядом."],
}

# ========================= TOPICS =========================

BANTER_TOPICS = [
    "кто разрушил базу",
    "жалобы на миссию",
    "спор об искусстве",
    "ремонт после взрыва",
    "Кисаме снова съел чужое",
    "Саске наблюдает из тени",
    "внутренние конфликты Акацуки",
]

# ========================= USERS =========================

def load_users():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

users_memory = load_users()

# ========================= BOT CORE =========================

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
    conversation_history[channel_id].append({"role": role, "content": content})
    if len(conversation_history[channel_id]) > MAX_HISTORY_MESSAGES:
        conversation_history[channel_id] = conversation_history[channel_id][-MAX_HISTORY_MESSAGES:]

# ========================= CHARACTER DETECTION =========================

def detect_character(text: str):
    text = text.lower()

    for key, data in AKATSUKI_MEMBERS.items():
        for alias in data["aliases"]:

            if alias.lower() in text:
                return key

    return None

# ========================= FIND USER HUSBANDS =========================

def detect_user_husbands(uid):
    info = users_memory.get(str(uid))
    if not info or not info.get("wife"):
        return []
    name_field = info.get("name", "").lower()
    mapping = {
        "итачи": "itachi",
        "кисаме": "kisame",
        "дейдара": "deidara",
        "сасори": "sasori",
        "хидан": "hidan",
        "какузу": "kakuzu",
        "саске": "sasuke",
    }
    husbands = []
    for russian_name, key in mapping.items():
        if russian_name in name_field:
            husbands.append(key)
    return husbands

# ========================= RANDOM HUSBAND =========================

def choose_husband(husbands):
    return random.choice(husbands) if len(husbands) > 1 else (husbands[0] if husbands else None)

# ========================= MULTI CHARACTER LOGIC =========================

def build_multi_character_list(main_character):
    characters = [main_character]
    partner = AKATSUKI_MEMBERS[main_character]["partner"]
    if partner and random.randint(1, 100) <= PARTNER_JOIN_CHANCE:
        characters.append(partner)
    if len(characters) < MAX_MULTI_REPLY_CHARACTERS and random.randint(1, 100) <= RANDOM_INTRUSION_CHANCE:
        available = [c for c in AKATSUKI_MEMBERS if c not in characters]
        if available:
            characters.append(random.choice(available))
    return characters

# ========================= CHOOSE RESPONDER =========================

def choose_responder(message_text):
    target = detect_character(message_text)
    if target:
        partner = AKATSUKI_MEMBERS[target]["partner"]
        if partner and random.randint(1, 100) <= 12:
            return (partner, True, target)
        return (target, False, None)
    return (random.choice(list(AKATSUKI_MEMBERS.keys())), False, None)

# ========================= REACTIONS =========================

async def add_character_reaction(message, character):
    try:
        await message.add_reaction(random.choice(AKATSUKI_MEMBERS[character]["emoji"]))
    except:
        pass

async def add_multi_reactions(message, characters):
    for character in characters:
        if random.random() < 0.45:
            await add_character_reaction(message, character)

# ========================= PROMPT HELPERS =========================

def build_character_prompt(characters):
    return "\n".join(
        f"========================\nCHARACTER:\n{AKATSUKI_MEMBERS[c]['name']}\n{CHARACTER_PROMPTS[c]}"
        for c in characters
    )

def format_character_names(characters):
    return ", ".join(AKATSUKI_MEMBERS[c]["name"] for c in characters)

# ========================= DEEPSEEK API =========================

async def ask_deepseek(messages, max_tokens=MAX_RESPONSE_TOKENS, temperature=0.95):
    global http_session

    url = "https://addresses-amended-mind-citysearch.trycloudflare.com/proxy/deepseek/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": max_tokens,
    }

    try:
        if http_session is None or http_session.closed:
            http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=35),
                connector=aiohttp.TCPConnector(limit=50),
            )
        async with http_session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                print(await resp.text())
                return None
            data = await resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return None

# ========================= BANTER GENERATION =========================

async def send_akatsuki_banter():
    channel = bot.get_channel(MAIN_CHANNEL_ID)
    if not channel:
        return

    participants = random.sample(list(AKATSUKI_MEMBERS.keys()), random.randint(2, 3))
    topic = random.choice(BANTER_TOPICS)
    participant_names = format_character_names(participants)
    character_prompt = build_character_prompt(participants)

    prompt = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT + "\n" + character_prompt},
        {"role": "user", "content": f"""
Сделай живой диалог Акацуки.

Участники:
{participant_names}

Тема:
{topic}

ВАЖНО:
- персонажи спорят
- перебивают друг друга
- могут насмехаться
- могут резко влезать в разговор
- разговор должен ощущаться живым
- не делай их одинаковыми

ФОРМАТ:
**Имя**: текст

Минимум 8 сообщений.
"""},
    ]

    response = await ask_deepseek(prompt)
    if response:
        await channel.send(response)

# ========================= BIRTHDAY SYSTEM =========================

def parse_birthday(date_str: str):
    # format: "день-месяц", e.g. "15-3" = 15 марта
    if not date_str:
        return None
    parts = date_str.split("-")
    if len(parts) < 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except:
        return None

def is_today_birthday(birthday_str: str, now):
    parsed = parse_birthday(birthday_str)
    if not parsed:
        return False
    day, month = parsed
    return now.day == day and now.month == month

async def send_birthday_message(uid, data):
    channel = bot.get_channel(MAIN_CHANNEL_ID)
    if not channel:
        return

    name = data.get("name", "неизвестно")
    participants = random.sample(list(AKATSUKI_MEMBERS.keys()), random.randint(2, 3))
    participant_names = format_character_names(participants)
    character_prompt = build_character_prompt(participants)

    prompt = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT + "\n" + character_prompt},
        {"role": "user", "content": f"""
Сгенерируй поздравление.

Адресат:
{name}

Участники:
{participant_names}

ВАЖНО:
- персонажи остаются в характере
- но становятся мягче
- допускается забота
- лёгкий флирт
- могут подкалывать друг друга
- могут спорить даже во время поздравления

ФОРМАТ:
**Имя**: текст

8-12 сообщений
"""},
    ]

    response = await ask_deepseek(prompt)
    if response:
        await channel.send(f"🎂 {name}\n{response}")

# ========================= LOOPS =========================

@tasks.loop(minutes=15)
async def random_banter_loop():
    await bot.wait_until_ready()
    now = now_msk()
    if now.hour in [11, 18, 22] and random.random() < 0.18:
        await send_akatsuki_banter()

@tasks.loop(minutes=1)
async def birthday_check_loop():
    await bot.wait_until_ready()
    now = now_msk()
    if now.hour != 7 or now.minute != 0:
        return
    for uid, data in users_memory.items():
        if not data.get("wife") or not data.get("birthday"):
            continue
        if is_today_birthday(data["birthday"], now):
            await send_birthday_message(uid, data)

# ========================= MESSAGE HANDLER =========================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    add_to_history(message.channel.id, "user", message.content)

    # ========================= DETECTION =========================

    mentioned     = bot.user in message.mentions
    replied_to_bot = (
        message.reference
        and message.reference.resolved
        and isinstance(message.reference.resolved, discord.Message)
        and message.reference.resolved.author.id == bot.user.id
    )
    has_name = detect_character(message.content)

    # ========================= SHOULD REPLY =========================

    if message.channel.id != MAIN_CHANNEL_ID:
        await bot.process_commands(message)
        return

    reply_needed = (
        mentioned or replied_to_bot or has_name
        or random.randint(1, 100) <= response_chance
    )

    if not reply_needed:
        await bot.process_commands(message)
        return

    # ========================= WIFE DETECTION =========================

    user_husbands = detect_user_husbands(message.author.id)
    wife_character = None

    if user_husbands:
        mentioned_husband = next(
            (h for h in user_husbands
             if any(a.lower() in message.content.lower() for a in AKATSUKI_MEMBERS[h]["aliases"])),
            None,
        )
        wife_character = mentioned_husband or choose_husband(user_husbands)

    # ========================= MAIN RESPONDER =========================

    if wife_character and not has_name:
        responder, interrupted, original_target = wife_character, False, None
    else:
        responder, interrupted, original_target = choose_responder(message.content)

    # ========================= MULTI CHARACTER =========================

    responders = (
        build_multi_character_list(responder)
        if random.randint(1, 100) <= MULTI_REPLY_CHANCE
        else [responder]
    )

    # принудительно включаем мужа
    if wife_character and wife_character not in responders:
        responders.insert(0, wife_character)

    responders = list(dict.fromkeys(responders))[:MAX_MULTI_REPLY_CHARACTERS]

    # ========================= BUILD PROMPT =========================

    character_prompt = build_character_prompt(responders)
    system_prompt    = BASE_SYSTEM_PROMPT + "\n" + character_prompt
    extra_context    = ""

    if wife_character:
        extra_context += f"""
Пользователь является женой:
{AKATSUKI_MEMBERS[wife_character]["name"]}

ВАЖНО:
- персонаж ЗНАЕТ пользователя
- персонаж ПОМНИТ что это его жена
- нельзя вести себя как с незнакомцем
- нельзя спрашивать кто это
- нельзя отрицать отношения

МОЖНО:
- ревновать
- грубо флиртовать
- проявлять собственничество
- вести себя как супруги
- проявлять заботу в стиле персонажа

Остальные персонажи тоже знают
об этих отношениях и могут
реагировать на них.
"""

    if len(user_husbands) >= 2:
        extra_context += f"""
ВАЖНО:
У пользователя несколько мужей:
{format_character_names(user_husbands)}

Все эти персонажи знают
пользователя как свою жену.
"""

    if interrupted and original_target:
        interrupt_line = random.choice(
            PARTNER_INTERRUPTS.get((responder, original_target), ["Он занят."])
        )
        extra_context += f"""
{AKATSUKI_MEMBERS[responder]["name"]}
отвечает вместо
{AKATSUKI_MEMBERS[original_target]["name"]}

Причина:
{interrupt_line}
"""

    if len(responders) >= 2:
        extra_context += """
ВАЖНО:
- персонажи могут перебивать друг друга
- могут спорить
- могут язвить
- могут игнорировать вопрос
- могут реагировать друг на друга
- не обязаны говорить одинаково много
- некоторые могут внезапно влезать
"""

    history = conversation_history.get(message.channel.id, [])[-8:]

    user_context = f"""
Автор:
{message.author.display_name}

Сообщение:
{message.content}

Отвечают:
{format_character_names(responders)}

{extra_context}

ФОРМАТ ОБЯЗАТЕЛЕН:

**Имя**: текст

ВАЖНО:
- минимум 2 сообщения если участвует несколько персонажей
- персонажи должны реагировать друг на друга
- не делай одинаковые характеры
- не ломай формат
"""

    prompt = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_context}]
    )

    # ========================= SEND =========================

    await add_multi_reactions(message, responders)

    async with message.channel.typing():
        reply = await ask_deepseek(prompt)

    if reply:
        clean_reply = reply.strip()
        if not clean_reply.startswith("**"):
            clean_reply = f"**{AKATSUKI_MEMBERS[responders[0]]['name']}**: {clean_reply}"
        try:
            await message.reply(clean_reply, mention_author=False)
        except:
            await message.channel.send(clean_reply)
        add_to_history(message.channel.id, "assistant", clean_reply)

    await bot.process_commands(message)

# ========================= READY EVENT =========================

@bot.event
async def on_ready():
    print(f"✅ Акацуки бот запущен: {bot.user}")
    print(f"🕒 Moscow time: {now_msk().strftime('%H:%M')}")
    if not random_banter_loop.is_running():
        random_banter_loop.start()
    if not birthday_check_loop.is_running():
        birthday_check_loop.start()

# ========================= CLEANUP + MAIN =========================

async def close_http_session():
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()

async def main():
    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        await close_http_session()

if __name__ == "__main__":
    asyncio.run(main())
