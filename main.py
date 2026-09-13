import os, requests, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None
app = Flask(__name__)

def get_df(interval):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval={interval}&limit=100"
    try:
        r = requests.get(url, timeout=15).json()
        df = pd.DataFrame(r, columns=['t','O','H','L','C','V','x','y','z','a','b','c'])
        for col in ['O','H','L','C']: df[col]=df[col].astype(float)
        return df
    except: return None

def get_price():
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=PAXGUSDT", timeout=10).json()
        return float(r['price'])
    except: return 4356.1

def tf_logic(df):
    if df is None: return None
    c = df['C'].iloc[-1]
    hi20 = df['H'].tail(20).max()
    lo20 = df['L'].tail(20).min()
    e50 = df['C'].ewm(50).mean().iloc[-1]
    BOS = "❌ No BOS"
    if c > hi20*0.998: BOS = "✅ Bullish BOS"
    elif c < lo20*1.002: BOS = "🔻 Bearish BOS"
    CHOCH = "Bullish" if df['C'].ewm(50).mean().iloc[-1] > df['C'].ewm(200).mean().iloc[-1] else "Bearish"
    SWEEP = "No Sweep"
    if df['H'].iloc[-2] > hi20 and df['C'].iloc[-2] < hi20: SWEEP="🔥 Sweep Bull"
    if df['L'].iloc[-2] < lo20 and df['C'].iloc[-2] > lo20: SWEEP="🔥 Sweep Bear"
    FVG = "No FVG"
    if df['L'].iloc[-1] > df['H'].iloc[-3]: FVG=f"Bullish FVG {df['H'].iloc[-3]:.1f}-{df['L'].iloc[-1]:.1f}"
    if df['H'].iloc[-1] < df['L'].iloc[-3]: FVG=f"Bearish FVG"
    OB = f"OB ~ {e50:.1f}"
    return {"BOS":BOS,"CHOCH":CHOCH,"SWEEP":SWEEP,"FVG":FVG,"OB":OB}

def build():
    price=get_price()
    data={}
    bull=0
    for name, inter in {"1H":"1h","30M":"30m","15M":"15m"}.items():
        v=tf_logic(get_df(inter))
        data[name]=v
        if v and "Bullish BOS" in v['BOS']: bull+=1
    if bull>=2:
        final="🔥 BUY A+ SETUP"; entry=price; sl=price-8; tp1=price+10; tp2=price+18
    elif bull==0:
        final="🔻 SELL SETUP"; entry=price; sl=price+8; tp1=price-10; tp2=price-18
    else:
        final="⏳ WAIT"; entry=price; sl=price; tp1=price; tp2=price
    return data, final, entry, sl, tp1, tp2, price

def make_chart(df, entry, sl, tp1, tp2, final):
    plt.figure(figsize=(8,4))
    plt.plot(df['C'].tail(50).values, label='Price', color='black')
    plt.axhline(entry, color='blue', linestyle='--', label=f'ENTRY {entry:.1f}')
    plt.axhline(sl, color='red', linestyle='--', label=f'SL {sl:.1f}')
    plt.axhline(tp1, color='green', linestyle='--', label=f'TP1 {tp1:.1f}')
    plt.axhline(tp2, color='green', linestyle=':', label=f'TP2 {tp2:.1f}')
    plt.title(final)
    plt.legend()
    plt.tight_layout()
    plt.savefig('/tmp/chart.png')
    plt.close()
    return '/tmp/chart.png'

@app.route('/')
def home():
    d,f,en,sl,tp1,tp2,p = build()
    h=f"<h2>{f} | Price {p}</h2>"
    for k,v in d.items():
        if v: h+=f"<p><b>{k}:</b> {v['BOS']} | {v['FVG']} | {v['OB']}</p>"
    h+=f"<h3>ENTRY {en:.2f} | SL {sl:.2f} | TP1 {tp1:.2f} | TP2 {tp2:.2f}</h3><img src='/chart' width=600>"
    return h

@app.route('/chart')
def chart_route():
    df = get_df("15m")
    _, f, en, sl, tp1, tp2, _ = build()
    make_chart(df, en, sl, tp1, tp2, f)
    return app.send_static_file('/tmp/chart.png') if False else open('/tmp/chart.png','rb').read(), 200, {'Content-Type':'image/png'}

@bot.message_handler(commands=['start','signal'])
def s(m):
    d,f,en,sl,tp1,tp2,p = build()
    df = get_df("15m")
    txt=f"🤖 XAU ROBOT @Emon_sheak\n💰 {p:.2f}\n🏆 {f}\n\n"
    for k in ["1H","30M","15M"]:
        v=d.get(k)
        if v: txt+=f"{k}: {v['BOS']} | {v['FVG']} | {v['OB']}\n"
    txt+=f"\n🎯 FINAL: {f}\nENTRY: {en:.2f}\nSL: {sl:.2f}\nTP1: {tp1:.2f}\nTP2: {tp2:.2f}"
    chart_path = make_chart(df, en, sl, tp1, tp2, f)
    bot.send_photo(m.chat.id, open(chart_path,'rb'), caption=txt)

def run_b():
    if bot: bot.infinity_polling()
def run_w():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    Thread(target=run_b).start()
    run_w()
