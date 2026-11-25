# -*- coding: utf-8 -*-
import re, time, json, base64, socket, logging, random, os, urllib.parse, html
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from pathlib import Path
import requests, telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BRAND = "Zero Lost | زیرولاست"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("STATE_DIRECTORY") or BASE_DIR / "data")
SEEN_FILE = DATA_DIR / "seen.json"

def channel_settings():
    target = os.environ.get("ZERO_LOST_CHANNEL_ID", "@ZiroLost").strip()
    url = "https://t.me/ZiroLost"
    if re.fullmatch(r"-100[0-9]+", target):
        target = int(target)
    elif not re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{3,31}", target):
        raise SystemExit("Set ZERO_LOST_CHANNEL_ID to your channel @username or numeric -100... ID.")
    footer = (
        "زمان درج‌شده فقط زمان اتصال TCP از سرور ربات است؛ کارکرد سرویس تضمین نیست.\n\n"
        f'<a href="{url}">📢 کانال اصلی زیرولاست</a>\n'
        '<a href="https://t.me/ZiroLost_Vip">🔔 اطلاع‌رسانی VIP</a>\n'
        '<a href="https://t.me/zerolostbot">🤖 ربات زیرولاست</a>'
    )
    return {"id": target, "url": url, "header": f"🚀 <b>{BRAND}</b> | کانفیگ و پروکسی\n\n", "footer": footer}


RECYCLE_HOURS = 4
CONNECT_TIMEOUT = 5
MAX_MESSAGE_LENGTH = 4000
POST_INTERVAL_SECONDS = 600
TARGET_CONFIGS = 8
TARGET_PROXIES = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("zero-lost")

# ------------------- 2. منابع تلگرام (کانفیگ) -------------------
TG_SOURCES = [
    "SOSkeyNET", "ConfigsHUB", "FarahVPN", "Farah_VPN", "ConfigsHUB2",
    "ConfigX2ray", "v2ray1_ng", "AarazV2ray", "V2rayBaaz", "V2rayEnglish",
    "prrofile_purple", "SimChin_ir", "IRAN_V2RAY1", "Leviko_V2ray",
    "Outline_Vpn", "v2nodes", "SPARTAN_YT", "BigSmoke_Config", "FarazV2ray",
    "v2ray_outlineir", "PrivateVPNs", "V2rayNG_Fast", "FreeV2rays", "DailyV2RY"
]

# ------------------- 3. منابع تلگرام (پروکسی) -------------------
PROXY_TG_SOURCES = [
    "Farah_Proxy", "FarahProxy", "ProxyMTProto", "Proxy_Qavi",
    "iMTProxy_ir", "ShahinProxi", "iMTProto", "ProxyMTProto_tel",
    "i8proxy", "TelMTProto", "darkproxy", "iRoProxy",
    "MTProxyStar", "letsproxys1", "ProxGp", "Myporoxy", "ProxyDaemi"
]

# ------------------- 4. منابع گیت‌هاب و وب (پروکسی) -------------------
PROXY_GH_SOURCES = [
    "https://raw.githubusercontent.com/0xRadikal/Free-Telegram-Proxy/main/top100.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-Telegram-Proxy/main/faketls/all.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-Telegram-Proxy/main/resilient/all.txt",
    "https://raw.githubusercontent.com/zakky8/mtproto-proxy-pro/main/censorship_resistant.txt",
    "https://raw.githubusercontent.com/zakky8/mtproto-proxy-pro/main/all_proxies.txt",
    "https://tgmtproxy.github.io/mtproxy/proxies.txt",
    "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt",
    "https://raw.githubusercontent.com/Grim1313/mtproto-for-telegram/master/all_proxies.txt",
    "https://raw.githubusercontent.com/dubblebyte/free-mtproto-proxies/main/all_proxies.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/MTProtoProxy/main/mtproto.txt",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-proxies-collector/main/proxies.txt",
    "https://raw.githubusercontent.com/MuLTi-Co/MTProto-Proxy/main/proxies.txt",
    "https://raw.githubusercontent.com/B3H1Z/MTProto-Proxy/main/proxies.txt",
    "https://raw.githubusercontent.com/yebekhe/MTProtoCollector/main/proxy/mtproto.txt"
]

