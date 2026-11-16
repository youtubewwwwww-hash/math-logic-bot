import os
import logging
import io
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai
from PIL import Image

# Loggingni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token va API kalitlarni olish
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Token yoki API kalit topilmadi!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.8-flash"

# Asosiy menyu
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 To'plamlar nazariyasi", callback_data="menu_sets"))
    builder.row(types.InlineKeyboardButton(text="🔢 Kombinatorika", callback_data="menu_combinatorics"))
    builder.row(types.InlineKeyboardButton(text="🔗 Munosabatlar", callback_data="menu_relations"))
    builder.row(types.InlineKeyboardButton(text="🧠 Mantiq", callback_data="menu_logic"))
    builder.row(types.InlineKeyboardButton(text="💡 Boshqa savollar (Erkin rejim)", callback_data="menu_free"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Men Math Logic Helper botiman.\n\n"
        "Menga matematika, mantiq yoki istalgan mavzuda savol yuboring (rasm yoki matn):",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    prompts = {
        "sets": "📊 To'plamlar nazariyasi bo'yicha savol yuboring:",
        "combinatorics": "🔢 Kombinatorika bo'yicha savol yuboring:",
        "relations": "🔗 Munosabatlar bo'yicha savol yuboring:",
        "logic": "🧠 Mantiqiy masala yuboring:",
        "free": "💡 Istalgan mavzuda savolingizni yuboring:"
    }
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Asosiy menyuga", callback_data="back_to_main"))
    await callback.message.edit_text(prompts.get(action, "Savolingizni yuboring:"), reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("Asosiy menyu:", reply_markup=get_main_menu())
    await callback.answer()

@dp.message(F.photo | F.text)
async def handle_message(message: types.Message):
    if message.text and message.text.startswith("/"):
        return

    user_text = message.text or message.caption or "Ushbu masalani yechib bering:"
    wait_msg = await message.answer("💡 Tahlil qilinmoqda...")

    try:
        prompt = f"Siz matematika va mantiq o'qituvchisisiz. Ushbu masalani o'zbek tilida qadam-baqadam yechib bering:\n\n{user_text}"
        contents = [prompt]

        if message.photo:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            file_bytes = await bot.download_file(file_info.file_path)
            image = Image.open(io.BytesIO(file_bytes.read()))
            contents.append(image)

        # Bloklanib qolmasligi uchun alohida oqimda (thread) ishlatamiz va 30 sekund timeout qo'yamiz
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=MODEL_NAME,
                contents=contents
            ),
            timeout=30.0
        )

        await bot.delete_message(message.chat.id, wait_msg.message_id)
        await message.answer(response.text, reply_markup=get_main_menu())

    except asyncio.TimeoutError:
        try:
            await bot.delete_message(message.chat.id, wait_msg.message_id)
        except:
            pass
        await message.answer("⚠️ Server javob berishni kechiktirdi (timeout). Iltimos, qaytadan urinib ko'ring.", reply_markup=get_main_menu())

    except Exception as e:
        logger.error(f"Xatolik: {e}")
        try:
            await bot.delete_message(message.chat.id, wait_msg.message_id)
        except:
            pass
        await message.answer(f"❌ Xatolik yuz berdi:\n`{e}`", parse_mode="Markdown", reply_markup=get_main_menu())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
