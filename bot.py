import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai
from google.genai import types as genai_types

# Loggingni sozlash
logging.basicConfig(level=logging.INFO)

# Token va API kalitlarni muhit o'zgaruvchilaridan olish
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables bo'limini tekshiring.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY topilmadi! Railway Variables bo'limini tekshiring.")

# Bot va GenAI mijozini ishga tushirish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# To'g'ri va ishlaydigan Gemini klienti (gemini-2.5-flash modeli ishlatiladi)
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Salom! Men Math Logic Helper botiman. Menga matematika yoki mantiqiy savol yuboring, yordam beraman!"
    )

@dp.message()
async def chat_handler(message: types.Message):
    user_text = message.text or message.caption
    if not user_text:
        await message.answer("Iltimos, matnli savol yuboring.")
        return

    try:
        # Gemini API orqali javob olish
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_text,
        )
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        await message.answer(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
