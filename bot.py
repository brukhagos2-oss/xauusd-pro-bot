import os
import sys
import time
import asyncio
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from strategy import get_xau_data, calculate_signal

# ==========================================
# 1. LOGGING CONFIGURATION & SETUP
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("XAU_SCALPER_BOT")

# ==========================================
# 2. ENVIRONMENT VARIABLES (SECURE LOADING)
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("8581232155:AAF5IYyCs0rKtp9VDktOz0HxwGXAOFbhsKc")
TWELVE_API_KEY = os.getenv("3664c54c5d064605a75795583af2cd9c")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Ethio_online_works_1")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "@Ethio_online_works_1")

# Strict Validation for Security and Stability
if not TELEGRAM_BOT_TOKEN:
    logger.critical("FATAL ERROR: TELEGRAM_BOT_TOKEN is missing from environment variables!")
    sys.exit(1)

if not TWELVE_API_KEY:
    logger.critical("FATAL ERROR: TWELVE_API_KEY is missing from environment variables!")
    sys.exit(1)

# Global State Tracker for Active Signals
active_signal = None
total_signals_sent = 0
successful_wins = 0
stopped_losses = 0

# ==========================================
# 3. TELEGRAM FORCE SUBSCRIPTION CHECK
# ==========================================
async def check_subscription(user_id: int, bot) -> bool:
    """
    Verifies whether a specific Telegram user has joined the required channel.
    """
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            logger.info(f"User {user_id} subscription verified successfully.")
            return True
    except Exception as e:
        logger.warning(f"Could not verify subscription for user {user_id}: {e}")
    return False