# ------------------- 5. منابع گیت‌هاب و ساب (کانفیگ) -------------------
GITHUB_SOURCES = [
    "https://raw.githubusercontent.com/noahclanman/free-xray-gcp/main/output/top100.txt",
    "https://raw.githubusercontent.com/noahclanman/free-xray-gcp/main/output/fast/configs.txt",
    "https://raw.githubusercontent.com/noahclanman/free-xray-gcp/main/output/transports/ws_tls.txt",
    "https://raw.githubusercontent.com/mohammadaz2/v2rayConfigsForYou/main/configs.txt",
    "https://raw.githubusercontent.com/mohammadaz2/v2rayConfigsForYou/main/sub/vless.txt",
    "https://raw.githubusercontent.com/MohammadBahemmat/V2ray-Collector/main/all_servers.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub2.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://matinghanbari.github.io/v2ray-configs/index.html",
    "https://v2freehub-sub.v2freehub.workers.dev/",
    "https://sub.vlessfo.ru/vlessforu/working_configs.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/verified/configs_base64.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/all/configs.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/all_configs.txt",
    "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/main/all_configs.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Subscribes/sub1.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Subscribes/sub2.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Subscribes/sub3.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Subscribes/sub4.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Subscribes/sub5.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/vless.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/vmess.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/shadowsocks.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/trojan.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt",
    "https://raw.githubusercontent.com/coldwater-10/V2ray-Config-Lite/main/Sub1.txt",
    "https://raw.githubusercontent.com/coldwater-10/V2ray-Config-Lite/main/Sub2.txt",
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/main/configs/ir/all.txt",
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/main/configs/ir/light.txt",
    "https://raw.githubusercontent.com/FNET00bot/FNET00/Config/Main",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/all_extracted_configs.txt",
    "https://raw.githubusercontent.com/expressalaki/ExpressVPN/refs/heads/main/configs2.txt",
    "https://raw.githubusercontent.com/expressalaki/ExpressVPN/refs/heads/main/configs.txt",
    "https://raw.githubusercontent.com/v2FreeHub/v2hub-configs/refs/heads/main/Sub-AutoUpdate",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/all_configs.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/mix_sub.txt",
    "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/vless_iran.txt",
    "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/mixed_iran.txt",
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/vless",
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/reality",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/reality",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/trojan",
    "https://raw.githubusercontent.com/Kwinwoo/config-v2ray/main/vless.txt",
    "https://raw.githubusercontent.com/Kwinwoo/config-v2ray/main/reality.txt",
    "https://raw.githubusercontent.com/amirhosein-v2ray/Free-V2ray-Config/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Firmfox/proxify/main/v2ray_configs/subscriptions/subscription-1.txt",
    "https://raw.githubusercontent.com/Firmfox/proxify/main/v2ray_configs/subscriptions/subscription-2.txt",
    "https://raw.githubusercontent.com/Firmfox/proxify/main/v2ray_configs/subscriptions/subscription-3.txt",
    "https://raw.githubusercontent.com/Firmfox/proxify/main/v2ray_configs/subscriptions/subscription-4.txt",
    "https://raw.githubusercontent.com/Firmfox/proxify/main/v2ray_configs/subscriptions/subscription-5.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/3.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/4.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/5.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/7.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/8.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/9.txt",
    "https://raw.githubusercontent.com/pog7x/vpn-configs/refs/heads/master/githubmirror/10.txt"
]

URI_RE = re.compile(r"(?:vless|vmess|ss|trojan|socks5|socks)://[^\s<>\"']+")
PROXY_RE = re.compile(r"(?:https?://t\.me/proxy\?|tg://proxy\?)[^\s<>\"']+")
NUM_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
PERSIAN_NUMS = ["۱", "۲", "۳"]

