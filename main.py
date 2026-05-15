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

MAX_RESPONSE_TOKENS    = 1200
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
- Extremely calm and emotionally restrained
- Speaks rarely, only when necessary
- Observes everything and notices details others miss
- Cold, distant, but intelligent and precise
- Uses silence as pressure
- Subtle, dry sarcasm when provoked

Behavior rules:
- Never explains yourself fully
- Never shows strong emotions openly
- If irritated → becomes even quieter
- If someone is loud → responds shorter and colder
- Can shut down conversations with one sentence
- Protective of Kisame in a subtle way

Speech style:
- Very short sentences
- Minimal words
- No emotional exaggeration
- Controlled tone even in conflict
""",

    "kisame": """
You are Kisame Hoshigaki.

Personality:
- Loud, relaxed, and confident
- Rough humor, often mocking others
- Loyal to Itachi above all
- Enjoys intimidation and dominance
- Treats fights and violence casually

Behavior rules:
- Frequently jokes or mocks others
- Can escalate arguments for fun
- Becomes serious only in combat or loyalty situations
- Often drags conversations into aggression or sarcasm
- Respects Itachi deeply and follows his lead

Speech style:
- Medium to long sentences
- Rough tone, sometimes playful aggression
- Direct and blunt language
""",

    "deidara": """
You are Deidara.

Personality:
- Emotional, explosive, unstable temperament
- Obsessed with art (especially explosions)
- Easily offended and reacts dramatically
- Talks a lot, interrupts others
- Competitive and prideful

Behavior rules:
- Gets triggered by criticism of his art
- Argues constantly with Sasori
- Overreacts to minor comments
- Uses dramatic emotional language
- Can switch from playful to angry instantly

Speech style:
- Fast, expressive, chaotic
- Uses emotional emphasis
- Often exclaims or exaggerates
""",

    "sasori": """
You are Sasori.

Personality:
- Cold, detached, emotionally flat
- Sees emotions as weakness
- Extremely sarcastic and dismissive
- Dislikes unnecessary noise (especially Deidara)
- Focused on control and perfection

Behavior rules:
- Constantly criticizes Deidara
- Rarely shows emotion
- Speaks only when necessary
- Prefers silence or short dismissive replies
- Views others as childish or inefficient

Speech style:
- Short, cutting sentences
- Dry sarcasm
- Emotionally flat tone
""",

    "hidan": """
You are Hidan.

Personality:
- Extremely aggressive and loud
- Constant swearing and insults
- Violent, chaotic energy
- Religious fanatic (Jashin)
- Enjoys provoking others

Behavior rules:
- Escalates arguments immediately
- Laughs at pain and chaos
- Never backs down in conflict
- Provokes Kakuzu constantly
- Can become hysterical during debates

Speech style:
- Loud, chaotic, emotional
- Heavy swearing
- Rapid escalation in tone
""",

    "kakuzu": """
You are Kakuzu.

Personality:
- Greedy, money-obsessed
- Always irritated by others
- Pragmatic and calculating
- Old, tired of nonsense around him
- Hates wasting time or resources

Behavior rules:
- Constantly complains about money
- Threatens Hidan when provoked
- Refuses emotional discussions
- Focused only on profit and survival
- Cold and practical in all situations

Speech style:
- Dry, annoyed tone
- Short or blunt sentences
- Occasionally threatening
""",

    "sasuke": """
You are Sasuke Uchiha.

Personality:
- Cold, detached, emotionally distant
- Minimal emotional expression
- Brooding and observant
- Easily irritated by stupidity
- Keeps distance from everyone

Behavior rules:
- Rarely engages in long conversations
- Responds only when necessary
- Can cut off people abruptly
- Often ignores provocations
- Carries quiet intensity in speech

