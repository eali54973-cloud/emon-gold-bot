import os
from flask import Flask, render_template_string
from threading import Thread
import telebot, yfinance as yf

BOT_TOKEN=os.getenv("BOT_TOKEN")
bot=telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None
app=Flask(__name__)

def analyze():
    tfs={"4H":"4h","1H":"1h","30M":"30m","15M":"15m"}
    res={};score=0
    for n,i in tfs.items():
        try:
            df=yf.download("GC=F",period="5d",interval=i,progress=False)
            c=df['Close'].iloc[-1]
            e50=df['Close'].ewm(span=50).mean().iloc[-1]
            e200=df['Close'].ewm(span=200).mean().iloc[-1]
            ok=c>df['High'].tail(20).max()*0.998 and e50>e200
            res[n]="✅ Bullish" if ok else "❌ No BOS"
            if ok:score+=2
        except:res[n]="Loading"
    return res,f"{score}/8",score>=8

@app.route('/')
def home():
    r,q,a=analyze()
    return render_template_string("<h2>XAU SMC BOT @Emon_sheak</h2><h3>Q:{{q}} A+:{{a}}</h3>{%for k,v in r.items()%}<p>{{k}}:{{v}}</p>{%endfor%}",r=r,q=q,a=a)

@bot.message_handler(commands=['start','signal'])
def sig(m):
    r,q,a=analyze()
    bot.reply_to(m,f"GOLD {q}\n{r}")

def run_b():
    if bot:bot.infinity_polling()
def run_w():
    app.run(host="0.0.0.0",port=10000)

if __name__=="__main__":
    Thread(target=run_b).start()
    run_w()