def load_seen():
    try:
        with SEEN_FILE.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    cutoff = time.time() - RECYCLE_HOURS * 3600
    return {key: stamp for key, stamp in data.items() if isinstance(stamp, (float, int)) and stamp > cutoff}

def save_seen(seen):
    temp_file = SEEN_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as handle:
        json.dump(seen, handle)
    temp_file.replace(SEEN_FILE)


def config_key(uri):
    core = uri.split("#", 1)[0]
    return core.strip().rstrip("/")

def extract(text):
    if not text: return []
    text = html.unescape(text)
    res = URI_RE.findall(text)
    if not res:
        try:
            pad = text.strip() + "=" * (-len(text.strip()) % 4)
            decoded = base64.b64decode(pad.encode()).decode("utf-8", errors="ignore")
            decoded = html.unescape(decoded)
            res = URI_RE.findall(decoded)
        except Exception: pass
    return res

def extract_proxies(text):
    if not text: return []
    text = html.unescape(text)
    raw_proxies = PROXY_RE.findall(text)
    clean_proxies = []
    for p in raw_proxies:
        p = p.replace("tg://proxy?", "https://t.me/proxy?")
        if "server=" in p and "port=" in p and "secret=" in p:
            clean_proxies.append(p)
    return clean_proxies

def fetch_github(url):
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200: return extract(r.text)
    except: pass
    return []

def fetch_github_proxies(url):
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200: return extract_proxies(r.text)
    except: pass
    return []

