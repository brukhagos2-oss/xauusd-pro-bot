import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from strategy import get_xau_data, calculate_signal

# Logging Setup for 250+ lines reliability & performance tracking
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ትክክለኛው የ Variables አወቃቀር ---
TELEGRAM_BOT_TOKEN = os.getenv("8581232155:AAF5IYyCs0rKtp9VDktOz0HxwGXAOFbhsKc8")
TWELVE_API_KEY = os.getenv("3664c54c5d064605a75795583af2cd9c")

CHANNEL_USERNAME = "@Ethio_online_works_1"
ADMIN_CHAT_ID = "@Ethio_online_works_1"
 

active_signal = None

async def check_subscription(user_id, bot):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        logger.warning(f"Subscription check warning for user {user_id}: {e}")
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot = context.bot
    
    is_subscribed = await check_subscription(user_id, bot)
    
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 ቻናሉን Join ለማድረግ እዚህ ይጫኑ", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("🔄 ቼክ አድርግ (Verify)", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ **ቦቱን ለመጠቀም መጀመሪያ ከታች ያለውን ቻናል Join ማድረግ አለብዎት!**\n\n"
            "ቻናሉን ከተቀላቀሉ በኋላ '🔄 ቼክ አድርግ' የሚለውን ይጫኑ።",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "✅ እንኳን ደህና መጡ! ወደ ፕሮፌሽናል XAU/USD 5M Scalper ቦት ተቀላቀለዋል።\n"
            "ሲግናሎች እና ውጤቶች ወደ ቻናሉ በራስ ሰር ይለቀቃሉ።",
            parse_mode="Markdown"
        )

async def background_scalper(app):
    global active_signal
    bot = app.bot
    logger.info("XAU/USD Professional Scalper Background Engine Started 24/7!")
    
    while True:
        try:
            if active_signal:
                candles = get_xau_data(TWELVE_API_KEY)
                if candles:
                    current_price = float(candles[0]['close'])
                    
                    if active_signal['action'] == 'BUY':
                        if current_price >= active_signal['tp']:
                            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ **XAU/USD WIN (TP Hit)!** \nGold reached Target: `{current_price}`", parse_mode="Markdown")
                            active_signal = None
                        elif current_price <= active_signal['sl']:
                            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ **XAU/USD LOSS (SL Hit)!** \nGold hit Stop Loss: `{current_price}`", parse_mode="Markdown")
                            active_signal = None
                    elif active_signal['action'] == 'SELL':
                        if current_price <= active_signal['tp']:
                            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ **XAU/USD WIN (TP Hit)!** \nGold reached Target: `{current_price}`", parse_mode="Markdown")
                            active_signal = None
                        elif current_price >= active_signal['sl']:
                            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ **XAU/USD LOSS (SL Hit)!** \nGold hit Stop Loss: `{current_price}`", parse_mode="Markdown")
                            active_signal = None
            else:
                candles = get_xau_data(TWELVE_API_KEY)
                if candles:
                    signal = calculate_signal(candles)
                    if signal:
                        active_signal = signal
                        msg = (
                            f"🔔 **PROFESSIONAL XAU/USD 5M SCALPER** 🔔\n\n"
                            f"▫️ Action: **{signal['action']}**\n"
                            f"▫️ Entry Price: `{signal['entry']}`\n"
                            f"▫️ Stop Loss (SL): `{signal['sl']}`\n"
                            f"▫️ Take Profit (1:3): `{signal['tp']}`\n\n"
                            f"⏳ *Status: Monitoring market live...*"
                        )
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
            
            await asyncio.sleep(300) # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in background scalper loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is missing!")
        exit(1)
        
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    loop = asyncio.get_event_loop()
    loop.create_task(background_scalper(app))
    
    app.run_polling()
