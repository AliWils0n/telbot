import copy
import html
import io
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telebot.types import ReplyKeyboardMarkup

OWNER = 1358769287
TEHRAN = ZoneInfo("Asia/Tehran")
HOME = "🏠 منوی اصلی"
INTERVAL = "⏱ فاصله انتشار"
TARGETS = "📣 کانال‌های مقصد"
SOURCES = "📥 منابع کانفیگ"
TEMPLATE = "✏️ متن و لینک‌ها"
SCHEDULE = "🗓 پیام جدید"
JOBS = "📋 برنامه‌ها"
ADD, REMOVE = "➕ افزودن", "➖ حذف"
NOW, LATER, DAILY = "یک بار، همین حالا", "یک بار، با تأخیر", "هر روز"
CONFIRM = "✅ ثبت برنامه"
CLEAR = "🗑 پاک کردن این بخش"
FIELDS = {"تیتر": "title", "توضیح زیر پست": "note", "لینک کانال اصلی": "main", "لینک اطلاع‌رسانی": "vip", "لینک ربات": "bot"}
DEFAULTS = {"title": "Zero Lost | زیرولاست | کانفیگ و پروکسی", "note": "زمان درج‌شده فقط زمان اتصال TCP از سرور ربات است؛ کارکرد سرویس تضمین نیست.", "main": "https://t.me/ZiroLost", "vip": "https://t.me/ZiroLost_Vip", "bot": "https://t.me/zerolostbot"}
log = logging.getLogger("zero-lost")


class Store:
    def __init__(self, path, target, sources):
        self.path = path
        self.lock = threading.RLock()
        self.data = {"minutes": 10, "targets": [str(target)], "sources": list(sources), "fields": dict(DEFAULTS), "jobs": {}, "next_id": 1}
        if path.exists():
            self.data.update(json.loads(path.read_text(encoding="utf-8")))

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.data)

    def change(self, action):
        with self.lock:
            new = copy.deepcopy(self.data)
            result = action(new)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
            os.replace(temp, self.path)
            self.data = new
            return result


def template(fields):
    footer = [html.escape(fields["note"])] if fields["note"] else []
    for key, label in [("main", "📢 کانال اصلی زیرولاست"), ("vip", "🔔 اطلاع‌رسانی VIP"), ("bot", "🤖 ربات زیرولاست")]:
        if fields[key]:
            footer.append(f'<a href="{html.escape(fields[key], quote=True)}">{label}</a>')
    title = html.escape(fields["title"])
    return {"url": fields["main"], "header": f"<b>{title}</b>\n\n" if title else "", "footer": "\n".join(footer)}


def next_daily(clock, now):
    local = datetime.fromtimestamp(now, TEHRAN)
    hour, minute = map(int, clock.split(":"))
    due = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return (due if due > local else due + timedelta(days=1)).timestamp()


def display_time(stamp):
    return datetime.fromtimestamp(stamp, TEHRAN).strftime("%Y-%m-%d %H:%M")


def channel_id(target):
    return int(target) if target.startswith("-") else target


def tick(store, publisher, control):
    for key, job in store.snapshot()["jobs"].items():
        now = time.time()
        if job["due"] > now or job.get("status", "ready") != "ready":
            continue
        def claim(data):
            current = data["jobs"].get(key)
            if current != job or job["target"] not in data["targets"]:
                return False
            current["status"] = "sending"
            return True
        if not store.change(claim):
            continue
        try:
            target = channel_id(job["target"])
            photo = job.get("photo")
            if not photo:
                publisher.send_message(target, job["body"], disable_web_page_preview=True)
            elif control.token == publisher.token:
                publisher.send_photo(target, photo, caption=job["body"] or None)
            else:
                remote = control.get_file(photo)
                with io.BytesIO(control.download_file(remote.file_path)) as upload:
                    upload.name = "photo.jpg"
                    publisher.send_photo(target, upload, caption=job["body"] or None)
        except Exception as error:
            log.warning("Scheduled post %s failed (%s)", key, type(error).__name__)
            def failed(data):
                if key in data["jobs"]:
                    data["jobs"][key]["status"] = "failed"
            store.change(failed)
            try:
                control.send_message(OWNER, f"ارسال برنامه #{key} تأیید نشد؛ کانال و دسترسی ربات را بررسی کن. برنامه متوقف شد.")
            except Exception:
                log.warning("Could not notify owner")
        else:
            def finish(data):
                current = data["jobs"].get(key)
                if not current:
                    return
                if job["clock"]:
                    current.update(due=next_daily(job["clock"], time.time()), status="ready")
                else:
                    del data["jobs"][key]
            store.change(finish)


def schedule_loop(store, publisher, control):
    while True:
        try:
            tick(store, publisher, control)
        except Exception as error:
            log.error("Scheduler error (%s)", type(error).__name__)
        time.sleep(2)