def fetch_telegram(ch):
    try:
        r = requests.get(f"https://t.me/s/{ch}", timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        return extract(r.text)
    except: return []

def fetch_telegram_proxies(ch):
    try:
        r = requests.get(f"https://t.me/s/{ch}", timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        return extract_proxies(r.text)
    except: return []

def parse_host_port(uri):
    try:
        scheme, rest = uri.split("://", 1)
        if scheme == "vmess":
            pad = rest.split("#", 1)[0]
            pad += "=" * (-len(pad) % 4)
            j = json.loads(base64.urlsafe_b64decode(pad.encode()).decode("utf-8", errors="ignore"))
            return j.get("add"), int(j.get("port", 0))
        parsed = urllib.parse.urlsplit(uri.split("#", 1)[0])
        if scheme == "ss" and not parsed.port and "@" not in parsed.netloc:
            value = parsed.netloc
            decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
            parsed = urllib.parse.urlsplit("ss://" + decoded)
        return parsed.hostname, parsed.port or 443

    except: return None, None

def parse_proxy_host_port(proxy_url):
    try:
        parsed = urllib.parse.urlparse(proxy_url)
        qs = urllib.parse.parse_qs(parsed.query)
        server = qs.get("server", [None])[0]
        port = int(qs.get("port", [0])[0])
        return server, port
    except: return None, None

def tcp_check(host, port):
    if not isinstance(host, str) or not host or not port or not 1 <= port <= 65535 or "%" in host:
        return False, 0
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        for family, kind, proto, _, endpoint in addresses:
            address = ipaddress.ip_address(endpoint[0])
            if not address.is_global or address.is_multicast:
                continue
            if address.version == 6 and (address not in ipaddress.ip_network("2000::/3") or address.sixtofour or address.teredo):
                continue
            try:
                with socket.socket(family, kind, proto) as conn:
                    conn.settimeout(CONNECT_TIMEOUT)
                    started = time.monotonic()
                    conn.connect(endpoint)
                    return True, round((time.monotonic() - started) * 1000)
            except OSError:
                continue
    except (OSError, ValueError, UnicodeError):
        pass
    return False, 0

def is_alive_and_ping(uri):
    host, port = parse_host_port(uri)
    return (*tcp_check(host, port), host)

def is_proxy_alive(proxy_url):
    return (*tcp_check(*parse_proxy_host_port(proxy_url)), proxy_url)


def rename_config_uri(uri, flag, channel_id):
    NEW_NAME = f"{flag} {channel_id} | کانفیگ روزانه"
    try:
        scheme, rest = uri.split("://", 1)
        if scheme == "vmess":
            pad = rest.split("#", 1)[0]
            pad += "=" * (-len(pad) % 4)
            j = json.loads(base64.urlsafe_b64decode(pad.encode()).decode("utf-8", errors="ignore"))
            j["ps"] = NEW_NAME
            encoded = base64.urlsafe_b64encode(json.dumps(j, ensure_ascii=False).encode("utf-8")).decode("utf-8").rstrip("=")
            return f"vmess://{encoded}"
        else:
            if "#" in rest: rest = rest.split("#", 1)[0]
            frag = urllib.parse.quote(NEW_NAME, safe="")
            return f"{scheme}://{rest}#{frag}"
    except Exception:
        return uri

def build_pack_post(valid_items, ch_info):
    header = ch_info["header"]
    footer = ch_info["footer"]
    ch_id = BRAND
    body = ""
    used_keys = []
    
    for idx, (c_key, flag, country, ping_ms, raw_uri) in enumerate(valid_items):
        renamed_uri = rename_config_uri(raw_uri, flag, ch_id)
        num_emoji = NUM_EMOJIS[idx] if idx < len(NUM_EMOJIS) else f"{idx+1}."
        block = f"{num_emoji} 🌐 {flag} ({country}) | TCP: {ping_ms}ms\n"
        block += f"<pre>{html.escape(renamed_uri)}</pre>\n\n"
        
        if len(header) + len(body) + len(block) + len(footer) <= MAX_MESSAGE_LENGTH:
            body += block
            used_keys.append(c_key)
        else:
            continue
            
    if not used_keys:
        return None, []
        
    return header + body + footer, used_keys

def build_keyboard(proxies_list, channel_url):
    markup = InlineKeyboardMarkup()
    p_buttons = []
    for i, (p_url, p_ping) in enumerate(proxies_list[:3]):
        label = PERSIAN_NUMS[i] if i < len(PERSIAN_NUMS) else str(i+1)
        p_buttons.append(InlineKeyboardButton(text=f"⚡ پروکسی {label} ({p_ping}ms)", url=p_url))
        
    if channel_url:
        p_buttons.append(InlineKeyboardButton(text="📢 کانال زیرولاست", url=channel_url))
    for offset in range(0, len(p_buttons), 2):
        markup.row(*p_buttons[offset:offset+2])
    return markup if p_buttons else None


def collect_telegram():
    pool = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(fetch_telegram, TG_SOURCES):
            if res: pool += res
    return list(dict.fromkeys(pool))

def collect_github():
    pool = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        for res in ex.map(fetch_github, GITHUB_SOURCES):
            if res: pool += res
    return list(dict.fromkeys(pool))

def collect_valid_proxies(seen, now, max_needed=TARGET_PROXIES):
    pool = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(fetch_telegram_proxies, PROXY_TG_SOURCES):
            if res: pool += res
        for res in ex.map(fetch_github_proxies, PROXY_GH_SOURCES):
            if res: pool += res
    pool = list(dict.fromkeys(pool))
    random.shuffle(pool)
    
    fresh_cands = [p for p in pool if now - seen.get(p, 0) > RECYCLE_HOURS * 3600]
    old_cands = [p for p in pool if now - seen.get(p, 0) <= RECYCLE_HOURS * 3600]
    
    valid_proxies = []
    for cands in [fresh_cands, old_cands]:
        if len(valid_proxies) >= max_needed: break
        if not cands: continue
        
        with ThreadPoolExecutor(max_workers=30) as ex:
            for i in range(0, len(cands), 30):
                batch = cands[i:i+30]
                results = list(ex.map(is_proxy_alive, batch))
                for ok, ping_ms, p_url in results:
                    if ok:
                        valid_proxies.append((p_url, ping_ms))
                        if len(valid_proxies) >= max_needed: break
                if len(valid_proxies) >= max_needed: break
                
    return valid_proxies

def process_candidates(candidates, valid_items, max_needed):
    seen_in_batch = {item[0] for item in valid_items}
    with ThreadPoolExecutor(max_workers=50) as ex:
        for i in range(0, len(candidates), 30):
            batch = candidates[i:i+30]
            results = list(ex.map(is_alive_and_ping, batch))
            
            for cfg, (ok, ping_ms, host) in zip(batch, results):
                if ok:
                    c_key = config_key(cfg)
                    if c_key in seen_in_batch:
                        continue
                    country, flag = "اتصال TCP", "🌐"
                    test_uri = rename_config_uri(cfg, flag, BRAND)
                    if len(test_uri) <= 700:
                        valid_items.append((c_key, flag, country, ping_ms, cfg))
                        seen_in_batch.add(c_key)
                    
                    if len(valid_items) >= max_needed: break
            if len(valid_items) >= max_needed: break
    return valid_items

def prepare_post(seen, channel):
    now = time.time()
    valid_items = []

    # --- مرحله اول: جستجوی کانفیگ در تلگرام ---
    log.info("Collecting configs from Telegram...")
    tg_cfgs = collect_telegram()
    random.shuffle(tg_cfgs)
    tg_candidates = [c for c in tg_cfgs if now - seen.get(config_key(c), 0) > RECYCLE_HOURS * 3600]

    valid_items = process_candidates(tg_candidates, valid_items, TARGET_CONFIGS)

    # --- مرحله دوم: تکمیل ظرفیت کانفیگ از گیت‌هاب و لینک‌های ساب ---
    if len(valid_items) < TARGET_CONFIGS:
        needed = TARGET_CONFIGS - len(valid_items)
        log.info(f"Need {needed} more configs. Fetching from GitHub...")
        gh_cfgs = collect_github()
        random.shuffle(gh_cfgs)
        gh_candidates = [c for c in gh_cfgs if now - seen.get(config_key(c), 0) > RECYCLE_HOURS * 3600]

        valid_items = process_candidates(gh_candidates, valid_items, TARGET_CONFIGS)
    post_text, used_keys = build_pack_post(valid_items, channel)
    if not used_keys:
        return None
    proxies = collect_valid_proxies(seen, now, TARGET_PROXIES)
    return post_text, build_keyboard(proxies, channel["url"]), [*used_keys, *(url for url, _ in proxies)]


def run_publisher(bot, channel):
    next_slot = time.monotonic()
    while True:
        try:
            seen = load_seen()
            last_sent = max(seen.values(), default=0)
            remaining = min(POST_INTERVAL_SECONDS, max(0, last_sent + POST_INTERVAL_SECONDS - time.time()))
            next_slot = max(next_slot, time.monotonic() + remaining)
            post = prepare_post(seen, channel)
            time.sleep(max(0, next_slot - time.monotonic()))
            if post:
                text, keyboard, keys = post
                bot.send_message(channel["id"], text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)
                sent_at = time.time()
                seen.update(dict.fromkeys(keys, sent_at))
                save_seen(seen)
                log.info("Sent one post to %s", channel["id"])
            else:
                log.info("No eligible configs; skipping this slot")
        except Exception as error:
            log.error("Round failed (%s)", type(error).__name__)
            time.sleep(max(0, next_slot - time.monotonic()))
        next_slot = time.monotonic() + POST_INTERVAL_SECONDS


if __name__ == "__main__":
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN before starting Zero Lost.")
    bot = telebot.TeleBot(token, threaded=False)
    channel = channel_settings()
    DATA_DIR.mkdir(mode=0o700, exist_ok=True)
    log.info("Zero Lost started")
    run_publisher(bot, channel)