# ==========================================
# 4. COMMAND HANDLERS (/start, /help, /status)
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command, performs Force Subscribe validation,
    and welcomes the user with interactive buttons.
    """
    user = update.effective_user
    user_id = user.id
    logger.info(f"Received /start command from user: {user.username} (ID: {user_id})")

    is_subscribed = await check_subscription(user_id, context.bot)

    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 ቻናሉን Join ለማድረግ እዚህ ይጫኑ", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("🔄 ቼክ አድርግ (Verify Sub)", callback_data="verify_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            f"ሰላም {user.first_name}! 黄金 (XAU/USD) 5M Scalper ቦት እንኳን ደህና መጡ።\n\n"
            f"⚠️ **ቦቱን ለመጠቀም መጀመሪያ ከታች ያለውን ኦፊሴላዊ ቻናል Join ማድረግ አለብዎት!**\n"
            f"ቻናሉን ከተቀላቀሉ በኋላ '🔄 ቼክ አድርግ' የሚለውን በመጫን አገልግሎቱን ማግኘት ይችላሉ።"
        )
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        success_text = (
            f"✅ **እንኳን ደህና መጡ {user.first_name}!**\n\n"
            f"የ XAU/USD 5 ደቂቃ ፕሮፌሽናል ሲግናል ቦት በአግባቡ ተከፍቷል። "
            f"ሁሉም ሲግናሎች እና ሪፖርቶች በቀጥታ ወደ ዋናው ቻናል ይለቀቃሉ።"
        )
        await update.message.reply_text(success_text, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Provides bot execution statistics and system health metrics.
    """
    status_msg = (
        f"📊 **BOT PERFORMANCE STATUS**\n\n"
        f"🔹 Status: `Online & Monitoring 24/7`\n"
        f"🔹 Asset: `XAU/USD (Gold)`\n"
        f"🔹 Timeframe: `5 Minutes`\n"
        f"🔹 Strategy Risk-Reward: `1:3 Ratio`\n"
        f"🔹 Total Signals Sent: `{total_signals_sent}`\n"
        f"🔹 Wins Recorded: `{successful_wins}`\n"
        f"🔹 Losses Recorded: `{stopped_losses}`\n"
    )
    await update.message.reply_text(status_msg, parse_mode="Markdown")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manages inline keyboard button clicks for verification.
    """
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "verify_sub":
        is_subscribed = await check_subscription(user_id, context.bot)
        if is_subscribed:
            await query.edit_message_text(
                "✅ **ማረጋገጫው ተሳክቷል!** አሁን ቦቱን ሙሉ በሙሉ መጠቀም ይችላሉ። ሲግናሎች ወደ ቻናሉ ይለቀቃሉ።",
                parse_mode="Markdown"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📢 ቻናሉን Join ለማድረግ እዚህ ይጫኑ", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
                [InlineKeyboardButton("🔄 እንደገና ቼክ አድርግ", callback_data="verify_sub")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ **እስካሁን ቻናሉን አላገኙትም!** እባክዎ መጀመሪያ ቻናሉን Join በማድረግ መልሰው ቼክ አድርግ የሚለውን ይጫኑ።",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

# ==========================================
# 5. BACKGROUND 24/7 SCALPING & MONITORING ENGINE
# ==========================================
async def background_scalper_engine(app):
    """
    Runs continuously in the background, fetching market data every 5 minutes,
    evaluating signals, and tracking trade performance (TP/SL).
    """
    global active_signal, total_signals_sent, successful_wins, stopped_losses
    bot = app.bot
    logger.info("Background XAU/USD Scalper Engine successfully initialized.")

    # Small initial delay to let the application boot smoothly
    await asyncio.sleep(5)

    while True:
        try:
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Running market scan cycle at {current_time_str}...")

            candles = get_xau_data(TWELVE_API_KEY)

            if not candles:
                logger.warning("Failed to fetch candle data from API. Retrying in next cycle.")
                await asyncio.sleep(60)
                continue

            current_price = float(candles[0]['close'])
            logger.info(f"Current XAU/USD Market Price: {current_price}")

            if active_signal:
                # Track existing active signal outcome (Win / Loss)
                action = active_signal['action']
                tp = active_signal['tp']
                sl = active_signal['sl']

                logger.info(f"Tracking active signal [{action}] -> Entry: {active_signal['entry']} | TP: {tp} | SL: {sl}")

                if action == 'BUY':
                    if current_price >= tp:
                        successful_wins += 1
                        win_msg = (
                            f"✅ **XAU/USD WIN (TP HIT)!** 🚀\n\n"
                            f"Target price successfully reached!\n"
                            f"🔹 Exit Price: `{current_price}`\n"
                            f"📊 Total Wins: `{successful_wins}` | Losses: `{stopped_losses}`"
                        )
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=win_msg, parse_mode="Markdown")
                        active_signal = None
                    elif current_price <= sl:
                        stopped_losses += 1
                        loss_msg = (
                            f"❌ **XAU/USD LOSS (SL HIT)!** 🛡️\n\n"
                            f"Stop loss triggered safely.\n"
                            f"🔹 Exit Price: `{current_price}`\n"
                            f"📊 Total Wins: `{successful_wins}` | Losses: `{stopped_losses}`"
                        )
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=loss_msg, parse_mode="Markdown")
                        active_signal = None

                elif action == 'SELL':
                    if current_price <= tp:
                        successful_wins += 1
                        win_msg = (
                            f"✅ **XAU/USD WIN (TP HIT)!** 🚀\n\n"
                            f"Target price successfully reached!\n"
                            f"🔹 Exit Price: `{current_price}`\n"
                            f"📊 Total Wins: `{successful_wins}` | Losses: `{stopped_losses}`"
                        )
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=win_msg, parse_mode="Markdown")
                        active_signal = None
                    elif current_price >= sl:
                        stopped_losses += 1
                        loss_msg = (
                            f"❌ **XAU/USD LOSS (SL HIT)!** 🛡️\n\n"
                            f"Stop loss triggered safely.\n"
                            f"🔹 Exit Price: `{current_price}`\n"
                            f"📊 Total Wins: `{successful_wins}` | Losses: `{stopped_losses}`"
                        )
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=loss_msg, parse_mode="Markdown")
                        active_signal = None
            else:
                # Scan for new scalping setups
                new_signal = calculate_signal(candles)
                if new_signal:
                    active_signal = new_signal
                    total_signals_sent += 1

                    signal_msg = (
                        f"🔔 **PROFESSIONAL XAU/USD 5M SCALPER SIGNAL** 🔔\n\n"
                        f"▫️ Asset: `Gold (XAU/USD)`\n"
                        f"▫️ Action: **{new_signal['action']}**\n"
                        f"▫️ Entry Price: `{new_signal['entry']}`\n"
                        f"▫️ Stop Loss (SL): `{new_signal['sl']}`\n"
                        f"▫️ Take Profit (1:3): `{new_signal['tp']}`\n\n"
                        f"⏳ *Status: Tracking trade result live in background...*"
                    )
                    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=signal_msg, parse_mode="Markdown")
                    logger.info(f"New signal broadcasted: {new_signal['action']} at {new_signal['entry']}")

            # Wait for 5 minutes (300 seconds) before next interval check
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"Critical error encountered in background scalper loop: {e}")
            await asyncio.sleep(60)

# ==========================================
# 6. MAIN APPLICATION EXECUTION
# ==========================================
def main() -> None:
    """
    Initializes the Telegram Bot Application and registers all handlers and background routines.
    """
    logger.info("Initializing Telegram Bot Application...")
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register Command & Callback Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Configure Background Task on Startup
    async def post_init(app):
        app.create_task(background_scalper_engine(app))

    application.post_init = post_init

    logger.info("Bot is starting polling and active listeners...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