def attach(control, store):
    state = {}

    def show(text, buttons=(), home=True):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        if buttons:
            markup.add(*buttons)
        if home:
            markup.row(HOME)
        control.send_message(OWNER, text, reply_markup=markup, disable_web_page_preview=True)

    def menu(text="پنل مدیریت زیرولاست"):
        state.clear()
        show(text, [INTERVAL, TARGETS, SOURCES, TEMPLATE, SCHEDULE, JOBS], False)

    def prompt(step, text, buttons=()):
        state["step"] = step
        show(text, buttons)

    def handle(message):
        text = (message.text or "").strip()
        step = state.get("step")
        if message.content_type == "photo" and step != "body":
            return control.send_message(OWNER, "عکس را بعد از انتخاب «پیام جدید» و کانال مقصد بفرست.")
        data = store.snapshot()
        if text in (HOME, "/panel", "/start", "/cancel"):
            return menu()
        if not step:
            if text == INTERVAL:
                return prompt("minutes", f"فاصله فعلی: {data['minutes']} دقیقه. انتخاب کن یا عدد ۱ تا ۱۴۴۰ بفرست.", ["10", "15", "20", "30", "60"])
            if text in (TARGETS, SOURCES):
                field = "targets" if text == TARGETS else "sources"
                state["field"] = field
                return prompt("list", text + ":\n" + "\n".join(data[field]), [ADD, REMOVE])
            if text == TEMPLATE:
                return prompt("field", "بخش مورد نظر را انتخاب کن.", list(FIELDS))
            if text == SCHEDULE:
                return prompt("target", "پیام به کدام کانال برود؟", data["targets"])
            if text == JOBS:
                jobs = data["jobs"]
                if not jobs:
                    return menu("هیچ برنامه‌ای ثبت نشده.")
                lines = []
                for key, job in jobs.items():
                    status = {"ready": "فعال", "sending": "ارسال نامشخص", "failed": "ناموفق"}[job["status"]]
                    repeat = "روزانه" if job["clock"] else "یک‌بار"
                    label = "📷 " if job.get("photo") else ""
                    lines.append(f"#{key} · {job['target']} · {repeat} · {display_time(job['due'])} · {status}\n{label}{job['body'][:32]}")
                return prompt("delete_job", "\n".join(lines) + "\nبرای حذف، شمارهٔ برنامه را انتخاب کن.", list(jobs))
            return menu()
        if step == "minutes":
            if not text.isdecimal() or len(text) > 4 or not 1 <= int(text) <= 1440:
                raise ValueError("عدد بین ۱ و ۱۴۴۰ بفرست.")
            store.change(lambda settings: settings.update(minutes=int(text)))
            return menu(f"فاصلهٔ پست‌های کانفیگ: {int(text)} دقیقه.")
        if step == "list":
            if text not in (ADD, REMOVE):
                raise ValueError("افزودن یا حذف را انتخاب کن.")
            state["adding"] = text == ADD
            return prompt("entry", "نام کانال را بفرست. حذف مقصد، برنامه‌های همان مقصد را هم لغو می‌کند.", [] if text == ADD else data[state["field"]])
        if step == "entry":
            field = state["field"]
            value = text.removeprefix("https://t.me/").lstrip("@")
            numeric = bool(re.fullmatch(r"-100[0-9]+", value)) and field == "targets"
            if not numeric and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", value):
                raise ValueError("نام کاربری عمومی کانال یا شناسهٔ عددی مقصد را وارد کن.")
            if field == "targets" and not numeric:
                value = "@" + value
            existing = next((item for item in data[field] if item.lower() == value.lower()), None)
            if state["adding"]:
                if existing or len(data[field]) >= 60:
                    raise ValueError("تکراری است یا فهرست پر شده.")
                store.change(lambda settings: settings[field].append(value))
            else:
                if not existing or (field == "targets" and len(data[field]) == 1):
                    raise ValueError("مورد پیدا نشد یا آخرین مقصد است.")
                def remove(settings):
                    settings[field].remove(existing)
                    if field == "targets":
                        settings["jobs"] = {key: job for key, job in settings["jobs"].items() if job["target"] != existing}
                store.change(remove)
            return menu("فهرست ذخیره شد.")
        if step == "field":
            if text not in FIELDS:
                raise ValueError("یکی از بخش‌ها را انتخاب کن.")
            state["field"] = FIELDS[text]
            return prompt("value", "مقدار فعلی: " + (data["fields"][FIELDS[text]] or "خالی") + "\nمقدار جدید را بفرست یا این بخش را پاک کن.", [CLEAR])
        if step == "value":
            field = state["field"]
            value = "" if text == CLEAR else text
            if field in ("main", "vip", "bot") and value:
                if value.startswith("@"):
                    value = "https://t.me/" + value[1:]
                if not re.fullmatch(r"https://t\.me/(?:[A-Za-z][A-Za-z0-9_]{3,31}|\+[\w-]{4,100})", value):
                    raise ValueError("لینک https://t.me/... یا @username بفرست.")
            if len(html.escape(value)) > (150 if field == "title" else 700):
                raise ValueError("متن طولانی است؛ کوتاه‌تر بفرست.")
            store.change(lambda settings: settings["fields"].update({field: value}))
            return menu("قالب پست‌های بعدی ذخیره شد.")
        if step == "target":
            if text not in data["targets"]:
                raise ValueError("یکی از مقصدهای فهرست را انتخاب کن.")
            state["target"] = text
            return prompt("body", "متن یا یک عکس بفرست. اگر کپشن می‌خواهی، موقع ارسال عکس زیرش بنویس.")
        if step == "body":
            if message.content_type == "photo":
                if message.media_group_id:
                    raise ValueError("فقط یک عکس بفرست، نه آلبوم.")
                text = message.caption or ""
                if len(text) > 1024:
                    raise ValueError("کپشن طولانی است؛ عکس را با کپشن کوتاه‌تر بفرست.")
                state["photo"] = max(message.photo, key=lambda size: size.width * size.height).file_id
            elif not text or len(text.encode("utf-16-le")) // 2 > 4000:
                raise ValueError("متن باید بین ۱ تا ۴۰۰۰ کاراکتر باشد.")
            state["body"] = text
            return prompt("mode", "چه زمانی فرستاده شود؟", [NOW, LATER, DAILY])
        if step == "mode":
            if text not in (NOW, LATER, DAILY):
                raise ValueError("یکی از سه حالت را انتخاب کن.")
            state.update(mode=text, clock="", delay=0)
            if text == LATER:
                return prompt("delay", "چقدر دیگر؟ مثلاً «3 ساعت» یا «15 دقیقه».")
            if text == DAILY:
                return prompt("clock", "ساعت تهران را ۲۴ ساعته بنویس؛ مثلاً 21:30.")
        elif step == "delay":
            match = re.fullmatch(r"(\d{1,5})\s*(ساعت|دقیقه)", text)
            if not match or not int(match[1]):
                raise ValueError("مثال: ۲ ساعت یا ۳۰ دقیقه")
            state["delay"] = int(match[1]) * (3600 if match[2] == "ساعت" else 60)
        elif step == "clock":
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
            if not match or int(match[1]) > 23 or int(match[2]) > 59:
                raise ValueError("ساعت معتبر مثل 09:05 بفرست.")
            state["clock"] = f"{int(match[1]):02d}:{int(match[2]):02d}"
        elif step == "confirm":
            if text != CONFIRM:
                raise ValueError("برای ثبت، دکمهٔ تأیید را بزن یا به منو برگرد.")
            def add(settings):
                if len(settings["jobs"]) >= 30 or state["target"] not in settings["targets"]:
                    raise ValueError("فهرست برنامه‌ها پر است یا مقصد حذف شده.")
                key = str(settings["next_id"])
                settings["next_id"] += 1
                now = time.time()
                due = next_daily(state["clock"], now) if state["clock"] else now + state["delay"]
                settings["jobs"][key] = dict(target=state["target"], body=state["body"], due=due, clock=state["clock"], status="ready")
                if "photo" in state:
                    settings["jobs"][key]["photo"] = state["photo"]
                return key
            return menu("برنامه ثبت شد: #" + store.change(add))
        elif step == "delete_job":
            if text not in data["jobs"]:
                raise ValueError("شمارهٔ یک برنامهٔ موجود را انتخاب کن.")
            state["key"] = text
            return prompt("confirm_delete", f"برنامه #{text} لغو شود؟", ["بله، لغو کن"])
        elif step == "confirm_delete":
            if text != "بله، لغو کن":
                raise ValueError("لغو را تأیید کن یا به منو برگرد.")
            store.change(lambda settings: settings["jobs"].pop(state["key"], None))
            return menu("برنامه لغو شد.")
        when = state["clock"] or (f"{state['delay']//60} دقیقه بعد از تأیید" if state["delay"] else "بعد از تأیید")
        label = "📷 عکس\n" if "photo" in state else ""
        return prompt("confirm", f"مقصد: {state['target']}\n{state['mode']} · {when} (تهران)\n\n{label}{state['body'][:500]}\n\nثبت شود؟", [CONFIRM])

    @control.message_handler(func=lambda message: message.chat.type == "private" and message.from_user is not None and message.from_user.id == OWNER and message.chat.id == OWNER, content_types=["text", "photo"])
    def owner_message(message):
        try:
            handle(message)
        except ValueError as error:
            control.send_message(OWNER, str(error))
