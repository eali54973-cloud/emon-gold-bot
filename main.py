import os, requests
from flask import Flask, render_template_string
from threading import Thread
import telebot
import pandas as pd

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None
app = Flask(__name__)

def get_data(interval):
    mapping = {"1d":"1d", "1h":"1h", "30m":"30m", "15m":"15m"}
    b_interval = mapping.get(interval, "1h")
    url = f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={b_interval}&limit=200"
    try:
        r = requests.get(url, timeout=10).json()
        if not r or isinstance(r, dict):
            return None
        df = pd.DataFrame(r, columns=['time','Open','High','Low','Close','Vol','c2','c3','c4','c5','c6','c7'])
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Open'] = df['Open'].astype(float)
        return df
    except:
        return None

def analyze():
    tfs = {"4H": "1d", "1H": "1h", "30M": "30m", "15M": "15m"}
    res = {}
    score = 0
    price = 0
    for name, interval in tfs.items():
        df = get_data(interval)
        if df is None:
            res[name] = "⏳ Loading..."
            continue
        try:
            close = df['Close'].iloc[-1]
            if name == "1H":
                price = float(close)
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1]
            ema200 = df['Close'].ewm(span=200).mean().iloc[-1]
            high20 = df['High'].tail(20).max()
            low20 = df['Low'].tail(20).min()

            if close > high20 * 0.998 and ema50 > ema200:
                res[name] = "✅ Bullish BOS"
                score += 2
            elif close < low20 * 1.002 and ema50 < ema200:
                res[name] = "🔻 Bearish BOS"
                score += 1
            else:
                res[name] = "❌ No BOS"
        except:
            res[name] = "❌ Error"

    quality = f"{score}/8"
    is_a_plus = score >= 6
    return res, quality, is_a_plus, price

@app.route('/')
def home():
    r,q,a,p = analyze()
    html = """
    <h2>XAU SMC BOT LIVE ✅ @Emon_sheak</h2>
    <h3>Price: {{p}} | Quality: {{q}} | A+: {{a}}</h3>
    {% for k,v in r.items() %}<p><b>{{k}}:</b> {{v}}</p>{% endfor %}
    """
    return render_template_string(html, r=r, q=q, a=a, p=round(p,2))

@bot.message_handler(commands=['start','signal'])
def sig(m):
    r,q,a,p = analyze()
    txt = f"🔥 XAU GOLD SMC SIGNAL 🔥\n💰 Price: {round(p,2)} (PAXG ~ XAU)\n📊 Quality: {q} {'🔥 A+ SETUP' if a else ''}\n\n4H: {r.get('4H')}\n1H: {r.get('1H')}\n30M: {r.get('30M')}\n15M: {r.get('15M')}\n\n{'✅ STRONG SIGNAL' if a else '⏳ WAIT FOR A+ (6/8+)'} \n@Emon_sheak"
    bot.reply_to(m, txt)

def run_b():
    if bot:
        bot.infinity_polling()

def run_w():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    Thread(target=run_b).start()
    run_w()
