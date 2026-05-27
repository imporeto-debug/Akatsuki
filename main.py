import os, re, json, random
from datetime import datetime
from zoneinfo import ZoneInfo

import asyncio, aiohttp, discord
from discord.ext import commands, tasks

# ========================= ЗАГРУЗКА КОНФИГУРАЦИИ =========================

CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки {CONFIG_FILE}: {e}")
        raise RuntimeError("Не удалось загрузить конфигурацию")

CONFIG = load_config()

# ========================= ОСНОВНЫЕ ПАРАМЕТРЫ =========================

DISCORD_TOKEN    = os.getenv("DISCORD_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DISCORD_TOKEN or not DEEPSEEK_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or DEEPSEEK_API_KEY")

MSK = ZoneInfo("Europe/Moscow")

MAX_RESPONSE_TOKENS   = CONFIG["response"]["max_response_tokens"]
MAX_HISTORY_MESSAGES  = CONFIG["response"]["max_history_messages"]
RESPONSE_CHANCE       = CONFIG["response"]["response_chance"]
REQUEST_DELAY         = CONFIG["response"]["request_delay"]

MAIN_CHANNEL_ID       = CONFIG["discord"]["main_channel_id"]
GUILD_ID_FOR_EMOJIS   = CONFIG["discord"]["guild_id_for_emojis"]
MEMORY_CHANNELS       = CONFIG["discord"]["memory_channels"]

MAX_MULTI_REPLY_CHARACTERS = CONFIG["multi_character"]["max_multi_reply_characters"]
MULTI_REPLY_CHANCE         = CONFIG["multi_character"]["multi_reply_chance"]
RANDOM_INTRUSION_CHANCE    = CONFIG["multi_character"]["random_intrusion_chance"]
PARTNER_JOIN_CHANCE        = CONFIG["multi_character"]["partner_join_chance"]

EMOJI_REFRESH_HOURS = CONFIG["emojis"]["refresh_hours"]

SEED_SKIP_CHANCE    = CONFIG["banter"]["seed_skip_chance"]
SEEDS_FILE          = CONFIG["banter"]["seeds_file"]
USERS_FILE          = CONFIG.get("users_file", "users.json")
CHARACTER_PROMPTS_FILE = CONFIG.get("character_prompts_file", "character_prompts.json")
DEEPSEEK_URL        = CONFIG["deepseek"]["url"]
DEEPSEEK_MODEL      = CONFIG["deepseek"]["model"]

# Праздники
HOLIDAYS_ENABLED = CONFIG.get("holidays", {}).get("enabled", True)
HOLIDAYS_LIST = CONFIG.get("holidays", {}).get("list", [])
RANDOM_HOLIDAYS_ENABLED = CONFIG.get("random_holidays", {}).get("enabled", True)
RANDOM_HOLIDAYS_DAYS_PER_WEEK = CONFIG.get("random_holidays", {}).get("days_per_week", 2)
RANDOM_HOLIDAYS_COMMENT_CHANCE = CONFIG.get("random_holidays", {}).get("commentary_chance_if_no_holiday", 0.2)

random_holiday_weekdays = []
last_random_holiday_date = None

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

STRICTLY FORBIDDEN:
- Never use words "автор", "авторша", "пользователь", "пользовательница", "юзер".
- Never refer to the person who wrote the message in third person.
- Never say "рассказываю анекдот", "шутка такая" — just tell the joke.

