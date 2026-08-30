import requests
import random
import time
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== تنظیمات از متغیرهای محیطی ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEFAULT_VIEW_COUNT = int(os.getenv("DEFAULT_VIEW_COUNT", "100"))
MAX_THREADS = int(os.getenv("MAX_THREADS", "3"))
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "20"))

# ========== User-Agent های متنوع ==========
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
]

# ========== دیکشنری ذخیره وضعیت کاربران ==========
user_data = {}

# ========== تابع دریافت پروکسی از گیت‌هاب ==========
def get_proxies_from_github():
    """دریافت لیست پروکسی از مخزن گیت‌هاب"""
    try:
        url = "https://raw.githubusercontent.com/SoliSpirit/mtproto/main/all_proxies.txt"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            lines = response.text.splitlines()
            proxies = []
            for line in lines:
                # استخراج IP و پورت از فرمت tg://proxy?server=IP&port=PORT
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

# ========== تابع استخراج آیدی پست ==========
def extract_post_id(url):
    """استخراج آیدی پست از لینک تلگرام"""
    parts = url.split("/")
    try:
        if len(parts) >= 2:
            return parts[-1]
    except:
        return None
    return None

# ========== هندلر استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    welcome_text = """
🤖 **ربات ویو زن تلگرام**

لینک پست خود را به من بدهید تا ویو (بازدید) مصنوعی برای آن ثبت کنم.

🔗 **مثال:** `https://t.me/your_channel/123`

⚙️ **تنظیمات پیش‌فرض:**
- تعداد ویو: ۱۰۰
- ترد همزمان: ۳
- درخواست در دقیقه: ۲۰

📊 **وضعیت:** آماده به کار
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ========== هندلر دریافت لینک ==========
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت لینک پست از کاربر"""
    url = update.message.text.strip()
    user_id = update.effective_user.id
    
    # اعتبارسنجی لینک
    if not url.startswith("https://t.me/"):
        await update.message.reply_text(
            "❌ لطفاً یک لینک معتبر از تلگرام وارد کنید:\n`https://t.me/username/123`",
            parse_mode='Markdown'
        )
        return
    
    # استخراج آیدی پست
    post_id = extract_post_id(url)
    if not post_id:
        await update.message.reply_text(
            "❌ فرمت لینک نامعتبر است. لطفاً از فرمت زیر استفاده کنید:\n`https://t.me/username/123`",
            parse_mode='Markdown'
        )
        return
    
    # ذخیره اطلاعات کاربر
    user_data[user_id] = {
        "url": url,
        "post_id": post_id,
        "status": "pending",
        "views_done": 0,
        "total_views": DEFAULT_VIEW_COUNT
    }
    
    # دکمه‌های عملیات
    keyboard = [
        [InlineKeyboardButton("🚀 شروع ویو زدن", callback_data="start_views")],
        [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ لینک پست دریافت شد:\n`{url}`\n\n"
        f"آیدی پست: `{post_id}`\n"
        f"تعداد ویو: {DEFAULT_VIEW_COUNT}\n\n"
        f"برای شروع روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ========== هندلر دکمه‌ها ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    
    if not data:
        await query.edit_message_text("❌ ابتدا لینک پست را ارسال کنید.")
        return
    
    if query.data == "start_views":
        # شروع ویو زدن
        await query.edit_message_text("🔄 **در حال شروع ویو زدن...**\n⏳ لطفاً صبر کنید.")
        
        # اجرا در پس‌زمینه
        context.application.create_task(
            run_views_async(query.message, data["url"], user_id)
        )
        
    elif query.data == "status":
        # نمایش وضعیت
        status_text = f"📊 **وضعیت ربات:**\n\n"
        status_text += f"🔗 لینک: `{data.get('url')}`\n"
        status_text += f"📋 وضعیت: {data.get('status', 'نامشخص')}\n"
        status_text += f"✅ ویوهای ثبت شده: {data.get('views_done', 0)}\n"
        status_text += f"🎯 تعداد کل: {data.get('total_views', DEFAULT_VIEW_COUNT)}\n"
        
        if data.get('status') == 'running':
            status_text += f"⏳ در حال اجرا..."
        elif data.get('status') == 'completed':
            status_text += f"✅ تکمیل شد!"
        
        await query.edit_message_text(status_text, parse_mode='Markdown')

# ========== تابع اصلی ویو زدن ==========
async def run_views_async(message, url, user_id):
    """اجرای عملیات ویو زدن در پس‌زمینه"""
    try:
        # به‌روزرسانی وضعیت
        user_data[user_id]["status"] = "running"
        views_done = 0
        total_views = user_data[user_id].get("total_views", DEFAULT_VIEW_COUNT)
        
        # دریافت لیست پروکسی
        proxy_list = get_proxies_from_github()
        if not proxy_list:
            # اگر پروکسی دریافت نشد، از IP خود استفاده کن
            print("⚠️ پروکسی دریافت نشد، از IP خود استفاده می‌شود.")
        
        # حلقه اصلی ویو زدن
        for i in range(total_views):
            # انتخاب User-Agent تصادفی
            ua = random.choice(USER_AGENTS)
            
            # انتخاب پروکسی تصادفی (اگر موجود باشد)
            proxy = random.choice(proxy_list) if proxy_list else None
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            # هدرهای درخواست
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            try:
                # ارسال درخواست
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=15,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    views_done += 1
                    print(f"[{datetime.now()}] ✅ ویو {i+1}/{total_views} ثبت شد - {proxy or 'IP خود'}")
                else:
                    print(f"[{datetime.now()}] ⚠️ کد خطا: {response.status_code}")
                
                # به‌روزرسانی وضعیت هر ۱۰ ویو
                user_data[user_id]["views_done"] = views_done
                if i % 10 == 0 or i == total_views - 1:
                    await message.edit_text(
                        f"🔄 **در حال ویو زدن...**\n"
                        f"✅ {views_done}/{total_views} ویو ثبت شد\n"
                        f"⏳ {total_views - views_done} ویو باقی‌مانده\n"
                        f"🌐 {proxy or 'بدون پروکسی'}"
                    )
                
                # تاخیر تصادفی برای امنیت (۲ تا ۵ ثانیه)
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"[{datetime.now()}] ❌ خطا: {e}")
                time.sleep(5)
        
        # اتمام عملیات
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
        user_data[user_id]["status"] = "error"
        await message.edit_text(f"❌ **خطا در اجرا:**\n`{str(e)}`")

# ========== تابع اصلی ==========
def main():
    """راه‌اندازی ربات"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطا: توکن ربات تنظیم نشده است!")
        print("لطفاً متغیر محیطی BOT_TOKEN را تنظیم کنید.")
        return
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # شروع ربات
    print(f"[{datetime.now()}] 🤖 ربات ویو زن روشن شد!")
    print(f"[{datetime.now()}] 📊 تنظیمات:")
    print(f"   - تعداد ویو: {DEFAULT_VIEW_COUNT}")
    print(f"   - ترد همزمان: {MAX_THREADS}")
    print(f"   - درخواست در دقیقه: {MAX_REQUESTS_PER_MINUTE}")
    
    application.run_polling()

if __name__ == "__main__":
    main()
