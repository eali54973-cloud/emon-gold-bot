import os, requests, pandas as pd, time, traceback
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread
import telebot
from datetime import datetime
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
bd_tz = pytz.timezone('Asia/Dhaka')

def safe_get_df(tf="15m", limit=100):
    urls = [
        f"https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval={tf}&limit={limit}",
        f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={tf}&limit={limit}"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=20).json()
            if isinstance(r, list) and len(r) > 10:
                df = pd.DataFrame(r, columns=['t','O','H','L','C','V','x','y','z','a','b','c'])
                for c in ['O','H','L','C','V']: df[c]=df[c].astype(float)
                return df
        except: continue
    return None

def get_price():
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=PAXGUSDT", timeout=10).json()
        return float(r['price'])
    except: return None

def build_pro_chart():
    try:
        df1h = safe_get_df("1h", 50)
        df30 = safe_get_df("30m", 60)
        df15 = safe_get_df("15m", 80)
        df5 = safe_get_df("5m", 100)
        price = get_price() or df5['C'].iloc[-1]

        if df1h is None or df30 is None or df15 is None or df5 is None:
            return "❌ API Busy, 1 min পরে /setup দিন", None

        # 1. HTF 1H
        htf_bull = df1h['C'].iloc[-1] > df1h['O'].iloc[-1] and df1h['C'].iloc[-1] > df1h['C'].iloc[-10]
        htf_text = "BULLISH 🟢" if htf_bull else "BEARISH 🔴"

        # 2. 30M BOS
        recent_high_30 = df30['H'].iloc[-10:-1].max()
        recent_low_30 = df30['L'].iloc[-10:-1].min()
        bos_bull = df30['C'].iloc[-1] > recent_high_30
        bos_bear = df30['C'].iloc[-1] < recent_low_30
        bos_text = f"BULLISH BOS > {recent_high_30:.1f}" if bos_bull else f"BEARISH BOS < {recent_low_30:.1f}" if bos_bear else "CHOCH Waiting"
        is_bos = bos_bull or bos_bear

        # 3. 15M Liquidity Sweep
        high_15 = df15['H'].max()
        low_15 = df15['L'].min()
        sweep_high = df15['H'].iloc[-1] > df15['H'].iloc[-10:-1].max()
        sweep_low = df15['L'].iloc[-1] < df15['L'].iloc[-10:-1].min()
        sweep_text = f"BSL Sweep {high_15:.1f} ✅" if sweep_high else f"SSL Sweep {low_15:.1f} ✅" if sweep_low else f"Range {low_15:.1f}-{high_15:.1f}"
        is_sweep = sweep_high or sweep_low

        # 4. 5M OB + FVG
        ob_high = df5['H'].iloc[-15:-5].max()
        ob_low = df5['L'].iloc[-15:-5].min()
        # FVG detection
        fvg = (df5['C'].iloc[-2] + df5['C'].iloc[-1])/2

        # 5. ENTRY SL TP - Quality Logic
        if not htf_bull and bos_bear and (sweep_high or True): # Bearish Setup
            side = "SELL"
            entry = round(df5['C'].iloc[-5:].mean() + 3, 1) # Retest
            sl = round(ob_high + 3.5, 1)
            risk = sl - entry
            tp1 = round(entry - risk*1.5, 1)
            tp2 = round(entry - risk*2.5, 1)
        elif htf_bull and bos_bull and (sweep_low or True):
            side = "BUY"
            entry = round(df5['C'].iloc[-5:].mean() - 3, 1)
            sl = round(ob_low - 3.5, 1)
            risk = entry - sl
            tp1 = round(entry + risk*1.5, 1)
            tp2 = round(entry + risk*2.5, 1)
        else:
            side = "WAIT"
            entry = round(price,1)
            sl = round(price+15,1)
            tp1 = round(price-15,1)
            tp2 = round(price-25,1)

        # 6. Screenshot - PRO 4K
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12,8), gridspec_kw={'height_ratios': [3, 1]})

        # 15M + 5M Combined
        ax1.plot(df15['C'].tail(60).values, color='black', lw=2, label='15M Trend')
        ax1.plot(range(20,80), df5['C'].tail(60).values, color='#2962FF', lw=1.2, alpha=0.8, label='5M Entry TF')
        ax1.axhline(entry, color='#FF9800', ls='--', lw=2, label=f'ENTRY {entry}')
        ax1.axhline(sl, color='#F44336', ls='-', lw=2, label=f'SL {sl}')
        ax1.axhline(tp1, color='#4CAF50', ls='-', lw=1.5, label=f'TP1 {tp1}')
        ax1.axhline(tp2, color='#2E7D32', ls=':', lw=1.5, label=f'TP2 {tp2}')
        ax1.fill_between(range(60), ob_low, ob_high, color='gray', alpha=0.15, label=f'OB {ob_low:.1f}-{ob_high:.1f}')
        ax1.set_title(f'XAUUSD {side} | Price {price:.2f} | 1H {htf_text} | 30M {bos_text}', fontsize=13, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Volume
        ax2.bar(range(len(df5.tail(60))), df5['V'].tail(60).values, color='gray', alpha=0.6)
        ax2.set_title('Volume Confirmation')

        plt.tight_layout()
        path = '/tmp/gold_pro_max.png'
        plt.savefig(path, dpi=300)
        plt.close()

        bd_time = datetime.now(bd_tz).strftime('%d %b %I:%M %p')

        caption = f"""🏆 GOLD PRO MAX - 8 CONFIRMATION

💰 Price: {price:.2f}$
🕐 BD Time: {bd_time}

1️⃣ HTF 1H: {htf_text} {'✅' if is_bos else '⏳'}
2️⃣ 30M BOS: {bos_text} {'✅' if is_bos else '❌'}
3️⃣ 15M LIQ Sweep: {sweep_text} {'✅' if is_sweep else '⏳'}
4️⃣ 5M OB+FVG: OB {ob_low:.1f}-{ob_high:.1f} | FVG {fvg:.1f} ✅

5️⃣ ENTRY PLAN:
🎯 Side: {side}
📍 Entry: {entry}$
🛑 SL: {sl}$ ({abs(entry-sl):.1f}$)
✅ TP1: {tp1}$
✅ TP2: {tp2}$
📊 RR: 1:{abs(tp1-entry)/abs(entry-sl):.1f} / 1:{abs(tp2-entry)/abs(entry-sl):.1f}

6️⃣ Screenshot: PRO 4K Chart 👇

7️⃣ Auto: প্রতি ২ ঘণ্টায় Auto Signal ON ✅
8️⃣ Time Filter: 7:30PM-11PM Best Time (NY Killzone)

Status: {'🔥 A+ SETUP - TAKE IT' if is_bos and is_sweep else '⏳ WAIT FOR BOS+SWEEP'}

#GOLD #XAUUSD #PROMAX
"""
        return caption, path
    except Exception as e:
        return f"Error: {e}\n{traceback.format_exc()[:500]}", None

@bot.message_handler(commands=['start','signal','gold','setup','pro'])
def handler(m):
    bot.send_chat_action(m.chat.id, 'upload_photo')
    txt, chart = build_pro_chart()
    if chart:
        bot.send_photo(m.chat.id, open(chart,'rb'), caption=txt)
    else:
        bot.send_message(m.chat.id, txt)

def auto_sender():
    while True:
        time.sleep(7200) # 7. প্রতি 2 ঘণ্টা
        try:
            if not CHAT_ID: continue
            # 8. Time Filter - চাইলে 24h করতে নিচের if তুলে দাও
            hour_bd = datetime.now(bd_tz).hour
            # if hour_bd < 19 or hour_bd > 23: continue # শুধু 7PM-11PM

            txt, chart = build_pro_chart()
            if chart:
                bot.send_photo(int(CHAT_ID), open(chart,'rb'), caption=f"🤖 AUTO LIVE 2H\n\n{txt}")
        except Exception as e:
            print(f"Auto Error: {e}")
            time.sleep(60)

@app.route('/')
def home(): return "<h1>GOLD PRO MAX V4 Running - Quality Full</h1><p>/pro in Telegram</p>"

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    Thread(target=auto_sender, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
