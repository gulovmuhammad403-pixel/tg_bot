# bot_full.py
# Бот барои компютер (long polling)
# - Санҷиши обуна ба канал пеш аз ҳар амал
# - Имкони тағйири профил ҳар вақт
# - Форварди ҳама намудҳои паём (матн, акс, voice, video, document ...)
# - Ҳангоми оғоз дар консол паём медиҳад, то бо F5 (IDE) ё бо бозоғоз фаҳмед, ки бот фаъол шуд

import logging
import json
import os
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import asyncio

# ---------- Танзимот ----------
# Ба ҷои "YOUR_TOKEN_HERE" токени боти худро гузоред ё онро дар муҳити система (env) нигоҳ доред
TOKEN = os.environ.get("BOT=TOKEN")
# Ба ҷои @your_channel номи канали худро гузоред (бо @)
CHANNEL_ID = os.getenv("CHANNEL_ID", "@m_soft_studio")

# ---------- Логгиронӣ ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Объектҳои бот ----------
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ---------- Файли нигоҳдорӣ ----------
DATA_FILE = "users.json"

def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("{}")

def load_users():
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users_atomic(data):
    # Навиштан ба файл бо усули атомӣ (temp -> rename)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=".", prefix="users_", suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmpf:
            json.dump(data, tmpf, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_FILE)
    except Exception as e:
        logger.exception("Failed to save users.json: %s", e)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

# Боргирии аввал
user_data = load_users()

waiting_users = {}   # user_id -> True
active_chats = {}    # user_id -> partner_id

# ---------- Меню ----------
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(
    KeyboardButton("🔍 Ҷустуҷӯи ҳамсӯҳбат"),
    KeyboardButton("📄 Профили ман"),
    KeyboardButton("✏️ Тағйири профил"),
    KeyboardButton("⛔ Қатъи суҳбат")
)

# ---------- FSM барои анкета ----------
class Form(StatesGroup):
    name = State()
    gender = State()
    age = State()
    city = State()

# ---------- Ёрирасон: санҷиши обуна ----------
async def check_subscription(user_id: int) -> bool:
    """
    Санҷад, ки корбар ба канали CHANNEL_ID обуна шудааст.
    Агар ягон хатогӣ бошад (масалан бот админ нест ё канал нодуруст) -> False бармегардонад.
    """
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning("Subscription check failed for %s: %s", user_id, e)
        return False

# ---------- Командҳо ва handler-ҳо ----------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    # Ҳар дафъа пеш аз ҳама санҷиши обуна
    if not await check_subscription(message.from_user.id):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(KeyboardButton("📢 Канал"))
        await message.answer(
            f"❌ Барои истифодаи бот аввал ба канали мо обуна шавед:\n{CHANNEL_ID}\n\nПас аз обуна /start ро дубора пахш кунед.",
            reply_markup=kb
        )
        return

    uid = str(message.from_user.id)
    if uid in user_data:
        await message.answer("✅ Шумо аллакай анкета доред!", reply_markup=main_menu)
        return

    await message.answer("Салом! Лутфан номи худро нависед:")
    await Form.name.set()

# Ном
@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        await state.finish()
        return
    await state.update_data(name=message.text.strip())
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👨 Мард", "👩 Зан")
    await message.answer("Ҷинсиятро интихоб кунед:", reply_markup=kb)
    await Form.gender.set()

