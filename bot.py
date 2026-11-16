import os
import logging
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai
from PIL import Image

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
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.8-flash"

# Asosiy menyu tugmalari
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 To'plamlar nazariyasi", callback_data="menu_sets"))
    builder.row(types.InlineKeyboardButton(text="🔢 Kombinatorika", callback_data="menu_combinatorics"))
    builder.row(types.InlineKeyboardButton(text="🔗 Munosabatlar", callback_data="menu_relations"))
    builder.row(types.InlineKeyboardButton(text="🧠 Mantiq", callback_data="menu_logic"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    text = (
        "Assalomu alaykum! Men Math Logic Helper botiman.\n\n"
        "Menga istalgan matematika yoki mantiqiy masalaning rasmini yuboring "
        "yoki matn ko'rinishida yozing, to'liq yechib beraman!"
    )
    await message.answer(text, reply_markup=get_main_menu())

# Menyular bo'yicha bosilganda
@dp.callback_query(F.data.startswith("menu_"))
async def menu_callback_handler(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    
    prompts = {
        "sets": "To'plamlar nazariyasi bo'yicha savol yoki masalaning rasmini yuboring.",
        "combinatorics": "Kombinatorika bo'yicha masalaning rasmini yoki shartini yuboring.",
        "relations": "Munosabatlar bo'yicha savol yoki masalani yuboring.",
        "logic": "Mantiqiy masala yoki mulohazalar algebraasiga doir savol yuboring."
    }
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Asosiy menyuga", callback_data="back_to_main"))
    
    await callback.message.edit_text(
        prompts.get(action, "Savolingizni yuboring:"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Asosiy menyu. Kerakli bo'limni tanlang:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Rasm va matnni birgalikda qabul qilib, Gemini orqali tahlil qilish
@dp.message(F.photo | F.text)
async def handle_content(message: types.Message):
    user_text = message.text or message.caption or "Ushbu masalani qadam-baqadam yechib bering:"
    
    processing_msg = await message.answer("💡 Masalangiz tahlil qilinmoqda...")

    try:
        contents = []
        prompt = (
            "Siz professional matematika va mantiq o'qituvchisisiz. "
            "Quyidagi masala, rasm yoki savolni qadam-baqadam, tushunarli va aniq qilib o'zbek tilida yechib bering:\n\n"
            f"{user_text}"
        )
        contents.append(prompt)

        # Agar foydalanuvchi rasm yuborgan bo'lsa, uni yuklab olib Gemini'ga qo'shamiz
        if message.photo:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            file_bytes = await bot.download_file(file_info.file_path)
            image = Image.open(io.BytesIO(file_bytes.read()))
            contents.append(image)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
        )
        
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        await message.answer(response.text, reply_markup=get_main_menu())
        
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass
        await message.answer(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
