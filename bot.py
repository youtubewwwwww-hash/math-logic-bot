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

# Barcha mavjud modellar ro'yxati (qaysi biri tezroq javob bersa, o'sha tanlanadi)
MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.5-flash",
    "gemini-3.8-flash"
]

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔹 Bul algebrasi va Mulohazalar", callback_data="menu_boolean"))
    builder.row(types.InlineKeyboardButton(text="🔗 Graflar nazariyasi", callback_data="menu_graphs"))
    builder.row(types.InlineKeyboardButton(text="⚙️ Ikkilik mantiqiy elementlar", callback_data="menu_elements"))
    builder.row(types.InlineKeyboardButton(text="📐 Diskret tuzilmalar va to'plamlar", callback_data="menu_discrete"))
    builder.row(types.InlineKeyboardButton(text="🔢 Kombinatorika asoslari", callback_data="menu_combinatorics"))
    builder.row(types.InlineKeyboardButton(text="💡 Erkin savol yuborish", callback_data="menu_free"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🤖 **Math Logic Helper** — Diskret matematika va mantiqiy tahlil yordamchisi!\n\n"
        "Quyidagi bo'limlardan birini tanlang yoki o'zingizni qiziqtirgan masalani yuboring:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    prompts = {
        "boolean": "🔹 Bul algebrasi, mulohazalar va mantiqiy amallar bo'yicha savol yuboring:",
        "graphs": "🔗 Graflar nazariyasining asosiy tushunchalari bo'yicha savol yuboring:",
        "elements": "⚙️ Ikkilik mantiqiy elementlar bo'yicha savol yuboring:",
        "discrete": "📐 Diskret tuzilmalar va to'plamlar bo'yicha savol yuboring:",
        "combinatorics": "🔢 Kombinatorika qoidalari va uning tatbiqi bo'yicha savol yuboring:",
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
    wait_msg = await message.answer("⚡️ Tezkor tahlil qilinmoqda...")

    system_prompt = (
        "Siz diskret matematika, mantiq, bul algebrasi va graflar nazariyasi bo'yicha mutaxassis o'qituvchisisiz. "
        "Foydalanuvchi yuborgan masalani o'zbek tilida, tushunarli, qadam-baqadam va aniq qilib yechib bering.\n\n"
        f"Masala: {user_text}"
    )

    response = None
    # Barcha modellarni ketma-ket tekshirib chiqamiz, qaysi biri ishlasa o'shandan javob olamiz
    for attempt in range(2):  # 2 marta urinish sikli
        for model_name in MODELS:
            try:
                logger.info(f"Model tekshirilmoqda: {model_name}")
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=system_prompt
                )
                if response and response.text:
                    logger.info(f"Muvaffaqiyatli model: {model_name}")
                    break
            except Exception as e:
                logger.warning(f"Model {model_name} xatosi: {e}")
                continue
        
        if response and response.text:
            break
        await asyncio.sleep(1)

    try:
        await bot.delete_message(message.chat.id, wait_msg.message_id)
    except:
        pass

    if response and response.text:
        await message.answer(response.text, reply_markup=get_main_menu())
    else:
        await message.answer("⚠️ Hozirda barcha serverlarda bandlik yuqori. Iltimos, bir soniyadan keyin qaytadan yuboring.", reply_markup=get_main_menu())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([types.BotCommand(command="start", description="Botni ishga tushirish")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
