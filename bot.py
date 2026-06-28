import asyncio
import aiohttp
import re
import os
import sqlite3
from datetime import datetime
from routeros_api import RouterOsApiPool

SYSLOG = "/var/log/syslog"

router_identity = "MIKROTIK"
online_users = set()
all_users = set()
profiles = {}

login_pattern = re.compile(r'([^\s]+)\slogged\sin,\s(\d+\.\d+\.\d+\.\d+)')
logout_pattern = re.compile(r'([^\s]+)\slogged\sout')

def get_config():
    """Mengambil konfigurasi terbaru dari database."""
    try:
        conn = sqlite3.connect('instance/database.db')
        c = conn.cursor()
        c.execute("SELECT bot_token, chat_id, router_ip, router_port, router_user, router_pass FROM config WHERE id=1")
        row = c.fetchone()
        conn.close()
        if row and all(row):
            return {"BOT_TOKEN": row[0], "CHAT_ID": row[1], "ROUTER_IP": row[2], 
                    "ROUTER_PORT": int(row[3]), "ROUTER_USER": row[4], "ROUTER_PASS": row[5]}
    except Exception:
        pass
    return None

def mikrotik_api(cfg):
    return RouterOsApiPool(
        cfg['ROUTER_IP'],
        username=cfg['ROUTER_USER'],
        password=cfg['ROUTER_PASS'],
        port=cfg['ROUTER_PORT'],
        plaintext_login=True
    )

async def telegram_worker(queue):
    async with aiohttp.ClientSession() as session:
        while True:
            message = await queue.get()
            cfg = get_config()
            if not cfg:
                continue
            
            url = f"https://api.telegram.org/bot{cfg['BOT_TOKEN']}/sendMessage"
            try:
                await session.post(url, data={"chat_id": cfg['CHAT_ID'], "text": message}, timeout=10)
            except Exception as e:
                print(f"❌ Telegram Error: {e}")
            await asyncio.sleep(0.05)

async def sync_users():
    global online_users, all_users, profiles, router_identity
    cfg = get_config()
    if not cfg:
        print("⚠️ Konfigurasi belum diatur di Dashboard.")
        return

    print("⏳ Sinkronisasi data dari MikroTik...")
    try:
        router = mikrotik_api(cfg)
        api = router.get_api()

        for i in api.get_resource('/system/identity').get():
            router_identity = i['name']

        for s in api.get_resource('/ppp/secret').get():
            if 'name' in s:
                all_users.add(s['name'])
                profiles[s['name']] = s.get('profile', '-')

        for a in api.get_resource('/ppp/active').get():
            if 'name' in a:
                online_users.add(a['name'])
                
        print(f"✅ Sinkronisasi selesai: {len(all_users)} Secrets, {len(online_users)} Active.")
        router.disconnect()
    except Exception as e:
        print(f"❌ Gagal sinkronisasi MikroTik: {e}")

async def process(line, queue):
    global online_users
    login = login_pattern.search(line)
    logout = logout_pattern.search(line)

    if login:
        user, ip = login.group(1), login.group(2)
        online_users.add(user)
        offline = sorted(list(all_users - online_users))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pesan = (f"✅ LOGIN {router_identity}\nTime: {now}\n=======================\n"
                 f"User: {user}\nIP Client: {ip}\nProfile: {profiles.get(user, '-')}\n"
                 f"Total Secrets: {len(all_users)}\nTotal Active: {len(online_users)}\n"
                 f"Disconnected Users ({len(offline)}): {', '.join(offline) if offline else '-'}")
        await queue.put(pesan)

    elif logout:
        user = logout.group(1)
        online_users.discard(user)
        offline = sorted(list(all_users - online_users))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pesan = (f"❌ LOGOUT {router_identity}\nTime: {now}\n=======================\n"
                 f"User: {user}\nProfile: {profiles.get(user, '-')}\n"
                 f"Total Secrets: {len(all_users)}\nTotal Active: {len(online_users)}\n"
                 f"Disconnected Users ({len(offline)}): {', '.join(offline) if offline else '-'}")
        await queue.put(pesan)

async def follow(queue):
    while not os.path.exists(SYSLOG):
        print(f"⚠️ Menunggu file {SYSLOG}...")
        await asyncio.sleep(5)

    print(f"🚀 Memantau log PPPoE dari {SYSLOG}...")
    with open(SYSLOG, "r", encoding="utf-8", errors="ignore") as file:
        file.seek(0, 2)
        while True:
            line = file.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            low = line.lower()
            if "logged in" in low or "logged out" in low:
                if not any(err in low for err in ["failed", "failure", "invalid", "error", "authentication"]):
                    asyncio.create_task(process(line, queue))

async def main():
    queue = asyncio.Queue()
    await sync_users()
    asyncio.create_task(telegram_worker(queue))
    await follow(queue)

def run_bot():
    """Fungsi pembungkus untuk menjalankan asyncio loop dari thread lain."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Bot Error: {e}")
