import os
from flask import Flask, render_template_string
from threading import Thread
import telebot
import yfinance as yf

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None
app = Flask(__name__)

def get_data(interval):
    try:
        # XAUUSD এর জন্য 2টা symbol try করবে
        for symbol in ["XAUUSD=X", "GC=F", "GOLD"]:
            df = yf.download(symbol, period="1mo", interval=interval, progress=False, auto_adjust=True)
            if not df.empty and len(df) > 50:
                # yfinance new version fix
                if 'Close' in df.columns:
                    return df
        return None
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

            # SMC BOS Logic
            is_bullish = close > (high20 * 0.999) and ema50 > ema200
            is_bearish = close < (df['Low'].tail(20).min() * 1.001) and ema50 < ema200

            if is_bullish:
                res[name] = "✅ Bullish BOS"
                score += 2
            elif is_bearish:
                res[name] = "🔻 Bearish BOS"
                score += 0
            else:
                res[name] = "❌ No BOS / CHoCH"
        except Exception as e:
            res[name] = f"❌ Error"

    quality = f"{score}/8"
    is_a_plus = score >= 6
    return res, quality, is_a_plus, price

@app.route('/')
def home():
    r, q, a, p = analyze()
    return render_template_string("""
    <h2>XAU SMC BOT @Emon_sheak LIVE ✅</h2>
    <h3>Price: {{p}} | Quality: {{q}} | A+: {{a}}</h3>
    {% for k,v in r.items() %}<p><b>{{k}}:</b> {{v}}</p>{% endfor %}
    """, r=r, q=q, a=a, p=round(p,2))

@bot.message_handler(commands=['start','signal','analysis'])
def sig(m):
    r, q, a, p = analyze()
    text = f"""🔥 XAU GOLD SMC SIGNAL 🔥
💰 Price: {round(p,2)}
📊 Quality: {q} {'🔥 A+ SETUP' if a else ''}

4H: {r.get('4H')}
1H: {r.get('1H')}
30M: {r.get('30M')}
15M: {r.get('15M')}

{'✅ STRONG BUY' if a else '⏳ WAIT FOR A+ (6/8+)'}

@Emon_sheak
"""
    bot.reply_to(m, text)

def run_b():
    if bot:
        bot.infinity_polling()

def run_w():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    Thread(target=run_b).start()
    run_w()
j
