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

# ========== دریافت پروکسی از گیت‌هاب (خودکار) ==========
def get_proxies_from_github():
    """دریافت پروکسی از گیت‌هاب"""
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

# ========== تابع اصلی ویو زدن با پروکسی دستی ==========
async def run_views_async(message, url, user_id, custom_proxies=None):
    """اجرای ویو زدن با پروکسی دستی یا خودکار"""
    try:
        user_data[user_id]["status"] = "running"
        views_done = 0
        total_views = user_data[user_id].get("total_views", DEFAULT_VIEW_COUNT)
        
        # ========== انتخاب پروکسی ==========
        proxy_list = []
        
        # اولویت ۱: پروکسی دستی کاربر
        if custom_proxies:
            proxy_list = custom_proxies
            await message.edit_text(
                f"🔄 **در حال ویو زدن...**\n"
                f"✅ از پروکسی دستی استفاده می‌شود\n"
                f"📊 تعداد پروکسی: {len(proxy_list)}\n"
                f"✅ 0/{total_views} ویو ثبت شد"
            )
        else:
            # اولویت ۲: پروکسی خودکار از گیت‌هاب
            proxy_list = get_proxies_from_github()
            if proxy_list:
                await message.edit_text(
                    f"🔄 **در حال ویو زدن...**\n"
                    f"✅ {len(proxy_list)} پروکسی از گیت‌هاب دریافت شد\n"
                    f"✅ 0/{total_views} ویو ثبت شد"
                )
            else:
                await message.edit_text(
                    f"🔄 **در حال ویو زدن...**\n"
                    f"⚠️ بدون پروکسی - از IP خود استفاده می‌شود\n"
                    f"✅ 0/{total_views} ویو ثبت شد"
                )
        
        # حلقه اصلی
        for i in range(total_views):
            try:
                ua = random.choice(USER_AGENTS)
                
                # انتخاب پروکسی تصادفی
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
                
                print(f"[{datetime.now()}] 📤 ارسال درخواست {i+1}/{total_views} - {proxy or 'بدون پروکسی'}")
                
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
                
                # به‌روزرسانی هر ۵ ویو
                if i % 5 == 0 or i == total_views - 1:
                    try:
                        await message.edit_text(
                            f"🔄 **در حال ویو زدن...**\n"
                            f"✅ {views_done}/{total_views} ویو ثبت شد\n"
                            f"⏳ {total_views - views_done} ویو باقی‌مانده\n"
                            f"🌐 {proxy or 'بدون پروکسی'}\n"
                            f"📊 وضعیت: در حال اجرا"
                        )
                    except Exception as e:
                        print(f"⚠️ خطا در به‌روزرسانی پیام: {e}")
                
                delay = random.uniform(3, 7)
                time.sleep(delay)
                
            except Exception as e:
                print(f"❌ خطا: {e}")
                time.sleep(5)
        
        # اتمام
        user_data[user_id]["status"] = "completed"
        user_data[user_id]["views_done"] = views_done
        
        await message.edit_text(
            f"✅ **عملیات کامل شد!**\n\n"
            f"🔗 لینک: `{url}`\n"
            f"✅ ویوهای ثبت شده: {views_done}/{total_views}\n"
            f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🔄 برای اجرای مجدد، لینک جدید ارسال کنید."
        )
        
    except Exception as e:
        print(f"❌ خطای کلی: {e}")
        user_data[user_id]["status"] = "error"
        await message.edit_text(f"❌ **خطا در اجرا:**\n`{str(e)}`")

# ========== هندلر استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 **ربات ویو زن تلگرام**

**روش استفاده:**
1️⃣ لینک پست را ارسال کنید
2️⃣ روی دکمه شروع کلیک کنید

**برای استفاده از پروکسی دستی:**
📝 `/proxy http://ip:port`  
مثال: `/proxy http://185.143.234.45:8080`

📝 `/proxy_list` - برای مشاهده پروکسی‌های ذخیره شده

**توجه:** اگر پروکسی دستی وارد نکنید، از پروکسی خودکار استفاده می‌شود.
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ========== هندلر پروکسی دستی ==========
async def handle_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پروکسی دستی از کاربر"""
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
    
    # اعتبارسنجی ساده
    if not proxy.startswith("http://") and not proxy.startswith("https://"):
        await update.message.reply_text(
            "❌ فرمت پروکسی نامعتبر است.\n"
            "لطفاً از فرمت زیر استفاده کنید:\n"
            "`http://ip:port` یا `https://ip:port`",
            parse_mode='Markdown'
        )
        return
    
    # ذخیره پروکسی
    if "proxies" not in user_data.get(user_id, {}):
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["proxies"] = []
    
    user_data[user_id]["proxies"].append(proxy)
    
    await update.message.reply_text(
        f"✅ پروکسی اضافه شد:\n`{proxy}`\n\n"
        f"📊 تعداد پروکسی‌های ذخیره شده: {len(user_data[user_id]['proxies'])}"
    )

# ========== هندلر مشاهده پروکسی‌ها ==========
async def handle_proxy_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست پروکسی‌های ذخیره شده"""
    user_id = update.effective_user.id
    data = user_data.get(user_id, {})
    proxies = data.get("proxies", [])
    
    if not proxies:
        await update.message.reply_text("📭 **هیچ پروکسی دستی ذخیره نشده است.**")
        return
    
    text = "📋 **لیست پروکسی‌های ذخیره شده:**\n\n"
    for i, proxy in enumerate(proxies, 1):
        text += f"{i}. `{proxy}`\n"
    
    text += f"\n📊 تعداد: {len(proxies)}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ========== هندلر پاک کردن پروکسی‌ها ==========
