import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    ChatJoinRequest
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

# ================= KO'RSATMALAR =================
BOT_TOKEN = "8934292582:AAFmUAfT6N5WF2QujI3bPQYPF6GEdJ_NxTw"
ADMIN_ID = 8355669630  # O'zingizning Telegram ID raqamingiz
ADMIN_USERNAME = "@smart_gemini" # Murojaat uchun admin useri
# ===============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# ================= BAZA SOZLAMALARI =================
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ref_by INTEGER,
    ref_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 0
);
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR(50) PRIMARY KEY,
    url TEXT
);
CREATE TABLE IF NOT EXISTS join_requests (
    user_id INTEGER,
    channel_id VARCHAR(50),
    UNIQUE(user_id, channel_id)
);
""")
conn.commit()

# ================= FSM HOLATLAR =================
class AdminState(StatesGroup):
    broadcast = State()
    add_channel_id = State()
    add_channel_url = State()
    del_channel = State()

# ================= KLAVIATURALAR =================
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 Premium xarid qilish"), KeyboardButton(text="⭐️ Telegram Stars")],
            [KeyboardButton(text="💰 Mening Balansim"), KeyboardButton(text="👥 Takliflar (Referal)")],
            [KeyboardButton(text="💳 To'lovlar tarixi")]
        ], resize_keyboard=True
    )

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Umumiy Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Xabar yuborish (Reklama)", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="➕ Majburiy Kanal qo'shish", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="➖ Majburiy Kanal o'chirish", callback_data="admin_del_channel")]
    ])

def premium_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥇 1 Oylik Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🥈 3 Oylik Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🥉 6 Oylik Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🏆 12 Oylik Premium", callback_data="buy_premium")]
    ])

def stars_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 50 Stars", callback_data="buy_stars"),
         InlineKeyboardButton(text="🌟 100 Stars", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💫 500 Stars", callback_data="buy_stars"),
         InlineKeyboardButton(text="💫 1000 Stars", callback_data="buy_stars")]
    ])

# ================= ASOSIY FUNKSIYALAR =================
async def check_subscriptions(user_id: int):
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    
    if not channels:
        return True
    
    for (ch_id,) in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                # Yopiq kanal uchun so'rov yuborilganini tekshiramiz
                cursor.execute("SELECT * FROM join_requests WHERE user_id=? AND channel_id=?", (user_id, ch_id))
                if not cursor.fetchone():
                    return False
        except Exception:
            # Agar bot foydalanuvchini tekshira olmasa (masalan, yopiq kanalga kirmagan bo'lsa), so'rovni tekshiramiz
            cursor.execute("SELECT * FROM join_requests WHERE user_id=? AND channel_id=?", (user_id, ch_id))
            if not cursor.fetchone():
                return False
    return True

async def get_channels_keyboard():
    cursor.execute("SELECT url FROM channels")
    channels = cursor.fetchall()
    
    keyboard = []
    for idx, (url,) in enumerate(channels, 1):
        keyboard.append([InlineKeyboardButton(text=f"📢 {idx}-Kanalga a'zo bo'lish", url=url)])
    
    keyboard.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ================= START VA OBUNA TEKSHIRISH =================
@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        ref_by = int(args) if args and args.isdigit() and int(args) != user_id else None
        cursor.execute("INSERT INTO users (user_id, ref_by) VALUES (?, ?)", (user_id, ref_by))
        conn.commit()

    is_subbed = await check_subscriptions(user_id)
    if is_subbed:
        await check_referral_bonus(user_id)
        await message.answer(
            f"👋 <b>Assalomu alaykum, {message.from_user.first_name}!</b>\n\n"
            f"🎉 <i>Bizning botimizga xush kelibsiz! Bot orqali arzon narxlarda Telegram Premium va Stars xarid qilishingiz mumkin.</i>\n\n"
            f"👇 <b>Iltimos, quyidagi menyudan kerakli bo'limni tanlang:</b>", 
            reply_markup=main_menu(), parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            "⚠️ <b>Botdan to'liq foydalanish uchun quyidagi kanallarimizga obuna bo'lishingiz shart!</b>\n\n"
            "🔒 <i>Agar kanal yopiq bo'lsa, qo'shilish so'rovini yuboring, bot avtomatik tekshirib tasdiqlaydi.</i>\n\n"
            "👇 <b>Obuna bo'lgach, «✅ Obunani tekshirish» tugmasini bosing:</b>", 
            reply_markup=await get_channels_keyboard(), parse_mode=ParseMode.HTML
        )

@router.chat_join_request()
async def join_request_handler(request: ChatJoinRequest):
    user_id = request.from_user.id
    channel_id = str(request.chat.id)
    try:
        cursor.execute("INSERT OR IGNORE INTO join_requests (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
        conn.commit()
    except Exception as e:
        logging.error(f"Join request error: {e}")

@router.callback_query(F.data == "check_sub")
async def check_sub_handler(call: CallbackQuery):
    is_subbed = await check_subscriptions(call.from_user.id)
    if is_subbed:
        await check_referral_bonus(call.from_user.id)
        await call.message.delete()
        await call.message.answer(
            "✅ <b>Ajoyib! Siz barcha kanallarimizga a'zo bo'ldingiz.</b>\n\n"
            "👇 <i>Asosiy menyudan kerakli xizmatni tanlashingiz mumkin:</i>", 
            reply_markup=main_menu(), parse_mode=ParseMode.HTML
        )
    else:
        await call.answer(
            "❌ Kechirasiz! Hali barcha kanallarga a'zo bo'lmadingiz yoki yopiq kanalga so'rov yubormadingiz!", 
            show_alert=True
        )

async def check_referral_bonus(user_id):
    cursor.execute("SELECT ref_by, is_active FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result:
        ref_by, is_active = result
        if not is_active:
            cursor.execute("UPDATE users SET is_active=1 WHERE user_id=?", (user_id,))
            conn.commit()
            if ref_by:
                cursor.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (ref_by,))
                conn.commit()
                try:
                    await bot.send_message(
                        ref_by, 
                        "🎉 <b>Tabriklaymiz!</b>\n\n"
                        "🫂 <i>Sizning taklif havolangiz orqali do'stingiz botga qo'shildi va kanallarga a'zo bo'ldi! Sizga +1 taklif bonusi qo'shildi!</i>",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass

# ================= ASOSIY MENYU TUGMALARI =================
@router.message(F.text == "💎 Premium xarid qilish")
async def premium_btn(message: Message):
    await message.answer(
        "💎 <b>Telegram Premium xarid qilish bo'limi</b>\n\n"
        "<i>Premium orqali profiliga yulduzcha qadash, statuslar o'rnatish, 4GB gacha fayllar yuklash va boshqa imtiyozlarga ega bo'lasiz!</i>\n\n"
        "👇 <b>Necha oylik obuna xarid qilmoqchisiz? Tanlang:</b>", 
        reply_markup=premium_menu(), parse_mode=ParseMode.HTML
    )

@router.message(F.text == "⭐️ Telegram Stars")
async def stars_btn(message: Message):
    await message.answer(
        "⭐️ <b>Telegram Stars xarid qilish bo'limi</b>\n\n"
        "<i>Stars orqali pullik botlardan foydalanish, postlarga reaksiya qoldirish va turli tovarlar sotib olishingiz mumkin!</i>\n\n"
        "👇 <b>Qancha miqdorda Stars xarid qilmoqchisiz? Tanlang:</b>", 
        reply_markup=stars_menu(), parse_mode=ParseMode.HTML
    )

@router.message(F.text == "💰 Mening Balansim")
async def balance_btn(message: Message):
    text = (
        "💳 <b>Sizning shaxsiy balansingiz haqida ma'lumot:</b>\n\n"
        "💰 <b>Asosiy hisobingiz:</b> <code>0 so'm</code>\n"
        "⭐️ <b>Stars hisobingiz:</b> <code>0 ta</code>\n\n"
        "⚙️ <b>Hisobni qanday to'ldirish mumkin?</b>\n"
        "<i>Hisobni to'ldirish, Premium yoki Stars xarid qilish faqat admin orqali amalga oshiriladi. Bizda to'lovlar 100% xavfsiz va ishonchli!</i>\n\n"
        f"👨‍💻 <b>Admin bilan bog'lanish:</b> {ADMIN_USERNAME}\n\n"
        "⚡️ <i>Adminga yozing va kerakli tarifni ayting, u sizga hisob raqam va narxlarni taqdim etadi. To'lovdan so'ng hisobingiz darhol to'ldiriladi!</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(F.text == "👥 Takliflar (Referal)")
async def ref_btn(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT ref_count FROM users WHERE user_id=?", (user_id,))
    ref_count = cursor.fetchone()[0]
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    text = (
        "🤝 <b>Do'stlarni taklif qilish va bonuslar olish dasturi!</b>\n\n"
        "🎁 <i>Siz shaxsiy havolangiz orqali do'stlaringizni taklif qilib, bepul Telegram Premium yoki Stars yutib olish imkoniyatiga egasiz!</i>\n\n"
        f"📊 <b>Siz taklif qilgan jami do'stlar soni:</b> <code>{ref_count} ta</code>\n"
        "🎯 <b>Asosiy maqsad:</b> 5 ta do'st (Sovg'a olish uchun minimal talab)\n\n"
        "🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "📥 <i>Ushbu havolani nusxalang va do'stlaringizga yuboring. Ular kanallarimizga obuna bo'lishi bilanoq, sizga bonus yoziladi!</i> 🎉"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(F.text == "💳 To'lovlar tarixi")
async def payments_btn(message: Message):
    await message.answer(
        "📝 <b>Sizning to'lovlar tarixingiz:</b>\n\n"
        "🤷‍♂️ <i>Hozircha sizda muvaffaqiyatli amalga oshirilgan to'lovlar mavjud emas. Xarid qilish uchun adminga murojaat qiling!</i>",
        parse_mode=ParseMode.HTML
    )

# ================= PREMIUM VA STARS XARID QILISH =================
@router.callback_query(F.data.in_(["buy_premium", "buy_stars"]))
async def process_buy(call: CallbackQuery):
    user_id = call.from_user.id
    cursor.execute("SELECT ref_count FROM users WHERE user_id=?", (user_id,))
    ref_count = cursor.fetchone()[0]
    
    if ref_count < 5:
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        text = (
            "⚠️ <b>Kechirasiz, xaridni davom ettirish uchun shartni bajarmadingiz!</b>\n\n"
            "🎁 <i>Bepul xizmatlardan foydalanish yoki xaridni tasdiqlash uchun kamida 5 ta do'stingizni botga taklif qilishingiz majburiydir!</i>\n\n"
            f"📊 <b>Hozirgi holat:</b> {ref_count} ta do'st / 5 ta kerak\n\n"
            "🔗 <b>Shaxsiy havolangiz orqali do'stlaringizni taklif qiling:</b>\n"
            f"<code>{ref_link}</code>"
        )
        await call.message.answer(text, parse_mode=ParseMode.HTML)
    else:
        await call.message.answer(
            f"🎉 <b>Ajoyib! Siz yetarli do'st taklif qilgansiz.</b>\n\n"
            f"📥 <i>Xizmatni faollashtirish uchun bot adminiga ({ADMIN_USERNAME}) to'g'ridan-to'g'ri murojaat qiling, u tez orada sizga javob beradi!</i>",
            parse_mode=ParseMode.HTML
        )
    
    await call.answer()

# ================= ADMIN PANEL =================
@router.message(Command("admin"))
async def admin_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👨‍💻 <b>Boshqaruv paneliga xush kelibsiz, Admin!</b>\n\n"
            "⚙️ <i>Bu yerdan botni to'liq nazorat qilishingiz, majburiy kanallarni boshqarishingiz va xabarlar tarqatishingiz mumkin. Quyidagi menyudan foydalaning:</i> 👇", 
            reply_markup=admin_menu(), parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM channels")
        total_channels = cursor.fetchone()[0]
        
        text = (
            f"📊 BOT STATISTIKASI:\n\n"
            f"👥 Jami foydalanuvchilar: {total_users} ta\n"
            f"📢 Ulangan kanallar: {total_channels} ta"
        )
        await call.answer(text, show_alert=True)

# Reklama yuborish
@router.callback_query(F.data == "admin_broadcast")
async def ask_broadcast(call: CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer(
            "📢 <b>Foydalanuvchilarga xabar tarqatish bo'limi</b>\n\n"
            "📝 <i>Yuboriladigan xabarni kiriting (Rasm, video yoki oddiy matn bo'lishi mumkin):</i>",
            parse_mode=ParseMode.HTML
        )
        await state.set_state(AdminState.broadcast)
        await call.answer()

@router.message(AdminState.broadcast)
async def send_broadcast(message: Message, state: FSMContext):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    sent = 0
    fail = 0
    await message.answer("⏳ <i>Xabar tarqatilmoqda, kuting...</i>", parse_mode=ParseMode.HTML)
    
    for (user_id,) in users:
        try:
            await message.copy_to(chat_id=user_id)
            sent += 1
            await asyncio.sleep(0.05) # Bot limitiga tushmasligi uchun
        except:
            fail += 1
            
    await message.answer(
        f"✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"📨 Muvaffaqiyatli bordi: <code>{sent} ta</code>\n"
        f"🚫 Botni bloklaganlar: <code>{fail} ta</code>", 
        parse_mode=ParseMode.HTML
    )
    await state.clear()

# Kanal qo'shish
@router.callback_query(F.data == "admin_add_channel")
async def ask_channel_id(call: CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer(
            "➕ <b>Majburiy kanal qo'shish:</b>\n\n"
            "✍️ <i>Kanal ID sini yuboring (Masalan: <code>-100123456789</code>):</i>",
            parse_mode=ParseMode.HTML
        )
        await state.set_state(AdminState.add_channel_id)
        await call.answer()

@router.message(AdminState.add_channel_id)
async def get_channel_id(message: Message, state: FSMContext):
    await state.update_data(channel_id=message.text)
    await message.answer(
        "🔗 <b>Endi kanal havolasini yuboring!</b>\n\n"
        "<i>(Masalan: https://t.me/kanal_nomi yoki qo'shilish uchun yopiq havola)</i>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminState.add_channel_url)

@router.message(AdminState.add_channel_url)
async def save_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data['channel_id']
    url = message.text
    
    cursor.execute("INSERT OR REPLACE INTO channels (channel_id, url) VALUES (?, ?)", (channel_id, url))
    conn.commit()
    
    await message.answer(
        "✅ <b>Majburiy kanal bazaga muvaffaqiyatli qo'shildi!</b>\n\n"
        "<i>Eslatma: Botni shu kanalga Admin qilishni unutmang, aks holda tekshira olmaydi!</i>", 
        parse_mode=ParseMode.HTML
    )
    await state.clear()

# Kanal o'chirish
@router.callback_query(F.data == "admin_del_channel")
async def ask_del_channel(call: CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT channel_id, url FROM channels")
        channels = cursor.fetchall()
        if not channels:
            await call.answer("⚠️ Majburiy kanallar ro'yxati hozircha bo'sh!", show_alert=True)
            return
            
        text = "🗑 <b>O'chirmoqchi bo'lgan kanalingiz ID sini nusxalab yuboring:</b>\n\n"
        for ch_id, url in channels:
            text += f"ID: <code>{ch_id}</code> | 🔗 Havola: {url}\n"
            
        await call.message.answer(text, parse_mode=ParseMode.HTML)
        await state.set_state(AdminState.del_channel)
        await call.answer()

@router.message(AdminState.del_channel)
async def del_channel(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    cursor.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
    conn.commit()
    await message.answer(f"✅ <b><code>{channel_id}</code> ID ga ega kanal ro'yxatdan o'chirildi.</b>", parse_mode=ParseMode.HTML)
    await state.clear()

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
