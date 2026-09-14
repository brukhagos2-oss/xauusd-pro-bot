import os
import sys
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from strategy import get_xau_data, calculate_signal

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("XAU_SCALPER_BOT")

TELEGRAM_BOT_TOKEN = os.getenv("8581232155:AAF5IYyCs0rKtp9VDktOz0HxwGXAOFbhsKc")
TWELVE_API_KEY = os.getenv("3664c54c5d064605a75795583af2cd9c")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Ethio_online_works_1")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "@Ethio_online_works_1")

if not TELEGRAM_BOT_TOKEN:
    logger.critical("FATAL ERROR: TELEGRAM_BOT_TOKEN is missing!")
    sys.exit(1)

if not TWELVE_API_KEY:
    logger.critical("FATAL ERROR: TWELVE_API_KEY is missing!")
    sys.exit(1)

active_signal = None
total_signals_sent = 0
successful_wins = 0
stopped_losses = 0

async def check_subscription(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        logger.warning(f"Subscription check warning: {e}")
    return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context.bot)

    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 ቻናሉን Join ለማድረግ እዚህ ይጫኑ", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("🔄 ቼክ አድርግ (Verify)", callback_data="verify_sub")]
        ]
        await update.message.reply_text(
            f"ሰላም {user.first_name}! 🤖 **XAU/USD 5M Scalper ቦት**\n\n⚠️ መጀመሪያ ቻናሉን Join ያድርጉ!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"✅ እንኳን ደህና መጡ {user.first_name}!", parse_mode="Markdown")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "verify_sub":
        if await check_subscription(query.from_user.id, context.bot):
            await query.edit_message_text("✅ ማረጋገጫው ተሳክቷል! አሁን ቦቱን መጠቀም ይችላሉ።", parse_mode="Markdown")
        else:
            keyboard = [[InlineKeyboardButton("📢 ቻናሉን Join ያድርጉ", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
                        [InlineKeyboardButton("🔄 እንደገና ቼክ አድርግ", callback_data="verify_sub")]]
            await query.edit_message_text("❌ እስካሁን ቻናሉን አልተቀላቀሉም!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def background_scalper_engine(app):
    global active_signal, total_signals_sent, successful_wins, stopped_losses
    bot = app.bot
    logger.info("Background Scalper Engine started.")
    await asyncio.sleep(10)

    while True:
        try:
            candles = get_xau_data(TWELVE_API_KEY)
            if not candles:
                await asyncio.sleep(60)
                continue

            current_price = float(candles[0]['close'])

            if active_signal:
                action = active_signal['action']
                tp = active_signal['tp']
                sl = active_signal['sl']

                if action == 'BUY':
                    if current_price >= tp:
                        successful_wins += 1
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ **XAU/USD WIN (TP HIT)!** \n🔹 Exit: `{current_price}`", parse_mode="Markdown")
                        active_signal = None
                    elif current_price <= sl:
                        stopped_losses += 1
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ **XAU/USD LOSS (SL HIT)!** \n🔹 Exit: `{current_price}`", parse_mode="Markdown")
                        active_signal = None
                elif action == 'SELL':
                    if current_price <= tp:
                        successful_wins += 1
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ **XAU/USD WIN (TP HIT)!** \n🔹 Exit: `{current_price}`", parse_mode="Markdown")
                        active_signal = None
                    elif current_price >= sl:
                        stopped_losses += 1
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ **XAU/USD LOSS (SL HIT)!** \n🔹 Exit: `{current_price}`", parse_mode="Markdown")
                        active_signal = None
            else:
                new_signal = calculate_signal(candles)
                if new_signal:
                    active_signal = new_signal
                    total_signals_sent += 1
                    signal_msg = (
                        f"🔔 **XAU/USD 5M SCALPER SIGNAL** 🔔\n\n"
                        f"▫️ Action: **{new_signal['action']}**\n"
                        f"▫️ Entry: `{new_signal['entry']}`\n"
                        f"▫️ SL: `{new_signal['sl']}`\n"
                        f"▫️ TP (1:3): `{new_signal['tp']}`"
                    )
                    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=signal_msg, parse_mode="Markdown")

            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Error in background loop: {e}")
            await asyncio.sleep(60)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # Run background job safely alongside polling
    async def post_init(application):
        application.create_task(background_scalper_engine(application))

    app.post_init = post_init
    
    logger.info("Starting bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