# Ҷинсият
@dp.message_handler(state=Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        await state.finish()
        return
    gender = "male" if "Мард" in message.text else "female"
    await state.update_data(gender=gender)
    await message.answer("Синну соли худро нависед (аз 18 то 60):")
    await Form.age.set()

# Синну сол
@dp.message_handler(state=Form.age)
async def process_age(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        await state.finish()
        return
    if not message.text.isdigit():
        await message.answer("Лутфан танҳо рақам нависед.")
        return
    age = int(message.text)
    if age < 18 or age > 60:
        await message.answer("❌ Танҳо синну соли аз 18 то 60 қабул мешавад.")
        return
    await state.update_data(age=age)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Душанбе", "Хуҷанд", "Бохтар", "Кӯлоб", "Хоруғ", "Истаравшан", "Панҷакент", "Ваҳдат")
    await message.answer("Шаҳри худро интихоб кунед:", reply_markup=kb)
    await Form.city.set()

# Шаҳр
@dp.message_handler(state=Form.city)
async def process_city(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        await state.finish()
        return
    await state.update_data(city=message.text.strip())
    data = await state.get_data()
    user_data[str(message.from_user.id)] = data
    save_users_atomic(user_data)
    await message.answer(
        f"🎉 Анкета сабт шуд!\n\n"
        f"👤 Ном: {data['name']}\n"
        f"🚹 Ҷинсият: {'Мард' if data['gender']=='male' else 'Зан'}\n"
        f"🎂 Синну сол: {data['age']}\n"
        f"🏙️ Шаҳр: {data['city']}",
        reply_markup=main_menu
    )
    await state.finish()

# Профили ман
@dp.message_handler(lambda msg: msg.text == "📄 Профили ман")
async def show_profile(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        return
    data = user_data.get(str(message.from_user.id))
    if not data:
        await message.answer("❌ Анкета ёфт нашуд. Лутфан /start нависед.")
        return
    await message.answer(
        f"👤 Ном: {data['name']}\n"
        f"🚹 Ҷинсият: {'Мард' if data['gender']=='male' else 'Зан'}\n"
        f"🎂 Синну сол: {data['age']}\n"
        f"🏙️ Шаҳр: {data['city']}"
    )

# Тағйири профил
@dp.message_handler(lambda msg: msg.text == "✏️ Тағйири профил")
async def edit_profile(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        return
    # Агар профил вуҷуд надошта бошад, ба /start монанд оғоз кун
    uid = str(message.from_user.id)
    if uid not in user_data:
        await message.answer("Шумо анкета надоред. Лутфан /start нависед.")
        return
    await message.answer("Ҳоло номи навро нависед:")
    await Form.name.set()

# Ҷустуҷӯи ҳамсӯҳбат
@dp.message_handler(lambda msg: msg.text == "🔍 Ҷустуҷӯи ҳамсӯҳбат")
async def search_partner(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        return
    user_id = str(message.from_user.id)
    if user_id in waiting_users or user_id in active_chats:
        await message.answer("⏳ Шумо аллакай дар ҷустуҷӯ ё чат ҳастед.")
        return
    # Ҷустуҷӯ бо мувофиқат (ҳозир бе филтр, вале мумкин аст илова шавад)
    for other_id in list(waiting_users.keys()):
        if other_id != user_id:
            waiting_users.pop(other_id, None)
            active_chats[user_id] = other_id
            active_chats[other_id] = user_id
            data_me = user_data.get(user_id)
            data_other = user_data.get(other_id)
            # Агар маълумот набошад, паёмҳои мувофиқ фиристед
            await bot.send_message(message.from_user.id,
                f"🎯 Шумо пайваст шудед!\n\n"
                f"👤 Ном: {data_other.get('name','-')}\n"
                f"🚹 Ҷинсият: { 'Мард' if data_other.get('gender')=='male' else 'Зан' }\n"
                f"🎂 Синну сол: {data_other.get('age','-')}\n"
                f"🏙️ Шаҳр: {data_other.get('city','-')}"
            )
            await bot.send_message(int(other_id),
                f"🎯 Шумо пайваст шудед!\n\n"
                f"👤 Ном: {data_me.get('name','-')}\n"
                f"🚹 Ҷинсият: { 'Мард' if data_me.get('gender')=='male' else 'Зан' }\n"
                f"🎂 Синну сол: {data_me.get('age','-')}\n"
                f"🏙️ Шаҳр: {data_me.get('city','-')}"
            )
            return
    waiting_users[user_id] = True
    await message.answer("⏳ Дар ҷустуҷӯи ҳамсӯҳбат...")

# Қатъи суҳбат
@dp.message_handler(lambda msg: msg.text == "⛔ Қатъи суҳбат")
async def stop_chat(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await message.answer("❌ Шумо чатро қатъ кардед.")
        await bot.send_message(int(partner_id), "❌ Ҳамсӯҳбат чатро қатъ кард.")
    elif user_id in waiting_users:
        waiting_users.pop(user_id, None)
        await message.answer("❌ Шумо аз рӯйхати интизор хориҷ шудед.")
    else:
        await message.answer("⚠️ Шумо дар ҷустуҷӯ ё чат набудед.")

# Ҳамагуна паёмҳоро форвард/копи мекунем
@dp.message_handler(content_types=types.ContentTypes.ANY)
async def chat_forward(message: types.Message):
    # Пеш аз ҳама санҷиши обуна барои ҳар паём
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        return

    user_id = str(message.from_user.id)
    # Агар корбар дар чат бошад, паёмро ба ҳамсӯҳбат нусха (copy) кунем
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            # copy_message нигоҳ медорад metadata ва намоиш медиҳад, аммо ҳамчун паём аз бот
            await bot.copy_message(chat_id=int(partner_id), from_chat_id=message.chat.id, message_id=message.message_id)
        except Exception as e:
            logger.exception("Failed to forward/copy message: %s", e)
            # Агар copy_message кор накунад, кӯшиш кунем forward
            try:
                await message.forward(chat_id=int(partner_id))
            except Exception as e2:
                logger.exception("Failed to forward message: %s", e2)
    else:
        # Агар паём матн бошад ва ба меню марбут набошад, ҳеч кор накун
        # (ин блок барои паёмҳои ғайримуқаррарӣ ё фармонҳои дигар)
        pass

# Командаи оддӣ барои санҷиши ҳолат
@dp.message_handler(commands=["status", "ping"])
async def cmd_status(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Аввал ба канал обуна шавед!")
        return
    await message.answer("✅ Бот фаъол аст!")

# ---------- Ҳангоми оғоз ва қатъ ----------
async def on_startup(dp):
    logger.info("Бот оғоз шуд")
    print("✅ Бот фаъол шуд — агар шумо F5 пахш кунед, ин паёмро мебинед.")
    # Боргирии маълумоти корбарон (агар дар диск тағйир ёфта бошад)
    global user_data
    user_data = load_users()

async def on_shutdown(dp):
    logger.info("Бот қатъ мешавад")
    # Сабти охирин маълумот
    save_users_atomic(user_data)
    await bot.close()

# ---------- Оғози бот ----------
if __name__ == "__main__":
    ensure_data_file()
    # Агар шумо дар IDE F5 пахш кунед, ин скрипт бозоғоз мешавад ва паёми "Бот фаъол шуд" дар консол мебарояд
    loop = asyncio.get_event_loop()
    try:
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopped by user")

