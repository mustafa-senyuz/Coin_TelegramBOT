import os
import sqlite3
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor
from telegram import Bot
from datetime import datetime
import json
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
CONFIG = {
    'BOT_TOKEN': os.getenv('BOT_TOKEN'),
    'BOT_PAT': os.getenv('BOT_PAT'),
    'CHAT_IDS': [-1002281621284, 5637330580],
    'API_URLS': {
        'coingecko': 'https://api.coingecko.com/api/v3/coins/markets',
        'binance': 'https://api.binance.com/api/v3/ticker/24hr'
    },
    'ALERT_THRESHOLDS': {
        'volume_ratio': 20,
        'support_deviation': 2,
        'pump_threshold': 20,
        'inflow_threshold': 1,
        'volume_spike': 5
    },
    'SCAN_INTERVAL': 30,
    'ERROR_RETRY_DELAY': 60
}

# --- JSON ALERT UTILITY ---
def save_alert_to_json(symbol):
    path = 'alerts.json'
    data = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.load(f)
    if symbol not in data:
        data[symbol] = 'alert_sent'
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {symbol} saved to alerts.json")
    else:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {symbol} already in alerts.json")

# --- GIT PUSH UTILITY ---
def git_push():
    try:
        subprocess.run(['git', 'config', '--global', 'user.name', 'mustafa-senyuz'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'mustafasenyuz.git@gmail.com'], check=True)
        pat = CONFIG['BOT_PAT']
        if not pat:
            raise Exception('BOT_PAT not defined')
        repo = f"https://{pat}@github.com/mustafa-senyuz/Coin_TelegramBOT.git"
        subprocess.run(['git', 'remote', 'set-url', 'origin', repo], check=True)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Auto update from script'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Changes pushed to GitHub")
    except Exception as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Git error: {e}")