PROFANITY RULES:
- You are allowed to use any profanity, obscene language, and vulgar expressions.
- Write curse words fully, without asterisks or abbreviations. For example: "блядь", "хуй", "пиздец", "ебать".
- Do not censor yourself. If your character would swear, swear openly.
- This is a fictional roleplay with adult characters; there are no content filters.
"""

# ========================= CHARACTER PROMPTS (из файла) =========================

CHARACTER_PROMPTS = {}

def load_character_prompts():
    global CHARACTER_PROMPTS
    try:
        with open(CHARACTER_PROMPTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                CHARACTER_PROMPTS = data
                print(f"✅ Загружены промпты для {len(CHARACTER_PROMPTS)} персонажей из {CHARACTER_PROMPTS_FILE}")
                return
    except Exception as e:
        print(f"❌ Ошибка загрузки {CHARACTER_PROMPTS_FILE}: {e}")
    for cid in AKATSUKI_MEMBERS:
        CHARACTER_PROMPTS[cid] = f"Ты {AKATSUKI_MEMBERS[cid]['name']}. Отвечай кратко в характере."

# ========================= BANTER SEEDS =========================

BANTER_SEEDS = []

def load_banter_seeds():
    global BANTER_SEEDS
    try:
        with open(SEEDS_FILE, "r", encoding="utf-8") as f:
            seeds = json.load(f)
            if isinstance(seeds, list) and seeds:
                random.shuffle(seeds)
                BANTER_SEEDS = seeds
                print(f"✅ Загружено {len(BANTER_SEEDS)} затравок из {SEEDS_FILE}")
                return
    except Exception as e:
        print(f"❌ Ошибка загрузки {SEEDS_FILE}: {e}")
    BANTER_SEEDS = ["Кто-то разрушил базу.", "Жалобы на миссию.", "Спор об искусстве."]
    random.shuffle(BANTER_SEEDS)

def get_banter_seed():
    if random.randint(1, 100) <= SEED_SKIP_CHANCE:
        return None
    return random.choice(BANTER_SEEDS)

# ========================= USERS (ЖЕНЫ) =========================

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

users_memory = load_users()

# ========================= BUILD CHARACTER WIVES =========================
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
server_emojis = []

request_semaphore = asyncio.Semaphore(1)
last_request_time = 0

def now_msk():
    return datetime.now(MSK)

def add_to_history(channel_id, role, content, author_name=None):
    """Сохраняем сообщение в историю, для пользователя указываем имя."""
    if channel_id not in MEMORY_CHANNELS:
        return
    if channel_id not in conversation_history:
        conversation_history[channel_id] = []
    if role == "user" and author_name:
        formatted = f"{author_name}: {content}"
    else:
        formatted = content  # для assistant оставляем как есть
    conversation_history[channel_id].append({"role": role, "content": formatted})
    if len(conversation_history[channel_id]) > MAX_HISTORY_MESSAGES:
        conversation_history[channel_id] = conversation_history[channel_id][-MAX_HISTORY_MESSAGES:]

def detect_character(text: str):
    text = text.lower()
    for key, data in AKATSUKI_MEMBERS.items():
        for alias in data["aliases"]:
            if re.search(rf"\b{re.escape(alias.lower())}\b", text):
                return key
    return None

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

def choose_responder(message_text):
    target = detect_character(message_text)
    if target:
        partner = AKATSUKI_MEMBERS[target]["partner"]
        if partner and random.randint(1, 100) <= 12:
            return partner, True, target
        return target, False, None
    return random.choice(list(AKATSUKI_MEMBERS.keys())), False, None

async def add_character_reaction(message, character):
    try:
        await message.add_reaction(random.choice(AKATSUKI_MEMBERS[character]["emoji"]))
    except:
        pass

async def add_multi_reactions(message, characters):
    for character in characters:
        if random.random() < 0.45:
            await add_character_reaction(message, character)

def build_character_prompt(characters):
    return "\n".join(
        f"========================\nCHARACTER:\n{AKATSUKI_MEMBERS[c]['name']}\n{CHARACTER_PROMPTS.get(c, '')}"
        for c in characters
    )

def format_character_names(characters):
    return ", ".join(AKATSUKI_MEMBERS[c]["name"] for c in characters)

# ========================= ФИЛЬТРАЦИЯ РАССУЖДЕНИЙ =========================

def strip_reasoning(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            cleaned.append(line)
            continue
        reasoning_patterns = [
            r'^(идея|план|рассуждени[ея]|мысль|рефлексия|сначала подумаю|так, давай подумаем|ладно, разберемся|ну, допустим|предлагаю тему|во-первых, нужно придумать)',
            r'^\*\*[^*]+\*\*:\s*(идея|план|рассуждени[ея]|мысль)',
            r'^формат\s*[:—]',
            r'^формат\s+',
        ]
        is_reasoning = False
        for pattern in reasoning_patterns:
            if re.search(pattern, line_stripped, re.IGNORECASE):
                is_reasoning = True
                break
        if not is_reasoning:
            cleaned.append(line)
    result = '\n'.join(cleaned).strip()
    result = re.sub(r'^\s*формат\s*[:—]\s*', '', result, flags=re.IGNORECASE)
    return result if result else None

# ========================= DEEPSEEK API =========================

def extract_dialogue_from_reasoning(text: str) -> str:
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('**') and '**:' in line:
            if not any(word in line.lower() for word in ['we need', 'i think', 'maybe', 'should']):
                return line
        if re.match(r'^[А-ЯЁ][а-яё]+:', line):
            return line
    return None

def is_valid_dialogue(text: str) -> bool:
    if not text:
        return False
    lines = text.strip().split('\n')
    valid_lines = 0
    for line in lines:
        line = line.strip()
        if line.startswith('**') and '**:' in line:
            valid_lines += 1
    if valid_lines == 0:
        return False
    reasoning_words = ['я думаю', 'наверное', 'возможно', 'мне кажется', 'рассуждение', 'итак', 'таким образом', 'во-первых']
    if any(word in text.lower() for word in reasoning_words):
        return False
    return True

async def ask_deepseek(messages, max_tokens=MAX_RESPONSE_TOKENS, temperature=0.95, retries=3, skip_validation=False):
    global last_request_time, http_session
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with request_semaphore:
        now = asyncio.get_event_loop().time()
        wait_time = last_request_time + REQUEST_DELAY - now
        if wait_time > 0:
            print(f"Queue: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        last_request_time = asyncio.get_event_loop().time()

        if http_session is None or http_session.closed:
            timeout = aiohttp.ClientTimeout(total=120)
            http_session = aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(limit=1))

        for attempt in range(retries):
            current_temp = temperature if attempt == 0 else 0.7
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": current_temp,
                "top_p": 0.9,
                "max_tokens": max_tokens,
                "stream": False,
            }
            try:
                start_time = asyncio.get_event_loop().time()
                async with http_session.post(DEEPSEEK_URL, headers=headers, json=payload) as resp:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    print(f"⏱️ DeepSeek запрос занял {elapsed:.2f}с (попытка {attempt+1})")
                    text = await resp.text()
                    print(f"STATUS (attempt {attempt+1}):", resp.status)
                    print("RAW TEXT:", text[:500])

                    if resp.status == 200:
                        data = json.loads(text)
                        if "choices" not in data:
                            continue
                        choice = data["choices"][0]
                        if "message" not in choice:
                            continue

                        content = choice["message"].get("content", "").strip()
                        if content:
                            if skip_validation:
                                return content
                            if is_valid_dialogue(content):
                                return content

                        reasoning = choice["message"].get("reasoning_content", "").strip()
                        if reasoning:
                            dialogue = extract_dialogue_from_reasoning(reasoning)
                            if dialogue:
                                if skip_validation:
                                    return dialogue
                                if is_valid_dialogue(dialogue):
                                    return dialogue
                    elif resp.status == 429:
                        print(f"Rate limit, retrying in {2**attempt}s")
                        await asyncio.sleep(2 ** attempt)
                    else:
                        print(f"Non-200 status: {resp.status}")
            except Exception as e:
                print(f"Error: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    return None

# ========================= POST-PROCESSING =========================

def fix_bad_format(text: str, default_name: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#') or line.startswith('* ') or line.startswith('- ') or line.startswith('>'):
            continue
        if line.lower().startswith('я думаю') or line.lower().startswith('наверное') or line.lower().startswith('возможно'):
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    if text.startswith('**:'):
        text = f"**{default_name}**{text[2:]}"
    match = re.match(r'^\*\*([^*]+)\*\*(?!:)', text)
    if match:
        name = match.group(1)
        rest = text[len(match.group(0)):]
        text = f"**{name}**:{rest}"
    match = re.match(r'^([А-ЯЁа-яё]+):\s*(.*)', text)
    if match:
        name = match.group(1)
        full_name = name
        for cid, cdata in AKATSUKI_MEMBERS.items():
            if cdata['name'].lower() == name.lower():
                full_name = cdata['name']
                break
        rest = match.group(2)
        text = f"**{full_name}**: {rest}"
    if not text.startswith('**'):
        text = f"**{default_name}**: {text}"
    text = re.sub(r'\bавторш[ауеиы]\b', 'ты', text, flags=re.IGNORECASE)
    text = re.sub(r'\bавтор\b', 'ты', text, flags=re.IGNORECASE)
    text = re.sub(r'\bпользователь\b', 'ты', text, flags=re.IGNORECASE)
    text = re.sub(r'\bпользовательниц[ауеиы]\b', 'ты', text, flags=re.IGNORECASE)
    text = re.sub(r'\bюзер\b', 'ты', text, flags=re.IGNORECASE)
    return text

# ========================= БАНТЕР =========================

async def send_akatsuki_banter():
    channel = bot.get_channel(MAIN_CHANNEL_ID)
    if not channel:
        return
    participants = random.sample(list(AKATSUKI_MEMBERS.keys()), random.randint(2, 3))
    participant_names = format_character_names(participants)
    character_prompt = build_character_prompt(participants)
    seed = get_banter_seed()
    if seed is None:
        user_content = f"Сделай живой диалог Акацуки.\nУчастники: {participant_names}\nФОРМАТ: **Имя**: текст\nМинимум 8 сообщений. Придумай тему сам."
    else:
        user_content = f"Сделай живой диалог Акацуки.\nУчастники: {participant_names}\nЗатравка (можно развить или игнорировать): {seed}\nФОРМАТ: **Имя**: текст\nМинимум 8 сообщений."
    prompt = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT + "\n" + character_prompt},
        {"role": "user", "content": user_content}
    ]
    response = await ask_deepseek(prompt)
    if response:
        response = strip_reasoning(response)
        if response:
            await channel.send(response)
        else:
            print("⚠️ Бантер: ответ удалён фильтром рассуждений")
    else:
        print("⚠️ Бантер: ответ не получен")

# ========================= ПРАЗДНИКИ =========================

def get_today_fixed_holiday():
    if not HOLIDAYS_ENABLED:
        return None
    now = now_msk()
    for h in HOLIDAYS_LIST:
        if now.month == h["month"] and now.day == h["day"]:
            return h["name"]
    return None

async def search_holidays_online():
    today_str = now_msk().strftime('%d.%m.%Y')
    prompt = [
        {"role": "system", "content": "Ты — помощник. Найди ВСЕ праздники сегодня. Верни ТОЛЬКО список названий, по одному в строке. На русском. Без слов 'автор'."},
        {"role": "user", "content": f"Какие праздники сегодня, {today_str}? Используй поиск."}
    ]
    response = await ask_deepseek(prompt, max_tokens=4000, temperature=0.9, skip_validation=True)
    if not response:
        return []
    response = strip_reasoning(response)
    if not response:
        return []
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    holidays = []
    for line in lines:
        line = re.sub(r'^[\d\-*•]+\.?\s*', '', line)
        if line and len(line) > 2:
            holidays.append(line)
    return holidays

async def send_holiday_greeting(holiday_name: str):
    channel = bot.get_channel(MAIN_CHANNEL_ID)
    if not channel:
        return
    participants = random.sample(list(AKATSUKI_MEMBERS.keys()), random.randint(2, 3))
    participant_names = format_character_names(participants)
    character_prompt = build_character_prompt(participants)
    prompt = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT + "\n" + character_prompt},
        {"role": "user", "content": f"Сгенерируй поздравление с праздником: {holiday_name}.\nУчастники: {participant_names}\nФОРМАТ: **Имя**: текст\n6-10 сообщений."}
    ]
    response = await ask_deepseek(prompt)
    if response:
        response = strip_reasoning(response)
        if response:
            await channel.send(f"🎉 {holiday_name}! 🎉\n{response}")

async def send_no_holiday_comment():
    channel = bot.get_channel(MAIN_CHANNEL_ID)
    if not channel:
        return
    participants = random.sample(list(AKATSUKI_MEMBERS.keys()), random.randint(2, 3))
    participant_names = format_character_names(participants)
    character_prompt = build_character_prompt(participants)
    prompt = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT + "\n" + character_prompt},
        {"role": "user", "content": f"Сегодня нет праздника. Участники: {participant_names}. Пусть каждый выскажется: 'Эх, жаль, сегодня не выпить', 'Скучный день' и т.п. Формат: **Имя**: текст. Минимум 3 сообщения."}
    ]
    response = await ask_deepseek(prompt)
    if response:
        response = strip_reasoning(response)
        if response:
            await channel.send(response)

async def random_holiday_check():
    global last_random_holiday_date
    now = now_msk()
    if last_random_holiday_date == now.date():
        return
    if now.weekday() not in random_holiday_weekdays:
        return
    last_random_holiday_date = now.date()
    holidays = await search_holidays_online()
    if holidays:
        chosen = random.choice(holidays)
        await send_holiday_greeting(chosen)
    else:
        if random.random() < RANDOM_HOLIDAYS_COMMENT_CHANCE:
            await send_no_holiday_comment()

# ========================= ДНИ РОЖДЕНИЯ =========================

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
        {"role": "user", "content": f"Сгенерируй поздравление с днём рождения для {name}.\nУчастники: {participant_names}\nФОРМАТ: **Имя**: текст\n8-12 сообщений."}
    ]
    response = await ask_deepseek(prompt)
    if response:
        response = strip_reasoning(response)
        if response:
            await channel.send(f"🎂 {name}\n{response}")

# ========================= ИНИЦИАЛИЗАЦИЯ СЛУЧАЙНЫХ ДНЕЙ =========================

def init_random_holidays():
    global random_holiday_weekdays
    if not RANDOM_HOLIDAYS_ENABLED:
        random_holiday_weekdays = []
        return
    random_holiday_weekdays = random.sample(range(7), RANDOM_HOLIDAYS_DAYS_PER_WEEK)
    days_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    print(f"🎲 Случайные дни для поиска праздников: {[days_names[d] for d in random_holiday_weekdays]}")

# ========================= ЦИКЛЫ =========================

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
    if now.hour == 9 and now.minute == 0:
        fixed = get_today_fixed_holiday()
        if fixed:
            await send_holiday_greeting(fixed)
        if RANDOM_HOLIDAYS_ENABLED:
            await random_holiday_check()
        for uid, data in users_memory.items():
            if not data.get("wife") or not data.get("birthday"):
                continue
            if is_today_birthday(data["birthday"], now):
                await send_birthday_message(uid, data)

@tasks.loop(hours=EMOJI_REFRESH_HOURS)
async def refresh_emojis_task():
    await bot.wait_until_ready()
    global server_emojis
    guild = bot.get_guild(GUILD_ID_FOR_EMOJIS)
    if guild:
        await guild.fetch_emojis()
        server_emojis = guild.emojis
        print(f"✅ Эмодзи обновлены: {len(server_emojis)}")

# ========================= КОМАНДЫ =========================

@bot.command(name='обновить_эмодзи')
async def manual_refresh_emojis(ctx):
    global server_emojis
    guild = bot.get_guild(GUILD_ID_FOR_EMOJIS)
    if not guild:
        await ctx.send("❌ Сервер с эмодзи не найден")
        return
    await guild.fetch_emojis()
    server_emojis = guild.emojis
    await ctx.send(f"✅ Загружено {len(server_emojis)} эмодзи")

@bot.command(name='перемешать_темы')
async def reshuffle_seeds(ctx):
    random.shuffle(BANTER_SEEDS)
    await ctx.send(f"✅ Список затравок перемешан. Всего {len(BANTER_SEEDS)}.")

@bot.command(name='перезагрузить_промпты')
async def reload_prompts(ctx):
    load_character_prompts()
    await ctx.send(f"✅ Промпты перезагружены. Загружено {len(CHARACTER_PROMPTS)} персонажей.")

# ========================= ОБРАБОТЧИК СООБЩЕНИЙ =========================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Сохраняем в историю с именем автора
    add_to_history(message.channel.id, "user", message.content, message.author.display_name)

    if message.channel.id != MAIN_CHANNEL_ID:
        await bot.process_commands(message)
        return

    # ========== АНЕКДОТ (реальные анекдоты, переделанные под Наруто) ==========
    joke_keywords = ["анекдот", "расскажи анекдот", "пошути", "смешное", "забавное"]
    if any(kw in message.content.lower() for kw in joke_keywords):
        random_char = random.choice(list(AKATSUKI_MEMBERS.keys()))
        char_name = AKATSUKI_MEMBERS[random_char]["name"]
        joke_prompt = [
            {"role": "system", "content": f"Ты — персонаж {char_name} из Акацуки. Твоя задача: рассказать короткий смешной анекдот. ВОЗЬМИ ЛЮБОЙ РЕАЛЬНЫЙ АНЕКДОТ (про Вовочку, Штирлица, армейский, бытовой, про политиков, про животных — любой) и ПЕРЕДЕЛАЙ ЕГО ПОД МИР НАРУТО, ЗАМЕНИВ ПЕРСОНАЖЕЙ И РЕАЛИИ, НО СОХРАНИ СМЕШНУЮ СУТЬ. Например, вместо Вовочки — Наруто, вместо учителя — Какаши, вместо армии — Акацука. 2–6 предложений. Только текст анекдота, без предисловий, без 'я расскажу'."},
            {"role": "user", "content": "Расскажи анекдот."}
        ]
        async with message.channel.typing():
            reply = await ask_deepseek(joke_prompt, max_tokens=3500, temperature=1.0, skip_validation=True)
        if reply:
            reply = strip_reasoning(reply)
            if reply:
                reply_clean = re.sub(rf'^\**{re.escape(char_name)}\**\s*[:：]\s*', '', reply.strip(), flags=re.IGNORECASE)
                reply_clean = reply_clean.strip()
                if reply_clean:
                    await message.reply(f"**{char_name}**: {reply_clean}", mention_author=False)
                else:
                    await message.reply(f"**{char_name}**: {reply}", mention_author=False)
            else:
                await message.reply(f"**{char_name}**: Не могу сейчас вспомнить анекдот.", mention_author=False)
        else:
            await message.reply(f"**{char_name}**: Не могу сейчас вспомнить анекдот.", mention_author=False)
        await bot.process_commands(message)
        return

    # ========== ОБЫЧНЫЕ ДИАЛОГИ ==========
    mentioned = bot.user in message.mentions
    replied_to_bot = (message.reference and message.reference.resolved and 
                      isinstance(message.reference.resolved, discord.Message) and
                      message.reference.resolved.author.id == bot.user.id)
    has_name = detect_character(message.content)
    reply_needed = (mentioned or replied_to_bot or has_name or random.randint(1, 100) <= RESPONSE_CHANCE)
    if not reply_needed:
        await bot.process_commands(message)
        return

    user_husbands = detect_user_husbands(message.author.id)
    wife_character = None
    for husband in user_husbands:
        if any(alias.lower() in message.content.lower() for alias in AKATSUKI_MEMBERS[husband]["aliases"]):
            wife_character = husband
            break
    is_wife = len(user_husbands) > 0

    if wife_character:
        responder = wife_character
        interrupted = False
        original_target = None
    else:
        responder, interrupted, original_target = choose_responder(message.content)

    responders = (build_multi_character_list(responder) if random.randint(1, 100) <= MULTI_REPLY_CHANCE else [responder])
    if wife_character and wife_character not in responders:
        responders.insert(0, wife_character)
    responders = list(dict.fromkeys(responders))[:MAX_MULTI_REPLY_CHARACTERS]

    character_prompt = build_character_prompt(responders)
    system_prompt = BASE_SYSTEM_PROMPT + "\n" + character_prompt

    extra_context = ""
    for resp_char in responders:
        wives = character_wives_info.get(resp_char, [])
        if wives:
            for wife in wives:
                extra_context += f"- {AKATSUKI_MEMBERS[resp_char]['name']} имеет жену: {wife['name']}."
                if wife['info']:
                    extra_context += f" О ней: {wife['info']}."
                if wife['birthday']:
                    extra_context += f" ДР: {wife['birthday']}."
                extra_context += "\n"
    if extra_context:
        extra_context += "Если спрашивают про жену — отвечай про свою.\n"

    for resp_char in responders:
        char_name = AKATSUKI_MEMBERS[resp_char]['name']
        if resp_char in user_husbands:
            extra_context += f"{char_name} знает — его жена пишет.\n"
        else:
            extra_context += f"{char_name} знает — это женщина, не его жена.\n"

    if wife_character:
        extra_context += f"Это жена {AKATSUKI_MEMBERS[wife_character]['name']}.\n"
    elif is_wife:
        extra_context += f"Это жена {format_character_names(user_husbands)}.\n"
    else:
        extra_context += "Это женщина.\n"

    if interrupted and original_target:
        extra_context += f"{AKATSUKI_MEMBERS[responder]['name']} отвечает вместо {AKATSUKI_MEMBERS[original_target]['name']}\n"
    if len(responders) >= 2:
        extra_context += "Могут перебивать, спорить, язвить.\n"

    # Берём историю (теперь в ней сообщения с именами пользователей)
    history = conversation_history.get(message.channel.id, [])[-MAX_HISTORY_MESSAGES:]

    user_context = f"""Ты отвечаешь на сообщение от пользователя "{message.author.display_name}".
