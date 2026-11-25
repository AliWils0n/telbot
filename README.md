# Zero Lost | زیرولاست

ربات تلگرامی که لینک‌های V2Ray و پروکسی MTProto را از منابع عمومی جمع می‌کند و در `@ZiroLost` منتشر می‌کند. پایین هر پست هم لینک کانال اصلی، کانال اطلاع‌رسانی VIP و ربات قرار می‌گیرد.

ربات فقط باز شدن اتصال TCP را از سرور خودش بررسی می‌کند؛ این تست تضمین نمی‌کند که کانفیگ از اینترنت کاربر هم وصل شود. برای اجرای ربات نیازی به باز کردن پورت ورودی نیست.

## نصب روی Ubuntu یا Debian

اول ربات را در کانال `@ZiroLost` ادمین کن و اجازهٔ **ارسال پیام** بده. مراحل زیر فرض می‌کنند فایل‌های `bot.py`، `requirements.txt` و `zero-lost.service` در ریشهٔ مخزن هستند.

```bash
sudo apt update
sudo apt install -y git python3-venv
git clone https://github.com/AliWils0n/telbot.git
cd telbot

sudo install -d /opt/zero-lost
sudo install -m 644 bot.py requirements.txt /opt/zero-lost/
sudo python3 -m venv /opt/zero-lost/.venv
sudo /opt/zero-lost/.venv/bin/pip install -r /opt/zero-lost/requirements.txt
```

مخزن خصوصی است؛ برای `git clone` از حسابی استفاده کن که به آن دسترسی دارد.

## تنظیم توکن و کانال

```bash
sudo touch /etc/zero-lost.env
sudo chmod 600 /etc/zero-lost.env
sudoedit /etc/zero-lost.env
```

این دو خط را داخل فایل بگذار و `YOUR_NEW_TOKEN` را با توکن جدید BotFather جایگزین کن. توکن واقعی را حتی در مخزن خصوصی هم ذخیره نکن.

```ini
TELEGRAM_BOT_TOKEN=YOUR_NEW_TOKEN
ZERO_LOST_CHANNEL_ID=@ZiroLost
```

## اجرای دائمی

از داخل پوشهٔ `telbot` اجرا کن. با شروع سرویس، اولین دور جمع‌آوری و ارسال بلافاصله آغاز می‌شود.

```bash
sudo install -m 644 zero-lost.service /etc/systemd/system/zero-lost.service
sudo systemctl daemon-reload
sudo systemctl enable --now zero-lost
```

**مشاهدهٔ لاگ زنده:** `sudo journalctl -u zero-lost -f`  
**بعد از تغییر توکن یا تنظیمات:** `sudo systemctl restart zero-lost`  
**توقف و غیرفعال‌کردن اجرای خودکار:** `sudo systemctl disable --now zero-lost`