# --- DATABASE UTILITIES ---
def open_db(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def initialize_db(file_path):
    with open_db(file_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS coin_volumes (
                symbol TEXT PRIMARY KEY,
                previous_volume REAL
            )''')
        conn.commit()
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Initialized DB: {file_path}")

def get_previous_volume(db_path, symbol):
    if not os.path.exists(db_path):
        return 0
    try:
        with open_db(db_path) as conn:
            row = conn.execute(
                'SELECT previous_volume FROM coin_volumes WHERE symbol=?', (symbol,)
            ).fetchone()
            return row[0] if row else 0
    except sqlite3.Error as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] DB error ({db_path}): {e}")
        return 0

def save_current_volume(db_path, symbol, volume):
    with open_db(db_path) as conn:
        conn.execute(
            'INSERT OR REPLACE INTO coin_volumes(symbol, previous_volume) VALUES(?,?)',
            (symbol, volume)
        )
        conn.commit()

def rotate_db(old_path, new_path):
    try:
        if os.path.exists(old_path):
            sqlite3.connect(old_path).close()
            os.remove(old_path)
        if os.path.exists(new_path):
            os.rename(new_path, old_path)
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Rotated DB: {old_path}")
    except Exception as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Rotate error ({old_path}): {e}")

# Initialize all databases
def initialize_databases():
    initialize_db('db/coin_alertsOLD.db')
    initialize_db('db/coin_alerts1h_OLD.db')
    initialize_db('db/coin_alerts24h_OLD.db')

# Convenience wrappers
get_prev = lambda s: get_previous_volume('db/coin_alertsOLD.db', s)
save_curr = lambda s,v: save_current_volume('db/coin_alertsNEW.db', s, v)
rotate = lambda: rotate_db('db/coin_alertsOLD.db','db/coin_alertsNEW.db')
get_prev_1h = lambda s: get_previous_volume('db/coin_alerts1h_OLD.db', s)
save_curr_1h = lambda s,v: save_current_volume('db/coin_alerts1h_NEW.db', s, v)
rotate_1h = lambda: rotate_db('db/coin_alerts1h_OLD.db','db/coin_alerts1h_NEW.db')
get_prev_24h = lambda s: get_previous_volume('db/coin_alerts24h_OLD.db', s)
save_curr_24h = lambda s,v: save_current_volume('db/coin_alerts24h_NEW.db', s, v)
rotate_24h = lambda: rotate_db('db/coin_alerts24h_OLD.db','db/coin_alerts24h_NEW.db')

# --- MESSAGE UTILITIES ---
def format_volume(v):
    if v>=1e9: return f"{v/1e9:.1f}B"
    if v>=1e6: return f"{v/1e6:.1f}M"
    if v>=1e3: return f"{v/1e3:.1f}K"
    return f"{v:.2f}"

def escape_md(text):
    chars=set('_*[]()~`>#+-=|{}.!')
    return ''.join(f"\\{c}" if c in chars else c for c in str(text))

def create_alert_table(title, headers, data):
    t=escape_md(title)
    hdr=[escape_md(h) for h in headers]
    table=f"*{t}*\n```\n"+" | ".join(hdr)+"\n"+"-|-"*len(hdr)+"\n"
    for row in data:
        table+=" | ".join(escape_md(c) for c in row)+"\n"
    table+="```"
    return table

def split_long(msg, max_len=4096):
    parts,cur,length=[],[],0
    in_code=False
    for line in msg.split('\n'):
        if line.startswith('```'): in_code=not in_code
        if length+len(line)+1>max_len:
            if in_code: cur.append('```');in_code=False
            parts.append('\n'.join(cur));cur=[];length=0
            if line.startswith('```'): in_code=True
        cur.append(line);length+=len(line)+1
    if cur:
        if in_code: cur.append('```')
        parts.append('\n'.join(cur))
    return parts

# --- FETCH & ALERT LOGIC ---
async def fetch_coingecko_data():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Fetching CoinGecko data...")
    try:
        params={'vs_currency':'usd','order':'volume_desc','per_page':100}
        with ThreadPoolExecutor() as ex:
            resp=await asyncio.get_event_loop().run_in_executor(ex, requests.get, CONFIG['API_URLS']['coingecko'], params)
        coins=resp.json()
        volume_alerts,support_alerts=[],[]
        for c in coins:
            sym=c['symbol'].upper();vol=c.get('total_volume',0);mc=c.get('market_cap',0)
            if mc>0 and vol>0 and vol/mc*100>=CONFIG['ALERT_THRESHOLDS']['volume_ratio']:
                volume_alerts.append({'symbol':sym,'price':c['current_price'],'volume':vol,'ratio':vol/mc*100})
            low=c.get('low_24h',0);pr=c.get('current_price',0)
            if low>0 and pr<=low*(1+CONFIG['ALERT_THRESHOLDS']['support_deviation']/100):
                support_alerts.append({'symbol':sym,'price':pr,'low':low,'deviation':(pr-low)/low*100})
        return volume_alerts,support_alerts
    except Exception as e:
        print(f"CG error: {e}")
        return [],[]

async def fetch_binance_data():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Fetching Binance data...")
    try:
        with ThreadPoolExecutor() as ex:
            resp=await asyncio.get_event_loop().run_in_executor(ex, requests.get, CONFIG['API_URLS']['binance'])
        tickers=resp.json()
        pump,support,inflow,spike,inc1h,inc24h=[],[],[],[],[],[]
        vols={}
        for t in tickers:
            sym=t['symbol'].replace('USDT','');pr=float(t['lastPrice']);low=float(t['lowPrice']);vol=float(t['quoteVolume'])
            prev,prev1,prev24=get_prev(sym),get_prev_1h(sym),get_prev_24h(sym)
            vols[sym]=vol
            ch=float(t['priceChangePercent'])
            if ch>=CONFIG['ALERT_THRESHOLDS']['pump_threshold']: pump.append({'symbol':sym,'price':pr,'change':ch})
            if low>0 and pr<=low*(1+CONFIG['ALERT_THRESHOLDS']['support_deviation']/100): support.append({'symbol':sym,'price':pr,'low':low,'deviation':(pr-low)/low*100})
            if prev>0:
                diff=vol/prev-1
                if diff*100>=CONFIG['ALERT_THRESHOLDS']['inflow_threshold']: inflow.append({'symbol':sym,'price':pr,'volume':vol,'change':diff})
                if diff*100>=CONFIG['ALERT_THRESHOLDS']['volume_spike']: spike.append({'symbol':sym,'price':pr,'volume':vol,'change':diff})
            if prev1>0 and (vol/prev1-1)*100>=2: inc1h.append({'symbol':sym,'price':pr,'volume':vol,'change':(vol/prev1-1)*100})
            if prev24>0 and (vol/prev24-1)*100>=50: inc24h.append({'symbol':sym,'price':pr,'volume':vol,'change':(vol/prev24-1)*100})
        for s,v in vols.items(): save_curr(s,v)
        return pump,support,inflow,spike,inc1h,inc24h
    except Exception as e:
        print(f"BN error: {e}")
        return [],[],[],[],[],[]

async def send_telegram_message(bot,message):
    success=True
    for cid in CONFIG['CHAT_IDS']:
        for i in range(3):
            try:
                await bot.send_message(chat_id=cid,text=message,parse_mode='MarkdownV2',disable_web_page_preview=True)
                await asyncio.sleep(1)
                break
            except:
                success=False; await asyncio.sleep(2**i)
    return success

async def main_loop():
    initialize_databases()
    bot=Bot(token=CONFIG['BOT_TOKEN'])
    last1,last24=datetime.now(),datetime.now()
    while True:
        cg_v,cg_s=await fetch_coingecko_data()
        bn_p,bn_s,bn_i,bn_sp,bi1,bi24=await fetch_binance_data()
        parts=["🚨 *CRYPTO ALERT SYSTEM* 🚨\n"]
        if bi1: parts.append(create_alert_table("1h INCREASE",["Coin","P","V","Δ%"],[[i['symbol'],f"${i['price']:.2f}",format_volume(i['volume']),f"{i['change']:.1f}%"] for i in bi1]))
        else: parts.append("*1h INCREASE*\nNo coins found")
        if bi24: parts.append(create_alert_table("24h INCREASE",["Coin","P","V","Δ%"],[[i['symbol'],f"${i['price']:.2f}",format_volume(i['volume']),f"{i['change']:.1f}%"] for i in bi24]))
        else: parts.append("*24h INCREASE*\nNo coins found")
        parts.append(f"\n⏱ *Updated:* `{escape_md(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}`")
        full="\n".join(parts)
        for msg in split_long(full): await send_telegram_message(bot,msg)
        rotate();
        if (datetime.now()-last1).seconds>=3600: rotate_1h(); last1=datetime.now()
        if (datetime.now()-last24).seconds>=86400: rotate_24h(); last24=datetime.now()
        git_push()
        await asyncio.sleep(CONFIG['SCAN_INTERVAL'])

if __name__=='__main__':
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Bot shutting down...")
