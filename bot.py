import asyncio
import aiohttp
import re
import os
import sqlite3
from datetime import datetime
from routeros_api import RouterOsApiPool

online_users = set()
all_users = set()
profiles = {}

login_pattern = re.compile(r'([^\s]+)\slogged\sin,\s(\d+\.\d+\.\d+\.\d+)')
logout_pattern = re.compile(r'([^\s]+)\slogged\sout')

def get_config():
    try:
        conn = sqlite3.connect('instance/database.db')
        c = conn.cursor()
        c.execute("SELECT bot_token, chat_id, router_ip, router_port, router_user, router_pass, router_identity FROM config WHERE id=1")
        row = c.fetchone()
        conn.close()
        
        if row and row[0] and row[1]:
            return {
                "BOT_TOKEN": row[0], 
                "CHAT_ID": row[1], 
                "ROUTER_IP": row[2], 
                "ROUTER_PORT": int(row[3]), 
                "ROUTER_USER": row[4], 
                "ROUTER_PASS": row[5] or "",
                "ROUTER_IDENTITY": row[6] or "MIKROTIK"
            }
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
    global online_users, all_users, profiles
    cfg = get_config()
    if not cfg:
        print("⚠️ Konfigurasi belum diatur di Web Dashboard.")
        return

    print("⏳ Sinkronisasi data dari MikroTik...")
    try:
        router = mikrotik_api(cfg)
        api = router.get_api()

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
    
    cfg = get_config()
    identity = cfg['ROUTER_IDENTITY'] if cfg else "MIKROTIK"

    if login:
        user = login.group(1)
        ip = login.group(2)
        online_users.add(user)
        offline = sorted(list(all_users - online_users))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pesan = (f"✅ LOGIN {identity}\nTime: {now}\n=======================\n"
                 f"User: {user}\nIP Client: {ip}\nProfile: {profiles.get(user, '-')}\n"
                 f"Total Secrets: {len(all_users)}\nTotal Active: {len(online_users)}\n"
                 f"Disconnected Users ({len(offline)}): {', '.join(offline) if offline else '-'}")
        await queue.put(pesan)

    elif logout:
        user = logout.group(1)
        online_users.discard(user)
        offline = sorted(list(all_users - online_users))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pesan = (f"❌ LOGOUT {identity}\nTime: {now}\n=======================\n"
                 f"User: {user}\nProfile: {profiles.get(user, '-')}\n"
                 f"Total Secrets: {len(all_users)}\nTotal Active: {len(online_users)}\n"
                 f"Disconnected Users ({len(offline)}): {', '.join(offline) if offline else '-'}")
        await queue.put(pesan)

class SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self, queue):
        self.queue = queue

    def datagram_received(self, data, addr):
        line = data.decode('utf-8', errors='ignore')
        low = line.lower()
        if "logged in" in low or "logged out" in low:
            if not any(err in low for err in ["failed", "failure", "invalid", "error", "authentication"]):
                asyncio.create_task(process(line, self.queue))

async def syslog_server(queue):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SyslogProtocol(queue),
        local_addr=('0.0.0.0', 514)
    )
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        transport.close()

async def auto_restart_timer():
    await asyncio.sleep(3600)
    os._exit(0)

async def main():
    queue = asyncio.Queue()
    await sync_users()
    asyncio.create_task(telegram_worker(queue))
    asyncio.create_task(auto_restart_timer())
    await syslog_server(queue)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Bot Error: {e}")