async def handle_clear_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن پروکسی‌های ذخیره شده"""
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id]["proxies"] = []
        await update.message.reply_text("🗑️ **همه پروکسی‌های دستی پاک شدند.**")
    else:
        await update.message.reply_text("📭 **هیچ پروکسی برای پاک کردن وجود ندارد.**")

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
    
    post_id = url.split("/")[-1]
    
    user_data[user_id] = {
        "url": url,
        "post_id": post_id,
        "status": "pending",
        "views_done": 0,
        "total_views": DEFAULT_VIEW_COUNT,
        "proxies": user_data.get(user_id, {}).get("proxies", [])  # حفظ پروکسی‌های قبلی
    }
    
    # نمایش وضعیت پروکسی
    proxy_status = f"✅ {len(user_data[user_id]['proxies'])} پروکسی دستی ذخیره شده" if user_data[user_id]['proxies'] else "⚠️ بدون پروکسی دستی - از خودکار استفاده می‌شود"
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع ویو زدن", callback_data="start_views")],
        [InlineKeyboardButton("📊 وضعیت", callback_data="status")],
        [InlineKeyboardButton("🔄 استفاده از پروکسی دستی", callback_data="use_custom_proxy")],
        [InlineKeyboardButton("🌐 استفاده از پروکسی خودکار", callback_data="use_auto_proxy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ لینک پست دریافت شد:\n`{url}`\n\n"
        f"تعداد ویو: {DEFAULT_VIEW_COUNT}\n"
        f"پروکسی: {proxy_status}\n\n"
        f"برای شروع روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ========== هندلر دکمه‌ها ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    
    if not data:
        await query.edit_message_text("❌ ابتدا لینک پست را ارسال کنید.")
        return
    
    if query.data == "start_views":
        await query.edit_message_text("🔄 **در حال شروع ویو زدن...**\n⏳ لطفاً صبر کنید.")
        
        # بررسی استفاده از پروکسی دستی یا خودکار
        use_custom = data.get("use_custom_proxy", False)
        custom_proxies = data.get("proxies", []) if use_custom else None
        
        context.application.create_task(
            run_views_async(query.message, data["url"], user_id, custom_proxies)
        )
        
    elif query.data == "status":
        status_text = f"📊 **وضعیت ربات:**\n\n"
        status_text += f"🔗 لینک: `{data.get('url')}`\n"
        status_text += f"📋 وضعیت: {data.get('status', 'نامشخص')}\n"
        status_text += f"✅ ویوهای ثبت شده: {data.get('views_done', 0)}\n"
        status_text += f"🎯 تعداد کل: {data.get('total_views', DEFAULT_VIEW_COUNT)}\n"
        status_text += f"📦 پروکسی دستی: {len(data.get('proxies', []))} عدد"
        await query.edit_message_text(status_text, parse_mode='Markdown')
    
    elif query.data == "use_custom_proxy":
        data["use_custom_proxy"] = True
        proxies = data.get("proxies", [])
        if proxies:
            await query.edit_message_text(
                f"✅ **حالت پروکسی دستی فعال شد.**\n\n"
                f"📦 تعداد پروکسی: {len(proxies)}\n"
                f"🔹 اولین پروکسی: `{proxies[0]}`\n\n"
                f"حالا روی دکمه **شروع ویو زدن** کلیک کنید."
            )
        else:
            await query.edit_message_text(
                "❌ **هیچ پروکسی دستی ذخیره نشده است.**\n\n"
                "لطفاً ابتدا با دستور `/proxy` پروکسی اضافه کنید.\n"
                "مثال: `/proxy http://185.143.234.45:8080`"
            )
    
    elif query.data == "use_auto_proxy":
        data["use_custom_proxy"] = False
        await query.edit_message_text(
            "✅ **حالت پروکسی خودکار فعال شد.**\n\n"
            "پروکسی از گیت‌هاب دریافت می‌شود.\n"
            "حالا روی دکمه **شروع ویو زدن** کلیک کنید."
        )

# ========== تابع اصلی ==========
def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطا: توکن ربات تنظیم نشده است!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proxy", handle_proxy))
    application.add_handler(CommandHandler("proxy_list", handle_proxy_list))
    application.add_handler(CommandHandler("clear_proxies", handle_clear_proxies))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"[{datetime.now()}] 🤖 ربات ویو زن با پشتیبانی از پروکسی دستی روشن شد!")
    print(f"[{datetime.now()}] 📊 دستورات:")
    print(f"   - /proxy http://ip:port  (اضافه کردن پروکسی)")
    print(f"   - /proxy_list  (مشاهده پروکسی‌ها)")
    print(f"   - /clear_proxies  (پاک کردن پروکسی‌ها)")
    
    application.run_polling()

if __name__ == "__main__":
    main()
