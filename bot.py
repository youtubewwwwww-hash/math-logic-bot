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
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
MODEL_NAME = "gemini-1.5-flash"

# Asosiy menyu tugmalari
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 To'plamlar nazariyasi", callback_data="menu_sets"))
    builder.row(types.InlineKeyboardButton(text="🔢 Kombinatorika", callback_data="menu_combinatorics"))
    builder.row(types.InlineKeyboardButton(text="🔗 Munosabatlar", callback_data="menu_relations"))
    builder.row(types.InlineKeyboardButton(text="🧠 Mantiq", callback_data="menu_logic"))
    builder.row(types.InlineKeyboardButton(text="💡 Boshqa savollar (Erkin rejim)", callback_data="menu_free"))
    return builder.as_markup()

# /start buyrug'i
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    text = (
        "Assalomu alaykum! Men **Math Logic Helper** botiman.\n\n"
        "Quyidagi bo'limlardan birini tanlang yoki istalgan savolingizni yuboring:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())

# Menyular bosilganda
@dp.callback_query(F.data.startswith("menu_"))
async def menu_callback_handler(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    
    prompts = {
        "sets": "📊 **To'plamlar nazariyasi** bo'yicha savol yoki masalaning matni / rasmini yuboring.",
        "combinatorics": "🔢 **Kombinatorika** bo'yicha masalaning shartini yoki rasmini yuboring.",
        "relations": "🔗 **Munosabatlar** bo'yicha savol yoki masalani yuboring.",
        "logic": "🧠 **Mantiqiy masala** yoki mulohazalar algebraasiga doir savol yuboring.",
        "free": "💡 **Erkin rejim:** Matematikadan tashqari istalgan mavzuda savolingizni yuboring, javob beraman!"
    }
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Asosiy menyuga", callback_data="back_to_main"))
    
    await callback.message.edit_text(
        prompts.get(action, "Savolingizni yuboring:"),
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Asosiy menyuga qaytish
@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Asosiy menyu. Kerakli bo'limni tanlang:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Matn va rasmlarni qabul qilib javob berish
@dp.message(F.photo | F.text)
async def handle_content(message: types.Message):
    if message.text and message.text.startswith("/"):
        return

    user_text = message.text or message.caption or "Ushbu savolga javob bering:"
    processing_msg = await message.answer("💡 Tahlil qilinmoqda, iltimos kuting...")

    try:
        contents = []
        system_instruction = (
            "Siz aqlli, har tomonlama bilimdon va yordam berishga tayyor sun'iy intellekt yordamchisisiz. "
            "Foydalanuvchi yuborgan savolga (xoh u matematika, xoh boshqa mavzu bo'lsin) "
            "o'zbek tilida aniq, to'liq va tushunarli qilib javob bering."
        )
        contents.append(system_instruction)
        contents.append(f"Savol: {user_text}")

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
        logger.error(f"Gemini API xatosi: {e}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass
        
        await message.answer(
            "⚠️ Xatolik yuz berdi. Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            reply_markup=get_main_menu()
        )

# Botni ishga tushirish
async def main():
    logger.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
