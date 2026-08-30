import requests
import random
import time
import os
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== توکن ربات ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEFAULT_VIEW_COUNT = 100

# ========== User-Agent ==========
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
]

# ========== دیکشنری کاربران ==========
user_data = {}

# ========== دریافت پروکسی از گیت‌هاب ==========
def get_proxies():
    try:
        url = "https://raw.githubusercontent.com/SoliSpirit/mtproto/main/all_proxies.txt"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            proxies = []
            for line in r.text.splitlines():
                match = re.search(r'server=([^&]+)&port=(\d+)', line)
                if match:
                    proxies.append(f"http://{match.group(1)}:{match.group(2)}")
            return proxies
    except:
        pass
    return []

# ========== دستور /start ==========
async def start(update: Update, context):
    await update.message.reply_text(
        "🤖 **ربات ویو زن تلگرام**\n\n"
        "دستورات:\n"
        "1. لینک پست رو مستقیماً به ربات بفرست\n"
        "2. برای اضافه کردن پروکسی دستی:\n"
        "   `/proxy http://ip:port`\n"
        "3. برای مشاهده پروکسی‌ها:\n"
        "   `/proxies`\n"
        "4. برای پاک کردن پروکسی‌ها:\n"
        "   `/clear`\n\n"
        "بعد از ارسال لینک، دکمه‌ها ظاهر می‌شن.",
        parse_mode='Markdown'
    )

# ========== دستور /proxy ==========
async def add_proxy(update: Update, context):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("مثال: `/proxy http://185.143.234.45:8080`", parse_mode='Markdown')
        return
    proxy = context.args[0]
    if not proxy.startswith("http://") and not proxy.startswith("https://"):
        await update.message.reply_text("فرمت اشتباه. باید با http:// یا https:// شروع بشه.")
        return
    if user_id not in user_data:
        user_data[user_id] = {"proxies": []}
    user_data[user_id]["proxies"].append(proxy)
    await update.message.reply_text(f"✅ پروکسی اضافه شد: `{proxy}`\nتعداد: {len(user_data[user_id]['proxies'])}", parse_mode='Markdown')

# ========== دستور /proxies ==========
async def show_proxies(update: Update, context):
    user_id = update.effective_user.id
    proxies = user_data.get(user_id, {}).get("proxies", [])
    if not proxies:
        await update.message.reply_text("📭 هیچ پروکسی ذخیره نشده.")
        return
    text = "📋 لیست پروکسی‌ها:\n" + "\n".join([f"{i+1}. `{p}`" for i, p in enumerate(proxies)])
    await update.message.reply_text(text, parse_mode='Markdown')

# ========== دستور /clear ==========
async def clear_proxies(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id]["proxies"] = []
    await update.message.reply_text("🗑️ همه پروکسی‌ها پاک شدن.")

# ========== دریافت لینک ==========
async def handle_url(update: Update, context):
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if not url.startswith("https://t.me/"):
        await update.message.reply_text("❌ لینک باید با https://t.me/ شروع بشه.")
        return

    if user_id not in user_data:
        user_data[user_id] = {"proxies": []}

    user_data[user_id]["url"] = url
    user_data[user_id]["status"] = "ready"
    user_data[user_id]["views_done"] = 0

    keyboard = [
        [InlineKeyboardButton("🚀 شروع ویو", callback_data="start")],
        [InlineKeyboardButton("📦 پروکسی دستی", callback_data="proxy_menu")],
        [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
    ]
    await update.message.reply_text(
        f"✅ لینک دریافت شد:\n`{url}`\n\n"
        f"تعداد ویو: {DEFAULT_VIEW_COUNT}\n"
        f"پروکسی دستی: {len(user_data[user_id]['proxies'])} عدد\n"
        f"حالت پروکسی: {'✅ فعال' if user_data[user_id].get('use_custom', False) else '❌ غیرفعال'}\n\n"
        f"یکی از دکمه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ========== دکمه‌ها ==========
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = user_data.get(user_id)

    if not data or "url" not in data:
        await query.edit_message_text("❌ اول لینک رو بفرست.")
        return

    if query.data == "start":
        await query.edit_message_text("⏳ شروع ویو زدن...")
        context.application.create_task(run_views(query.message, user_id))

    elif query.data == "proxy_menu":
        keyboard = [
            [InlineKeyboardButton("✅ فعال کردن پروکسی دستی", callback_data="enable_proxy")],
            [InlineKeyboardButton("❌ غیرفعال کردن", callback_data="disable_proxy")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
        ]
        await query.edit_message_text(
            f"📦 **مدیریت پروکسی**\n\n"
            f"تعداد پروکسی: {len(data.get('proxies', []))}\n"
            f"وضعیت: {'✅ فعال' if data.get('use_custom', False) else '❌ غیرفعال'}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == "enable_proxy":
        data["use_custom"] = True
        await query.edit_message_text("✅ پروکسی دستی فعال شد. برگشت به منو...")
        await asyncio.sleep(1)
        await button_handler(update, context)

    elif query.data == "disable_proxy":
        data["use_custom"] = False
        await query.edit_message_text("❌ پروکسی دستی غیرفعال شد.")
        await asyncio.sleep(1)
        await button_handler(update, context)

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🚀 شروع ویو", callback_data="start")],
            [InlineKeyboardButton("📦 پروکسی دستی", callback_data="proxy_menu")],
            [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
        ]
        await query.edit_message_text(
            f"🔙 منوی اصلی:\n`{data['url']}`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == "status":
        await query.edit_message_text(
            f"📊 وضعیت:\n"
            f"لینک: {data.get('url')}\n"
            f"ویو: {data.get('views_done', 0)}/{DEFAULT_VIEW_COUNT}\n"
            f"پروکسی: {len(data.get('proxies', []))} عدد\n"
            f"حالت: {'دستی' if data.get('use_custom', False) else 'خودکار'}"
        )

# ========== تابع ویو زدن ==========
async def run_views(message, user_id):
    data = user_data.get(user_id)
    url = data["url"]
    total = DEFAULT_VIEW_COUNT
    use_custom = data.get("use_custom", False)
    proxies = data.get("proxies", []) if use_custom else get_proxies()

    if use_custom and not proxies:
        await message.edit_text("⚠️ پروکسی دستی فعاله ولی هیچ پروکسی ذخیره نشده! اول با /proxy اضافه کن.")
        return

    for i in range(total):
        try:
            proxy = random.choice(proxies) if proxies else None
            ua = random.choice(USER_AGENTS)
            headers = {"User-Agent": ua}
            r = requests.get(url, headers=headers, proxies={"http": proxy, "https": proxy} if proxy else None, timeout=10)
            if r.status_code == 200:
                data["views_done"] += 1
            if i % 5 == 0 or i == total-1:
                await message.edit_text(f"🔄 ویو {i+1}/{total}\n✅ {data['views_done']} موفق\n🌐 {proxy or 'بدون پروکسی'}")
            time.sleep(random.uniform(3, 6))
        except:
            time.sleep(5)

    await message.edit_text(f"✅ کامل شد! {data['views_done']}/{total} ویو ثبت شد.")

# ========== اجرا ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("proxy", add_proxy))
    app.add_handler(CommandHandler("proxies", show_proxies))
    app.add_handler(CommandHandler("clear", clear_proxies))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
