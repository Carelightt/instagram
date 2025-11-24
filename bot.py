import time
import json
import requests
import os
import threading
from instagrapi import Client
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 STALKER BOT (ANTI-SPAM MODU)"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# AYARLAR
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
IG_SESSION = os.environ.get("IG_SESSION")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

def bot_loop():
    cl = Client()
    
    # --- CİHAZ TAKLİDİ (Samsung Galaxy S23) ---
    # Bu ayarlar botun gerçek bir telefon gibi görünmesini sağlar
    cl.set_country("TR")
    cl.set_locale("tr_TR")
    cl.set_timezone_offset(3 * 3600) # GMT+3 (Türkiye)
    
    print("Instagram'a bağlanılıyor...")
    
    try:
        if IG_SESSION:
            with open("session.json", "w") as f:
                f.write(IG_SESSION)
            cl.load_settings("session.json")
            
            # Cihaz ayarlarını yükledikten sonra tekrar uygula
            cl.set_country("TR")
            cl.set_locale("tr_TR")
            
            print("✅ Session Yüklendi.")
        else:
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("✅ Normal Giriş.")
    except Exception as e:
        print(f"Giriş Pas Geçildi (Hata olabilir): {e}")

    send_telegram_message("♻️ Bot IP Değişimi Yapıldı. Hazır!")

    last_update_id = 0 

    while True:
        try:
            # Telegram'ı kontrol et
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            resp = requests.get(tg_url, timeout=10)
            
            if resp.status_code == 200:
                resp_json = resp.json()
                if resp_json.get("ok"):
                    for result in resp_json["result"]:
                        last_update_id = result["update_id"]
                        message = result.get("message", {})
                        text = message.get("text", "").lower()
                        chat_id = message.get("chat", {}).get("id")
                        
                        if "/takipci" in text:
                            send_telegram_message("🕵️‍♂️ Analiz yapılıyor... (Bu işlem 429 hatası yememek için yavaşlatıldı)", chat_id)
                            
                            # BEKLEME SÜRESİ EKLE (SPAM YAPMAMAK İÇİN)
                            time.sleep(5) 
                            
                            try:
                                # Kullanıcıyı çek
                                user_id = cl.user_id_from_username(TARGET_USERNAME)
                                info = cl.user_info(user_id) # Sadece genel bilgi çek (Followers listesi çekmek çok riskli)
                                
                                msg = f"📊 GÜNCEL DURUM:\n👤 Takipçi: {info.follower_count}\n👉 Takip Edilen: {info.following_count}\n(Detaylı liste spam riski nedeniyle çekilmedi)"
                                send_telegram_message(msg, chat_id)
                                
                            except Exception as e:
                                if "429" in str(e):
                                    send_telegram_message("🔴 Hala banlıyız (429). 1-2 saat dinlenmesi lazım.", chat_id)
                                else:
                                    send_telegram_message(f"❌ Hata: {str(e)}", chat_id)

        except Exception as e:
            print(f"Loop Hata: {e}")
            time.sleep(10)

        time.sleep(5)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
