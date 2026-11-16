import os
import logging
import io
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai
from PIL import Image

# Loggingni sozlash (xatoliklarni kuzatib borish uchun)
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
MODEL_NAME = "gemini-3.8-flash"

# Asosiy menyu tugmalarini shakllantirish funksiyasi
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 To'plamlar nazariyasi", callback_data="menu_sets"))
    builder.row(types.InlineKeyboardButton(text="🔢 Kombinatorika", callback_data="menu_combinatorics"))
    builder.row(types.InlineKeyboardButton(text="🔗 Munosabatlar", callback_data="menu_relations"))
    builder.row(types.InlineKeyboardButton(text="🧠 Mantiq", callback_data="menu_logic"))
    return builder.as_markup()

# /start buyrug'i uchun handler
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    text = (
        "Assalomu alaykum! Men **Math Logic Helper** botiman.\n\n"
        "Menga istalgan matematika yoki mantiqiy masalaning rasmini yuboring "
        "yoki matn ko'rinishida yozing, uni qadam-baqadam va tushunarli qilib yechib beraman!"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())

# Inline menyular bosilganda ishlovchi handler
@dp.callback_query(F.data.startswith("menu_"))
async def menu_callback_handler(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    
    prompts = {
        "sets": "📊 **To'plamlar nazariyasi** bo'yicha savol yoki masalaning matni / rasmini yuboring.",
        "combinatorics": "🔢 **Kombinatorika** bo'yicha masalaning shartini yoki rasmini yuboring.",
        "relations": "🔗 **Munosabatlar** bo'yicha savol yoki masalani yuboring.",
        "logic": "🧠 **Mantiqiy masala** yoki mulohazalar algebraasiga doir savol yuboring."
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

# Rasm va matnli xabarlarni qabul qilib, Gemini orqali tahlil qilish
@dp.message(F.photo | F.text)
async def handle_content(message: types.Message):
    # Komanda xabarlarini o'tkazib yubormaslik uchun tekshiruv
    if message.text and message.text.startswith("/"):
        return

    user_text = message.text or message.caption or "Ushbu masalani to'liq va tushunarli qilib yechib bering:"
    
    # Foydalanuvchiga jarayon boshlanganini bildirish
    processing_msg = await message.answer("💡 Masalangiz tahlil qilinmoqda, iltimos kuting...")

    try:
        contents = []
        system_instruction = (
            "Siz professional matematika va mantiq o'qituvchisisiz. "
            "Foydalanuvchi yuborgan masala, rasm yoki savolni o'zbek tilida, "
            "juda aniq, mantiqiy va qadam-baqadam izohlab bering."
        )
        contents.append(system_instruction)
        contents.append(f"Masala sharti: {user_text}")

        # Agar foydalanuvchi rasm yuborgan bo'lsa, uni yuklab olib Gemini'ga qo'shamiz
        if message.photo:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            file_bytes = await bot.download_file(file_info.file_path)
            image = Image.open(io.BytesIO(file_bytes.read()))
            contents.append(image)

        # Gemini modelidan javob olish
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
        )
        
        # Kutish xabarini o'chirish
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        
        # Javobni yuborish va asosiy menyuni biriktirish
        await message.answer(response.text, reply_markup=get_main_menu())
        
    except Exception as e:
        logger.error(f"Gemini API xatosi: {e}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass
        
        error_str = str(e)
        if "503" in error_str or "UNAVAILABLE" in error_str:
            await message.answer(
                "⚠️ Serverda vaqtinchalik yuqori yuklama kuzatilmoqda. "
                "Iltimos, 1-2 daqiqadan so'ng qayta urinib ko'ring.",
                reply_markup=get_main_menu()
            )
        else:
            await message.answer(
                f"❌ Xatolik yuz berdi: {e}\nIltimos, keyinroq qayta urinib ko'ring.",
                reply_markup=get_main_menu()
            )

# Botni ishga tushirish funksiyasi
async def main():
    logger.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
