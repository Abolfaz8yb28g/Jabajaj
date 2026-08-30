import requests
import random
import time
import os
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== تنظیمات ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEFAULT_VIEW_COUNT = int(os.getenv("DEFAULT_VIEW_COUNT", "100"))

# ========== User-Agent ==========
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
]

user_data = {}

# ========== دریافت پروکسی از گیت‌هاب ==========
def get_proxies_from_github():
    try:
        url = "https://raw.githubusercontent.com/SoliSpirit/mtproto/main/all_proxies.txt"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            lines = response.text.splitlines()
            proxies = []
            for line in lines:
                match = re.search(r'server=([^&]+)&port=(\d+)', line)
                if match:
                    ip = match.group(1)
                    port = match.group(2)
                    proxies.append(f"http://{ip}:{port}")
            return proxies
        return []
    except Exception as e:
        print(f"❌ خطا در دریافت پروکسی: {e}")
        return []

# ========== تابع اصلی ویو زدن ==========
async def run_views_async(message, user_id):
    """اجرای ویو زدن"""
    try:
        data = user_data.get(user_id)
        if not data:
            await message.edit_text("❌ خطا: اطلاعات یافت نشد.")
            return
        
        url = data["url"]
        total_views = data.get("total_views", DEFAULT_VIEW_COUNT)
        use_custom = data.get("use_custom_proxy", False)
        custom_proxies = data.get("proxies", []) if use_custom else []
        
        # انتخاب منبع پروکسی
        if use_custom and custom_proxies:
            proxy_list = custom_proxies
            await message.edit_text(
                f"🔄 **در حال ویو زدن با پروکسی دستی...**\n"
                f"📦 تعداد پروکسی: {len(proxy_list)}\n"
                f"✅ 0/{total_views} ویو ثبت شد"
            )
        else:
            proxy_list = get_proxies_from_github()
            if proxy_list:
                await message.edit_text(
                    f"🔄 **در حال ویو زدن با پروکسی خودکار...**\n"
                    f"📦 {len(proxy_list)} پروکسی از گیت‌هاب\n"
                    f"✅ 0/{total_views} ویو ثبت شد"
                )
            else:
                await message.edit_text(
                    f"🔄 **در حال ویو زدن...**\n"
                    f"⚠️ بدون پروکسی - از IP خود\n"
                    f"✅ 0/{total_views} ویو ثبت شد"
                )
        
        views_done = 0
        
        for i in range(total_views):
            try:
                ua = random.choice(USER_AGENTS)
                proxy = random.choice(proxy_list) if proxy_list else None
                proxies = {"http": proxy, "https": proxy} if proxy else None
                
                headers = {
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Cache-Control": "max-age=0"
                }
                
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    views_done += 1
                    print(f"[{datetime.now()}] ✅ ویو {i+1}/{total_views} ثبت شد")
                else:
                    print(f"[{datetime.now()}] ⚠️ کد خطا: {response.status_code}")
                
                user_data[user_id]["views_done"] = views_done
                
                if i % 5 == 0 or i == total_views - 1:
                    try:
                        await message.edit_text(
                            f"🔄 **در حال ویو زدن...**\n"
                            f"✅ {views_done}/{total_views} ویو ثبت شد\n"
                            f"⏳ {total_views - views_done} ویو باقی‌مانده\n"
                            f"🌐 {proxy or 'بدون پروکسی'}"
                        )
                    except Exception as e:
                        print(f"⚠️ خطا در به‌روزرسانی: {e}")
                
                time.sleep(random.uniform(3, 7))
                
            except Exception as e:
                print(f"❌ خطا: {e}")
                time.sleep(5)
        
        user_data[user_id]["status"] = "completed"
        user_data[user_id]["views_done"] = views_done
        
        # منوی بعد از اتمام
        keyboard = [
            [InlineKeyboardButton("🔄 ویو مجدد", callback_data="start_views")],
            [InlineKeyboardButton("📊 وضعیت", callback_data="status")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            f"✅ **عملیات کامل شد!**\n\n"
            f"🔗 لینک: `{url}`\n"
            f"✅ ویوهای ثبت شده: {views_done}/{total_views}\n"
            f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ خطای کلی: {e}")
        user_data[user_id]["status"] = "error"
        await message.edit_text(f"❌ **خطا در اجرا:**\n`{str(e)}`")

# ========== هندلر استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # تنظیم اولیه
    if user_id not in user_data:
        user_data[user_id] = {
            "proxies": [],
            "use_custom_proxy": False
        }
    
    keyboard = [
        [InlineKeyboardButton("📝 ثبت لینک جدید", callback_data="new_link")],
        [InlineKeyboardButton("📦 مدیریت پروکسی", callback_data="manage_proxy")],
        [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **ربات ویو زن تلگرام**\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ========== هندلر دکمه‌ها ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # ===== منوی اصلی =====
    if query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📝 ثبت لینک جدید", callback_data="new_link")],
            [InlineKeyboardButton("📦 مدیریت پروکسی", callback_data="manage_proxy")],
            [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔙 **منوی اصلی:**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # ===== ثبت لینک جدید =====
    if query.data == "new_link":
        await query.edit_message_text(
            "📝 **لطفاً لینک پست خود را ارسال کنید.**\n\n"
            "مثال: `https://t.me/your_channel/123`"
        )
        return
    
    # ===== مدیریت پروکسی =====
    if query.data == "manage_proxy":
        proxies = user_data.get(user_id, {}).get("proxies", [])
        use_custom = user_data.get(user_id, {}).get("use_custom_proxy", False)
        
        status = "✅ فعال" if use_custom else "❌ غیرفعال"
        count = len(proxies)
        
        keyboard = [
            [InlineKeyboardButton("➕ اضافه کردن پروکسی", callback_data="add_proxy")],
            [InlineKeyboardButton("📋 مشاهده پروکسی‌ها", callback_data="view_proxies")],
            [InlineKeyboardButton("🗑️ پاک کردن همه", callback_data="clear_proxies")],
            [InlineKeyboardButton("🔄 تغییر حالت پروکسی", callback_data="toggle_proxy")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📦 **مدیریت پروکسی**\n\n"
            f"وضعیت: {status}\n"
            f"تعداد پروکسی: {count}\n\n"
            f"در صورت فعال بودن، از پروکسی دستی استفاده می‌شود.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # ===== تغییر حالت پروکسی =====
    if query.data == "toggle_proxy":
        if user_id not in user_data:
            user_data[user_id] = {}
        current = user_data[user_id].get("use_custom_proxy", False)
        user_data[user_id]["use_custom_proxy"] = not current
        
        new_status = "✅ فعال" if not current else "❌ غیرفعال"
        await query.edit_message_text(
            f"🔄 **حالت پروکسی تغییر کرد.**\n\n"
            f"وضعیت جدید: {new_status}\n\n"
            f"🔙 برای بازگشت به منوی مدیریت کلیک کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data="manage_proxy")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # ===== اضافه کردن پروکسی =====
    if query.data == "add_proxy":
        await query.edit_message_text(
            "➕ **لطفاً پروکسی را به فرمت زیر وارد کنید:**\n\n"
            "`http://ip:port`\n\n"
            "مثال: `http://185.143.234.45:8080`\n\n"
            "⚠️ هر بار فقط یک پروکسی وارد کنید.",
            parse_mode='Markdown'
        )
        return
    
    # ===== مشاهده پروکسی‌ها =====
    if query.data == "view_proxies":
        proxies = user_data.get(user_id, {}).get("proxies", [])
        if not proxies:
            await query.edit_message_text(
                "📭 **هیچ پروکسی ذخیره نشده است.**\n\n"
                "از گزینه **➕ اضافه کردن پروکسی** استفاده کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_proxy")]
                ]),
                parse_mode='Markdown'
            )
            return
        
        text = "📋 **لیست پروکسی‌های ذخیره شده:**\n\n"
        for i, proxy in enumerate(proxies, 1):
            text += f"{i}. `{proxy}`\n"
        text += f"\n📊 تعداد: {len(proxies)}"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_proxy")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # ===== پاک کردن پروکسی‌ها =====
    if query.data == "clear_proxies":
        if user_id in user_data:
            user_data[user_id]["proxies"] = []
        await query.edit_message_text(
            "🗑️ **همه پروکسی‌ها پاک شدند.**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_proxy")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # ===== شروع ویو زدن =====
    if query.data == "start_views":
        data = user_data.get(user_id)
        if not data or "url" not in data:
            await query.edit_message_text(
                "❌ **لطفاً ابتدا لینک پست را ارسال کنید.**\n\n"
                "از منوی اصلی گزینه **📝 ثبت لینک جدید** را انتخاب کنید."
            )
            return
        
        await query.edit_message_text("🔄 **در حال شروع ویو زدن...**\n⏳ لطفاً صبر کنید.")
        context.application.create_task(run_views_async(query.message, user_id))
        return
    
    # ===== وضعیت =====
    if query.data == "status":
        data = user_data.get(user_id, {})
        proxies = data.get("proxies", [])
        use_custom = data.get("use_custom_proxy", False)
        
        status_text = f"📊 **وضعیت ربات:**\n\n"
        status_text += f"📦 پروکسی دستی: {len(proxies)} عدد\n"
        status_text += f"🔄 حالت پروکسی: {'✅ فعال' if use_custom else '❌ غیرفعال'}\n"
        status_text += f"🔗 لینک: {data.get('url', '❌ ثبت نشده')}\n"
        status_text += f"✅ ویوهای ثبت شده: {data.get('views_done', 0)}\n"
        status_text += f"🎯 تعداد کل: {data.get('total_views', DEFAULT_VIEW_COUNT)}\n"
        status_text += f"📋 وضعیت: {data.get('status', 'آماده')}"
        
        keyboard = [
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

# ========== هندلر دریافت لینک ==========
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id
    
    if not url.startswith("https://t.me/"):
        await update.message.reply_text(
            "❌ لطفاً یک لینک معتبر از تلگرام وارد کنید:\n`https://t.me/username/123`",
            parse_mode='Markdown'
        )
        return
    
    if user_id not in user_data:
        user_data[user_id] = {"proxies": []}
    
    user_data[user_id]["url"] = url
    user_data[user_id]["post_id"] = url.split("/")[-1]
    user_data[user_id]["status"] = "pending"
    user_data[user_id]["views_done"] = 0
    user_data[user_id]["total_views"] = DEFAULT_VIEW_COUNT
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع ویو زدن", callback_data="start_views")],
        [InlineKeyboardButton("📦 مدیریت پروکسی", callback_data="manage_proxy")],
        [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ **لینک پست دریافت شد:**\n`{url}`\n\n"
        f"🎯 تعداد ویو: {DEFAULT_VIEW_COUNT}\n"
        f"📦 پروکسی دستی: {len(user_data[user_id].get('proxies', []))} عدد\n"
        f"🔄 حالت پروکسی: {'✅ فعال' if user_data[user_id].get('use_custom_proxy', False) else '❌ غیرفعال'}\n\n"
        f"برای شروع روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ========== هندلر دریافت پروکسی دستی ==========
async def handle_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پروکسی دستی از کاربر (برای دستور /proxy)"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ لطفاً پروکسی را وارد کنید:\n"
            "`/proxy http://ip:port`\n"
            "مثال: `/proxy http://185.143.234.45:8080`",
            parse_mode='Markdown'
        )
        return
    
    proxy = context.args[0]
    
    if not proxy.startswith("http://") and not proxy.startswith("https://"):
        await update.message.reply_text(
            "❌ فرمت پروکسی نامعتبر است.\n"
            "لطفاً از فرمت زیر استفاده کنید:\n"
            "`http://ip:port`",
            parse_mode='Markdown'
        )
        return
    
    if user_id not in user_data:
        user_data[user_id] = {"proxies": []}
    
    if "proxies" not in user_data[user_id]:
        user_data[user_id]["proxies"] = []
    
    user_data[user_id]["proxies"].append(proxy)
    
    await update.message.reply_text(
        f"✅ **پروکسی اضافه شد:**\n`{proxy}`\n\n"
        f"📦 تعداد پروکسی‌ها: {len(user_data[user_id]['proxies'])}"
    )

# ========== تابع اصلی ==========
def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطا: توکن ربات تنظیم نشده است!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proxy", handle_proxy))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"[{datetime.now()}] 🤖 ربات ویو زن روشن شد!")
    print(f"[{datetime.now()}] 📊 دستورات:")
    print(f"   - /start  (منوی اصلی)")
    print(f"   - /proxy http://ip:port  (اضافه کردن پروکسی)")
    
    application.run_polling()

if __name__ == "__main__":
    main()
