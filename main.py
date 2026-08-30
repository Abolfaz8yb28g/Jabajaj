import requests
import random
import time
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
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

# ========== دریافت پروکسی ==========
def get_proxies_from_github():
    """دریافت پروکسی از گیت‌هاب با هندلینگ خطا"""
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
            print(f"[{datetime.now()}] ✅ {len(proxies)} پروکسی دریافت شد")
            return proxies
        return []
    except Exception as e:
        print(f"[{datetime.now()}] ❌ خطا در دریافت پروکسی: {e}")
        return []

# ========== تابع اصلی ویو زدن با دیباگ ==========
async def run_views_async(message, url, user_id):
    """اجرای ویو زدن با لاگ کامل"""
    try:
        # تنظیم اولیه
        user_data[user_id]["status"] = "running"
        views_done = 0
        total_views = user_data[user_id].get("total_views", DEFAULT_VIEW_COUNT)
        
        # دریافت پروکسی
        proxy_list = get_proxies_from_github()
        if not proxy_list:
            print(f"[{datetime.now()}] ⚠️ بدون پروکسی - از IP خود استفاده می‌شود")
            await message.edit_text(
                f"🔄 **در حال ویو زدن...**\n"
                f"⚠️ پروکسی دریافت نشد، از IP خود استفاده می‌شود\n"
                f"✅ 0/{total_views} ویو ثبت شد"
            )
        
        # حلقه اصلی با لاگ کامل
        for i in range(total_views):
            try:
                # انتخاب User-Agent
                ua = random.choice(USER_AGENTS)
                
                # انتخاب پروکسی
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
                
                # ارسال درخواست با لاگ
                print(f"[{datetime.now()}] 📤 ارسال درخواست {i+1}/{total_views} - {proxy or 'بدون پروکسی'}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=30,
                    allow_redirects=True
                )
                
                # ثبت نتیجه
                if response.status_code == 200:
                    views_done += 1
                    print(f"[{datetime.now()}] ✅ ویو {i+1}/{total_views} ثبت شد - کد {response.status_code}")
                else:
                    print(f"[{datetime.now()}] ⚠️ کد خطا: {response.status_code}")
                
                # به‌روزرسانی پیام هر ۵ ویو
                user_data[user_id]["views_done"] = views_done
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
                        print(f"[{datetime.now()}] ⚠️ خطا در به‌روزرسانی پیام: {e}")
                
                # تاخیر تصادفی
                delay = random.uniform(3, 7)
                print(f"[{datetime.now()}] ⏳ تاخیر {delay:.1f} ثانیه")
                time.sleep(delay)
                
            except requests.exceptions.Timeout:
                print(f"[{datetime.now()}] ❌ تایم‌اوت در ویو {i+1}")
                time.sleep(5)
            except requests.exceptions.ConnectionError:
                print(f"[{datetime.now()}] ❌ خطای اتصال در ویو {i+1}")
                time.sleep(10)
            except Exception as e:
                print(f"[{datetime.now()}] ❌ خطای ناشناخته: {e}")
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
        print(f"[{datetime.now()}] ❌ خطای کلی: {e}")
        user_data[user_id]["status"] = "error"
        await message.edit_text(f"❌ **خطا در اجرا:**\n`{str(e)}`")

# ========== بقیه کد (Start, Handle URL, Button Handler) ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 **ربات ویو زن تلگرام**

لینک پست خود را به من بدهید تا ویو (بازدید) مصنوعی برای آن ثبت کنم.

🔗 **مثال:** `https://t.me/your_channel/123`

⚙️ **تنظیمات پیش‌فرض:**
- تعداد ویو: ۱۰۰

📊 **وضعیت:** آماده به کار
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

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
        "total_views": DEFAULT_VIEW_COUNT
    }
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع ویو زدن", callback_data="start_views")],
        [InlineKeyboardButton("📊 وضعیت", callback_data="status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ لینک پست دریافت شد:\n`{url}`\n\n"
        f"تعداد ویو: {DEFAULT_VIEW_COUNT}\n\n"
        f"برای شروع روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
        context.application.create_task(
            run_views_async(query.message, data["url"], user_id)
        )
        
    elif query.data == "status":
        status_text = f"📊 **وضعیت ربات:**\n\n"
        status_text += f"🔗 لینک: `{data.get('url')}`\n"
        status_text += f"📋 وضعیت: {data.get('status', 'نامشخص')}\n"
        status_text += f"✅ ویوهای ثبت شده: {data.get('views_done', 0)}\n"
        status_text += f"🎯 تعداد کل: {data.get('total_views', DEFAULT_VIEW_COUNT)}\n"
        await query.edit_message_text(status_text, parse_mode='Markdown')

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطا: توکن ربات تنظیم نشده است!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"[{datetime.now()}] 🤖 ربات ویو زن روشن شد!")
    application.run_polling()

if __name__ == "__main__":
    main()
