import os
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    logging.error("❌ BOT_TOKEN environment variable is not set!")
    exit(1)

# ==================== IMAGE CONFIGURATION ====================
# Raw URL for your image on GitHub
WELCOME_IMAGE_URL = "https://raw.githubusercontent.com/Ninavivaart/dailybonus1bot/main/image.png"

# ==================== LOGGING ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATA STORAGE ====================
DATA_FILE = "user_data.json"
user_data: Dict[int, Dict] = {}

# ==================== BONUS CONFIGURATION ====================
BASE_BONUS = 100
STREAK_MULTIPLIERS = {
    1: 1.0,   # Day 1: 100 coins
    2: 1.2,   # Day 2: 120 coins
    3: 1.5,   # Day 3: 150 coins
    4: 1.8,   # Day 4: 180 coins
    5: 2.0,   # Day 5: 200 coins
    6: 2.5,   # Day 6: 250 coins
    7: 3.0,   # Day 7: 300 coins
}
MAX_STREAK_BONUS = 500  # Maximum bonus for long streaks

# ==================== DATA PERSISTENCE ====================
def load_data():
    """Load user data from file"""
    global user_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                user_data = {int(k): v for k, v in data.items()}
                logger.info(f"✅ Loaded data for {len(user_data)} users")
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    """Save user data to file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({str(k): v for k, v in user_data.items()}, f)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

# Load data on startup
load_data()

# ==================== HELPER FUNCTIONS ====================
def calculate_bonus(streak: int) -> int:
    """Calculate bonus based on streak"""
    if streak <= 0:
        return BASE_BONUS
    
    # Check if streak qualifies for multiplier
    if streak in STREAK_MULTIPLIERS:
        return int(BASE_BONUS * STREAK_MULTIPLIERS[streak])
    
    # For streaks beyond 7 days, add extra bonus
    extra_days = streak - 7
    extra_bonus = min(extra_days * 10, MAX_STREAK_BONUS - 300)
    return min(300 + extra_bonus, MAX_STREAK_BONUS)

def get_streak_emoji(streak: int) -> str:
    """Get emoji based on streak length"""
    if streak == 0:
        return "🌱"
    elif streak < 3:
        return "🌿"
    elif streak < 7:
        return "🌳"
    elif streak < 14:
        return "🔥"
    elif streak < 30:
        return "⚡"
    else:
        return "👑"

def get_streak_title(streak: int) -> str:
    """Get title based on streak length"""
    if streak == 0:
        return "Newcomer"
    elif streak < 3:
        return "Starter"
    elif streak < 7:
        return "Regular"
    elif streak < 14:
        return "Dedicated"
    elif streak < 30:
        return "Champion"
    else:
        return "Legend"

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with image"""
    user = update.effective_user
    user_id = update.effective_chat.id

    # Initialize user if new
    if user_id not in user_data:
        user_data[user_id] = {
            'streak': 0,
            'total_bonus': 0,
            'last_claim': None,
            'joined': datetime.now().isoformat()
        }
        save_data()

    welcome_text = f"""🎁 **Welcome to Daily Bonus Bot!**

Hi {user.first_name}! 👋

Claim your daily bonus every day and build your streak!

💰 **How it works:**
• 📅 Claim your bonus every 24 hours
• 🔥 Build your streak for bigger rewards
• 🏆 Earn exclusive prizes

📊 **Streak Rewards:**
• Day 1: 💰 100 coins
• Day 3: 💰 150 coins
• Day 7: 💰 300 coins
• Day 14: 💰 400 coins
• Day 30+: 💰 500 coins

📌 **Commands:**
/start - Welcome menu
/claim - Claim your daily bonus
/status - Check your streak
/help - Need assistance?

🔥 **Don't break your streak!** Claim daily!
"""

    keyboard = [
        [InlineKeyboardButton("💰 Claim Bonus", callback_data="claim_bonus")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send image with caption
    try:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.info(f"✅ Welcome image sent to {user_id}")
    except Exception as e:
        logger.error(f"Error sending image: {e}")
        # Fallback: send text only
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def claim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim daily bonus"""
    user_id = update.effective_chat.id
    user = update.effective_user

    # Initialize user if new
    if user_id not in user_data:
        user_data[user_id] = {
            'streak': 0,
            'total_bonus': 0,
            'last_claim': None,
            'joined': datetime.now().isoformat()
        }

    data = user_data[user_id]
    now = datetime.now()

    # Check if already claimed today
    if data['last_claim']:
        last_claim = datetime.fromisoformat(data['last_claim'])
        time_diff = now - last_claim
        
        if time_diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - time_diff
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            
            await update.message.reply_text(
                f"⏳ **Already claimed today!**\n\n"
                f"Come back in {hours}h {minutes}m to claim your next bonus.\n\n"
                f"🔥 Current streak: {data['streak']} days\n"
                f"💰 Total earned: {data['total_bonus']} coins",
                parse_mode="Markdown"
            )
            return

    # Calculate bonus
    streak = data['streak']
    
    # Check if streak should continue or reset
    if data['last_claim']:
        last_claim = datetime.fromisoformat(data['last_claim'])
        days_diff = (now - last_claim).days
        if days_diff > 1:
            streak = 0  # Reset streak if more than 1 day missed

    # Increment streak
    new_streak = streak + 1
    bonus = calculate_bonus(new_streak)

    # Update user data
    data['streak'] = new_streak
    data['total_bonus'] = data.get('total_bonus', 0) + bonus
    data['last_claim'] = now.isoformat()
    save_data()

    # Get streak emoji and title
    emoji = get_streak_emoji(new_streak)
    title = get_streak_title(new_streak)

    # Create response message
    response = f"""🎉 **Bonus Claimed!** 🎉

{emoji} **{title}** - Day {new_streak}

💰 **Bonus earned:** {bonus} coins
📊 **Total coins:** {data['total_bonus']} coins
🔥 **Streak:** {new_streak} days

📅 **Next claim:** { (now + timedelta(hours=24)).strftime('%H:%M') } tomorrow

{f"🏆 **Bonus unlocked!** You've reached day {new_streak}!" if new_streak in STREAK_MULTIPLIERS or new_streak % 7 == 0 else ""}

Keep the streak alive! 🚀
"""

    keyboard = [
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        response,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user status"""
    user_id = update.effective_chat.id
    user = update.effective_user

    if user_id not in user_data:
        user_data[user_id] = {
            'streak': 0,
            'total_bonus': 0,
            'last_claim': None,
            'joined': datetime.now().isoformat()
        }

    data = user_data[user_id]
    streak = data['streak']
    emoji = get_streak_emoji(streak)
    title = get_streak_title(streak)

    # Calculate next bonus
    next_bonus = calculate_bonus(streak + 1)

    # Check if claimed today
    can_claim = True
    next_claim_time = ""
    if data['last_claim']:
        last_claim = datetime.fromisoformat(data['last_claim'])
        time_diff = datetime.now() - last_claim
        if time_diff < timedelta(hours=24):
            can_claim = False
            remaining = timedelta(hours=24) - time_diff
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            next_claim_time = f"{hours}h {minutes}m"

    status_text = f"""📊 **Your Daily Bonus Status**

👤 **User:** {user.first_name}

{emoji} **Title:** {title}
🔥 **Streak:** {streak} days
💰 **Total earned:** {data.get('total_bonus', 0)} coins
📅 **Joined:** {datetime.fromisoformat(data['joined']).strftime('%B %d, %Y')}

🎯 **Next bonus:** {next_bonus} coins
{f"⏳ **Available in:** {next_claim_time}" if not can_claim else "✅ **Ready to claim!**"}

{f"🏆 **Next milestone:** {7 - (streak % 7) if streak % 7 != 0 else '🎉 Milestone reached!'}" if streak > 0 else "Start your streak today!"}
"""

    keyboard = [
        [InlineKeyboardButton("💰 Claim Bonus", callback_data="claim_bonus")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        status_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """❓ **Help - Daily Bonus Bot**

🎁 **How it works:**

1️⃣ **Claim Daily Bonus:**
   Use /claim or click "Claim Bonus" every 24 hours

2️⃣ **Build Your Streak:**
   Claim every day to build your streak and earn bigger bonuses!

3️⃣ **Track Progress:**
   Use /status to see your streak and total earnings

📌 **Commands:**
/start - Welcome menu
/claim - Claim your daily bonus
/status - Check your streak
/help - This message

🎯 **Streak Rewards:**
| Day | Bonus |
|-----|-------|
| 1   | 100   |
| 3   | 150   |
| 7   | 300   |
| 14  | 400   |
| 30+ | 500   |

💡 **Pro Tip:** Never miss a day! Set a reminder to claim daily!
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ==================== CALLBACK HANDLERS ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "claim_bonus":
        await claim_command(update, context)
    
    elif query.data == "my_status":
        await status_command(update, context)
    
    elif query.data == "help":
        await help_command(update, context)
    
    elif query.data == "back_to_menu":
        user = update.effective_user
        welcome_text = f"""🎁 **Welcome back, {user.first_name}!**

What would you like to do?

📌 **Commands:**
/claim - Claim your daily bonus
/status - Check your streak
/help - Need assistance?
"""
        keyboard = [
            [InlineKeyboardButton("💰 Claim Bonus", callback_data="claim_bonus")],
            [InlineKeyboardButton("📊 My Status", callback_data="my_status")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ==================== AUTO-SAVE TASK ====================
async def auto_save():
    """Auto-save data every 5 minutes"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        save_data()
        logger.info("💾 Data saved automatically")

# ==================== MAIN ====================
async def main():
    """Start the bot"""
    logger.info("🎁 Starting Daily Bonus Bot...")
    logger.info(f"👥 {len(user_data)} users in database")
    logger.info(f"🖼️ Welcome image URL: {WELCOME_IMAGE_URL}")

    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("claim", claim_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add callback handler
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook removed, using polling mode")

    await application.start()
    await application.updater.start_polling()

    logger.info("✅ Daily Bonus Bot started successfully!")
    logger.info(f"👥 Users: {len(user_data)}")
    logger.info("🤖 Bot is ready to receive messages")

    # Start auto-save task
    asyncio.create_task(auto_save())

    # Keep running
    while True:
        await asyncio.sleep(3600)
        logger.info(f"📊 Status: {len(user_data)} users tracked")

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
