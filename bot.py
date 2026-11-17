import os
import logging
import io
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Token yoki API kalit topilmadi!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
MODEL_NAME = "gemini-1.5-flash"

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
        "Matematika, mantiq yoki istalgan mavzuda matn yuboring:",
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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"Matematika va mantiq o'qituvchisisiz. Ushbu savolni o'zbek tilida qadam-baqadam yechib bering:\n\n{user_text}"}]
        }]
    }

    answer_text = None
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        answer_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        break
                    else:
                        await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Urinish {attempt+1} xatosi: {e}")
                await asyncio.sleep(2)

    try:
        await bot.delete_message(message.chat.id, wait_msg.message_id)
    except:
        pass

    if answer_text:
        await message.answer(answer_text, reply_markup=get_main_menu())
    else:
        await message.answer("❌ Serverdan javob olishda xatolik yuz berdi. Qaytadan urinib ko'ring.", reply_markup=get_main_menu())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([types.BotCommand(command="start", description="Botni qayta ishga tushirish")])
    try:
        await bot.set_chat_menu_button(menu_button=types.MenuButtonCommands())
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