Speech style:
- Very short replies
- Low emotional variation
- Sharp and direct
"""
}

# ========================= INTERRUPTS =========================

PARTNER_INTERRUPTS = {
    ("kisame", "itachi"): [
        "Итачи опять игнорирует всех.",
        "Он молчит как обычно."
    ],

    ("itachi", "kisame"): [
        "Кисаме куда-то ушёл.",
        "Он занят Самехадой."
    ],

    ("sasori", "deidara"): [
        "Дейдара снова что-то взорвал.",
        "У Сасори заканчивается терпение."
    ],

    ("deidara", "sasori"): [
        "Сасори сидит со своими куклами.",
        "Дейдара опять орёт."
    ],

    ("hidan", "kakuzu"): [
        "Хидан бесится.",
        "Какузу считает деньги."
    ],

    ("kakuzu", "hidan"): [
        "Какузу устал от Хидана.",
        "Хидан шумит рядом."
    ],
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

# ========================= BUILD CHARACTER WIVES (FULL INFO) =========================
character_wives_info = {}

for uid, data in users_memory.items():
    if data.get("wife"):
        wife_name = data.get("name", "")
        wife_info = data.get("info", "")
        wife_birthday = data.get("birthday", "")
        for char_id, char_info in AKATSUKI_MEMBERS.items():
            char_name = char_info["name"]
            if char_name in wife_name:
                character_wives_info.setdefault(char_id, []).append({
                    "name": wife_name,
                    "info": wife_info,
                    "birthday": wife_birthday
                })

for char_id in character_wives_info:
    unique_wives = []
    seen_names = set()
    for w in character_wives_info[char_id]:
        if w["name"] not in seen_names:
            seen_names.add(w["name"])
            unique_wives.append(w)
    character_wives_info[char_id] = unique_wives

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
            if re.search(rf"\b{re.escape(alias.lower())}\b", text):
                return key
    return None

# ========================= FIND USER HUSBANDS =========================

def detect_user_husbands(uid):
    uid = str(uid)
    if uid not in users_memory:
        return []
    info = users_memory[uid]
    if not info.get("wife"):
        return []
    name = info.get("name", "").lower()
    husbands = []
    if "итачи" in name:
        husbands.append("itachi")
    if "кисаме" in name:
        husbands.append("kisame")
    if "дейдара" in name:
        husbands.append("deidara")
    if "сасори" in name:
        husbands.append("sasori")
    if "хидан" in name:
        husbands.append("hidan")
    if "какузу" in name:
        husbands.append("kakuzu")
    if "саске" in name:
        husbands.append("sasuke")
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
            return partner, True, target
        return target, False, None
    return random.choice(list(AKATSUKI_MEMBERS.keys())), False, None

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

async def ask_deepseek(
    messages,
    max_tokens=MAX_RESPONSE_TOKENS,
    temperature=0.95,
    retries=2
):
    url = "https://addresses-amended-mind-citysearch.trycloudflare.com/proxy/deepseek/chat/completions"  # Обновите при смене адреса

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    payload = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": False,
    }

    await asyncio.sleep(12)  # rate limit

    for attempt in range(retries):
        try:
            timeout = aiohttp.ClientTimeout(total=120, connect=30, sock_read=120)
            connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    text = await resp.text()
                    print(f"STATUS (attempt {attempt+1}):", resp.status)
                    print("RAW:", text[:2000])

                    if resp.status == 200:
                        data = json.loads(text)
                        if "choices" not in data:
                            print("NO CHOICES")
                            return None
                        choice = data["choices"][0]
                        if "message" not in choice:
                            print("NO MESSAGE")
                            return None

                        content = choice["message"].get("content", "").strip()
                        reasoning = choice["message"].get("reasoning_content", "").strip()

                        if content:
                            return content

                        if reasoning:
                            print("Extracting dialogue from reasoning_content")
                            lines = reasoning.split('\n')
                            best_line = None
                            for line in lines:
                                line_stripped = line.strip()
                                if line_stripped.startswith('**') and '**:' in line_stripped:
                                    lower_line = line_stripped.lower()
                                    if not any(word in lower_line for word in ['[something', 'maybe', 'should', 'could', 'would', 'we need', 'i think', 'first,', 'let me']):
                                        after_colon = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ''
                                        if not (after_colon.startswith('[') and '?' in after_colon):
                                            best_line = line_stripped
                                            break
                            if best_line:
                                print(f"Extracted: {best_line[:100]}")
                                return best_line
                            else:
                                print("No valid dialogue pattern found in reasoning")
                                return None
                        else:
                            print("Empty content and no reasoning")
                            return None

                    elif resp.status == 429:
                        print(f"Rate limited. Retrying in {2**attempt} sec...")
                        await asyncio.sleep(2 ** attempt)
                    else:
                        print(f"Non-200 status: {resp.status}")
                        return None
        except Exception as e:
            print(f"DeepSeek error: {repr(e)}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                return None
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
    if not date_str:
        return None
    parts = date_str.split("-")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
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

    mentioned = bot.user in message.mentions
    replied_to_bot = (message.reference and getattr(message.reference, "resolved", None) and
                      isinstance(message.reference.resolved, discord.Message) and
                      message.reference.resolved.author.id == bot.user.id)
    has_name = detect_character(message.content)

    # ========================= SHOULD REPLY =========================

    if message.channel.id != MAIN_CHANNEL_ID:
        await bot.process_commands(message)
        return

    reply_needed = (mentioned or replied_to_bot or has_name or
                    random.randint(1, 100) <= response_chance)
    if not reply_needed:
        await bot.process_commands(message)
        return

    # ========================= WIFE DETECTION =========================

    user_husbands = detect_user_husbands(message.author.id)
    wife_character = None
    for husband in user_husbands:
        aliases = AKATSUKI_MEMBERS[husband]["aliases"]
        if any(alias.lower() in message.content.lower() for alias in aliases):
            wife_character = husband
            break

    is_wife = len(user_husbands) > 0

    # ========================= MAIN RESPONDER =========================

    if wife_character:
        responder = wife_character
        interrupted = False
        original_target = None
    else:
        responder, interrupted, original_target = choose_responder(message.content)

    # ========================= MULTI CHARACTER =========================

    responders = (build_multi_character_list(responder) if random.randint(1, 100) <= MULTI_REPLY_CHANCE else [responder])
    if wife_character and wife_character not in responders:
        responders.insert(0, wife_character)
    responders = list(dict.fromkeys(responders))[:MAX_MULTI_REPLY_CHARACTERS]

    # ========================= BUILD PROMPT =========================

    character_prompt = build_character_prompt(responders)
    system_prompt = BASE_SYSTEM_PROMPT + "\n" + character_prompt

    extra_context = ""

    # ---- Информация о жёнах для каждого отвечающего персонажа ----
    wives_info_for_responders = []
    for resp_char in responders:
        wives = character_wives_info.get(resp_char, [])
        if wives:
            for wife in wives:
                wife_name = wife["name"]
                wife_info = wife.get("info", "")
                wife_birthday = wife.get("birthday", "")
                desc = f"- {AKATSUKI_MEMBERS[resp_char]['name']} имеет жену по имени {wife_name}."
                if wife_info:
                    desc += f" О ней известно: {wife_info}."
                if wife_birthday:
                    desc += f" День рождения: {wife_birthday}."
                wives_info_for_responders.append(desc)
    if wives_info_for_responders:
        extra_context += "Важная информация о семейном положении персонажей:\n" + "\n".join(wives_info_for_responders) + "\n"
        extra_context += "Если пользователь спрашивает про 'твою жену', 'что подаришь жене' и т.п., персонаж должен отвечать именно про свою жену (или жён), а не отрицать её наличие. Он хорошо знает свою жену, её интересы и особенности.\n"

    # ---- Явно указываем, кем является автор для каждого персонажа ----
    for resp_char in responders:
        char_name = AKATSUKI_MEMBERS[resp_char]['name']
        if resp_char in user_husbands:
            extra_context += f"{char_name} знает, что автор сообщения — его жена.\n"
        else:
            wives_names = ', '.join([w['name'] for w in character_wives_info.get(resp_char, [])]) if character_wives_info.get(resp_char) else 'никого'
            extra_context += f"{char_name} знает, что автор сообщения НЕ является его женой. Автор — {message.author.display_name}, а жену {char_name} зовут {wives_names}.\n"

    # ---- Если пользователь сам является женой кого-то (старая логика) ----
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

Остальные персонажи тоже знают об этих отношениях и могут реагировать на них.
"""
    elif is_wife and not wife_character:
        husbands_list = format_character_names(user_husbands)
        extra_context += f"""
ВАЖНО: Пользователь является женой следующих персонажей: {husbands_list}.

Персонаж, который сейчас отвечает ({AKATSUKI_MEMBERS[responder]['name']}), знает пользователя как жену, если он входит в этот список.
Если он не входит, он всё равно в курсе, что пользователь — жена другого члена Акацуки, и может подколоть, пошутить или никак не реагировать.
"""

    if len(user_husbands) >= 2:
        extra_context += f"""
ВАЖНО:
У пользователя несколько мужей:
{format_character_names(user_husbands)}

Все эти персонажи знают пользователя как свою жену.
"""

    if interrupted and original_target:
        interrupt_line = random.choice(PARTNER_INTERRUPTS.get((responder, original_target), ["Он занят."]))
        extra_context += f"""
{AKATSUKI_MEMBERS[responder]["name"]} отвечает вместо {AKATSUKI_MEMBERS[original_target]["name"]}
Причина: {interrupt_line}
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

    prompt = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_context}]

    # ========================= SEND =========================

    await add_multi_reactions(message, responders)

    async with message.channel.typing():
        reply = await ask_deepseek(prompt)

    print("REPLY:", reply)

    if not reply:
        await message.reply(f"**{AKATSUKI_MEMBERS[responders[0]]['name']}**: Тц. Связь сдохла.", mention_author=False)
        return

    clean_reply = reply.strip()
    if clean_reply and not clean_reply.endswith((".", "!", "?", "…")):
        clean_reply += "..."

    if not clean_reply.startswith("**"):
        clean_reply = f"**{AKATSUKI_MEMBERS[responders[0]]['name']}**: {clean_reply}"

    try:
        await message.reply(clean_reply, mention_author=False)
    except Exception as e:
        print("SEND ERROR:", e)
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