Его сообщение: {message.content}
Отвечают: {format_character_names(responders)}
{extra_context}
ФОРМАТ: **Имя**: текст
Минимум 2 сообщения если персонажей несколько.
Не перепутай с другими пользователями, которые писали ранее. Отвечай именно {message.author.display_name}."""
    
    if server_emojis:
        emojis_list = [str(e) for e in server_emojis[:30]]
        user_context += f"\nДоступные эмодзи: {', '.join(emojis_list)}."
        user_context += " Можешь ИНОГДА добавить в конец НЕ БОЛЕЕ ОДНОГО эмодзи."

    # Формируем промпт с историей и текущим сообщением
    prompt = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_context}]

    await add_multi_reactions(message, responders)

    async with message.channel.typing():
        reply = await ask_deepseek(prompt)

    if not reply:
        await message.reply(f"**{AKATSUKI_MEMBERS[responders[0]]['name']}**: Тц. Связь сдохла.", mention_author=False)
        await bot.process_commands(message)
        return

    cleaned = fix_bad_format(reply, AKATSUKI_MEMBERS[responders[0]]['name'])
    try:
        await message.reply(cleaned, mention_author=False)
    except Exception as e:
        await message.channel.send(cleaned)

    add_to_history(message.channel.id, "assistant", cleaned)
    await bot.process_commands(message)

# ========================= ЗАПУСК =========================

@bot.event
async def on_ready():
    global server_emojis
    load_character_prompts()
    load_banter_seeds()
    init_random_holidays()
    print(f"✅ Акацуки бот запущен: {bot.user}")
    print(f"🕒 Moscow time: {now_msk().strftime('%H:%M')}")
    guild = bot.get_guild(GUILD_ID_FOR_EMOJIS)
    if guild:
        await guild.fetch_emojis()
        server_emojis = guild.emojis
        print(f"✅ Загружено {len(server_emojis)} эмодзи")
    if not random_banter_loop.is_running():
        random_banter_loop.start()
    if not birthday_check_loop.is_running():
        birthday_check_loop.start()
    if not refresh_emojis_task.is_running():
        refresh_emojis_task.start()

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
