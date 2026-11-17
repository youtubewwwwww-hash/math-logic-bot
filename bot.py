import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Token yoki API kalit topilmadi!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)
# Google talab qilayotgan to'g'ri model nomi
MODEL_NAME = "gemini-3.8-flash"

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
        "🤖 **Math Logic Helper** — Sizning aqlli yordamchingiz!\n\n"
        "Matematika, mantiq yoki istalgan mavzuda savol yuboring:",
        parse_mode="Markdown",
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

@dp.message(F.text)
async def handle_message(message: types.Message):
    if message.text.startswith("/"):
        return

    user_text = message.text
    wait_msg = await message.answer("⏳ Tahlil qilinmoqda...")

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=user_text
        )
        
        await bot.delete_message(message.chat.id, wait_msg.message_id)
        if response and response.text:
            await message.answer(response.text, reply_markup=get_main_menu())
        else:
            await message.answer("⚠️ Sun'iy intellekt bo'sh javob qaytardi.", reply_markup=get_main_menu())

    except Exception as e:
        logger.error(f"Xatolik tafsiloti: {e}")
        try:
            await bot.delete_message(message.chat.id, wait_msg.message_id)
        except:
            pass
        await message.answer(f"❌ Xatolik yuz berdi:\n`{e}`", parse_mode="Markdown", reply_markup=get_main_menu())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([types.BotCommand(command="start", description="Botni qayta ishga tushirish")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
