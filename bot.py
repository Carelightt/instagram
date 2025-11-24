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
    return "🤖 GEVEZE BOT AKTİF"

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

MEDIA_CHECK_INTERVAL = 900
FOLLOWER_CHECK_INTERVAL = 3600

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

def load_data():
    if not os.path.exists("takip_data.json"):
        return {"followers": [], "following": [], "stories": [], "medias": {}, "profile": {}, "highlights": []}
    try:
        with open("takip_data.json", "r") as f:
            data = json.load(f)
            keys = ["followers", "following", "stories", "medias", "profile", "highlights"]
            for k in keys:
                if k not in data: data[k] = {} if k in ["medias", "profile"] else []
            return data
    except:
        return {"followers": [], "following": [], "stories": [], "medias": {}, "profile": {}, "highlights": []}

def save_data(data):
    with open("takip_data.json", "w") as f:
        json.dump(data, f)

def bot_loop():
    cl = Client()
    print("Instagram'a giriş yapılıyor...")
    
    # GİRİŞ KISMI
    try:
        if IG_SESSION:
            with open("session.json", "w") as f:
                f.write(IG_SESSION)
            cl.load_settings("session.json")
            print("✅ Session Yüklendi.")
        else:
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("✅ Normal Giriş.")
    except Exception as e:
        print(f"Giriş Hatası: {e}")

    send_telegram_message(f"🚨 BOT YENİDEN BAŞLADI!\nLütfen /takipci yazıp dene.")

    last_follower_check_time = 0
    last_media_check_time = 0
    last_update_id = 0 

    while True:
        current_time = time.time()
        
        # --- TELEGRAM DİNLEME ---
        try:
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
                        
                        if "/kontrol" in text:
                            send_telegram_message(f"✅ ÇALIŞIYORUM! ID: {chat_id}", chat_id)
                        
                        elif "/takipci" in text:
                            send_telegram_message("⏳ Instagram'a bağlanılıyor, lütfen bekle...", chat_id)
                            # EMRİ ALINCA HEMEN İŞLEM YAP (ZAMANLAYICIYI BEKLEME)
                            try:
                                # Hedef ID'yi tazeleyelim
                                user_id = cl.user_id_from_username(TARGET_USERNAME)
                                
                                # Takipçileri çekmeye çalış
                                curr_followers = cl.user_followers(user_id) # Bu işlem uzun sürerse burada bekler
                                count = len(curr_followers)
                                
                                # Başarılı olursa yaz
                                send_telegram_message(f"📊 ANALİZ BİTTİ!\n👤 Takipçi Sayısı: {count}", chat_id)
                                
                                # Veritabanını güncelle
                                data = load_data()
                                data["followers"] = list(curr_followers.keys())
                                save_data(data)
                                
                                # Otomatik kontrol saatini sıfırla (1 saat sonraya at)
                                last_follower_check_time = time.time()
                                
                            except Exception as e:
                                # İŞTE BURASI ÖNEMLİ: HATA VARSA SÖYLE
                                error_msg = str(e)
                                if "login_required" in error_msg:
                                    send_telegram_message("❌ HATA: Instagram giriş istiyor! Session patlamış olabilir.", chat_id)
                                elif "challenge_required" in error_msg:
                                    send_telegram_message("❌ HATA: Instagram doğrulama (challenge) istiyor! Hesabı telefondan onayla.", chat_id)
                                elif "feedback_required" in error_msg:
                                    send_telegram_message("❌ HATA: Çok sık istek attığın için Instagram seni geçici engelledi (Spam Koruması).", chat_id)
                                else:
                                    send_telegram_message(f"❌ BEKLENMEYEN HATA:\n{error_msg}", chat_id)

                        elif "/story" in text:
                            send_telegram_message("⏳ Hikayelere bakılıyor...", chat_id)
                            try:
                                user_id = cl.user_id_from_username(TARGET_USERNAME)
                                stories = cl.user_stories(user_id)
                                count = len(stories)
                                if count > 0:
                                    send_telegram_message(f"🔥 EVET! {count} adet hikayesi var.", chat_id)
                                else:
                                    send_telegram_message("ℹ️ Maalesef, şu an hikaye yok.", chat_id)
                                last_media_check_time = time.time()
                            except Exception as e:
                                send_telegram_message(f"❌ STORY HATASI: {str(e)}", chat_id)

        except Exception as e:
            print(f"Telegram Loop Hatası: {e}")

        # OTOMATİK KONTROLLER (Sadece vakti geldiyse)
        # ... (Kod uzamasın diye burayı kısalttım, manuel komut çalışsın yeter şu an)
        
        time.sleep(2)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
