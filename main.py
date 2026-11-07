import telebot
from groq import Groq
import os, requests, re
import yfinance as yf
from gtts import gTTS

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")
client = Groq(api_key=GROQ_KEY)
bot = telebot.TeleBot(BOT_TOKEN)

def ask_groq(prompt):
    res = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "system", "content": "You are Tom, assistant of Hashem from Yemen. Answer in Yemeni dialect. For trading, educational only, never give guaranteed buy/sell recommendation. For medicine, general info only and say see a doctor."}, {"role": "user", "content": prompt}])
    return res.choices[0].message.content

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        bot.reply_to(message, "سمعتك يا هاشم، جاري تفريغ الصوت وترجمته...")
        file_info = bot.get_file(message.voice.file_id)
        data = bot.download_file(file_info.file_path)
        open("voice.ogg", "wb").write(data)
        with open("voice.ogg", "rb") as f:
            trans = client.audio.transcriptions.create(file=f, model="whisper-large-v3", response_format="text")
        text_ar = ask_groq(f"ترجم هذا النص للعربية اليمنية واشرحه ببساطة: {trans}")
        bot.reply_to(message, f"اللي قلته:\n{trans}\n\nالترجمة والشرح:\n{text_ar}")
        tts = gTTS(text=text_ar[:400], lang='ar')
        tts.save("reply.mp3")
        bot.send_voice(message.chat.id, open("reply.mp3","rb"))
    except Exception as e:
        bot.reply_to(message, f"ما قدرت أترجم الصوت: {e}")

@bot.message_handler(func=lambda m: True)
def reply(message):
    text = message.text or ""
    if text.startswith("ترجم"):
        to_translate = text.replace("ترجم","").strip()
        bot.reply_to(message, ask_groq(f"ترجم هذا النص، إذا كان عربي ترجمه إنجليزي، وإذا كان إنجليزي ترجمه عربي يمني: {to_translate}"))
        return
    if text.startswith("صورة"):
        prompt = text.replace("صورة","").strip()
        url = f"https://image.pollinations.ai/prompt/{prompt}"
        bot.send_photo(message.chat.id, url, caption=f"صورتك: {prompt}")
        return
    if text.startswith("حلل"):
        pair = text.replace("حلل","").strip().upper() or "EURUSD"
        try:
            symbol = pair + "=X"
            data = yf.download(symbol, period="3mo", interval="1d", progress=False)
            close = data['Close']
            last = float(close.iloc[-1])
            ma50 = float(close.tail(50).mean())
            ma200 = float(close.tail(200).mean()) if len(close)>=200 else ma50
            delta = close.diff().dropna()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = 100 - (100/(1+gain/loss))
            rsi_val = float(rsi.iloc[-1])
            support = float(close.tail(20).min())
            resist = float(close.tail(20).max())
            prompt = f"اشرح تحليل {pair} بالتفصيل للمبتدئ بلهجة يمنية. السعر {last:.4f}, MA50 {ma50:.4f}, MA200 {ma200:.4f}, RSI {rsi_val:.1f}, دعم {support:.4f}, مقاومة {resist:.4f}. اشرح الاتجاه والدعم والمقاومة والاستراتيجية التعليمية، وقل انه تعليمي فقط وليس توصية."
            bot.reply_to(message, ask_groq(prompt))
        except Exception as e:
            bot.reply_to(message, f"ما قدرت أحلل {pair} الآن: {e}")
        return
    if "استراتيجية" in text or "استراتيجيه" in text:
        bot.reply_to(message, ask_groq(f"اشرح هذه الاستراتيجية بالتفصيل خطوة خطوة بلهجة يمنية بسيطة مع مثال على EURUSD ومتى تكون خطيرة، تعليمي فقط: {text}"))
        return
    if "أخبار" in text or "اخبار" in text:
        q = text.replace("أخبار","").replace("اخبار","").strip() or "سوق الأسهم"
        try:
            rss = requests.get(f"https://news.google.com/rss/search?q={q}&hl=ar&gl=SA&ceid=SA:ar", timeout=10).text
            titles = re.findall(r"<title>(.*?)</title>", rss)[1:4]
            bot.reply_to(message, "آخر أخبار " + q + ":\n\n" + "\n\n".join([f"- {t}" for t in titles]))
        except:
            bot.reply_to(message, "ما قدرت أجيب الأخبار الآن")
        return
    bot.reply_to(message, ask_groq(text))

print("Tom Full Pro is working...")
bot.polling(none_stop=True)
