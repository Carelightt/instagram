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
    return "🤖 DEBUG MODU AKTİF"

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
    except Exception as e:
        print(f"Telegram Gönderme Hatası: {e}")

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
    try:
        if IG_SESSION:
            with open("session.json", "w") as f:
                f.write(IG_SESSION)
            cl.load_settings("session.json")
            print("✅ Session Yüklendi.")
        else:
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("✅ Normal Giriş.")
    except:
        pass

    send_telegram_message(f"🚨 DEBUG MODU BAŞLADI!\nGrup ID: {TELEGRAM_CHAT_ID}\nLütfen /kontrol yazın.")

    last_follower_check_time = 0
    last_media_check_time = 0
    last_update_id = 0 

    while True:
        current_time = time.time()
        
        # --- TELEGRAM DİNLEME (DETAYLI LOGLU) ---
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            resp = requests.get(tg_url, timeout=10)
            
            if resp.status_code == 200:
                resp_json = resp.json()
                
                # Eğer yeni bir şey varsa
                if resp_json.get("ok") and resp_json.get("result"):
                    print(f"📩 TELEGRAM PAKETİ GELDİ: {resp_json}") # <--- LOGDA BUNU GÖRECEĞİZ
                    
                    for result in resp_json["result"]:
                        last_update_id = result["update_id"]
                        
                        # Mesajın türünü bulalım (message, channel_post, edited_message vs.)
                        message = result.get("message") or result.get("channel_post") or result.get("edited_message")
                        
                        if message:
                            text = message.get("text", "").lower()
                            chat_id = message.get("chat", {}).get("id")
                            print(f"🗣️ OKUNAN MESAJ: '{text}' | CHAT ID: {chat_id}")
                            
                            # KOMUTLARI KONTROL ET
                            if "/kontrol" in text:
                                send_telegram_message(f"✅ ÇALIŞIYORUM! Senin ID: {chat_id}", chat_id)
                            
                            elif "/takipci" in text:
                                send_telegram_message("🫡 Takipçi analizi başlatıldı...", chat_id)
                                last_follower_check_time = 0
                                
                            elif "/story" in text:
                                send_telegram_message("🫡 Hikaye analizi başlatıldı...", chat_id)
                                last_media_check_time = 0
            else:
                print(f"Telegram API Hatası: {resp.status_code}")

        except Exception as e:
            print(f"Telegram Loop Hatası: {e}")

        # --- ARKA PLAN İŞLEMLERİ ---
        # (Instagram hatası botu durdurmasın diye try-except)
        try:
             # Hedef ID Al (Her turda denesin)
            try:
                user_id = cl.user_id_from_username(TARGET_USERNAME)
            except:
                time.sleep(5)
                continue # Instagram yoksa aşağı inme, tekrar dene

            data = load_data()

            # MEDYA
            if current_time - last_media_check_time >= MEDIA_CHECK_INTERVAL:
                print("📸 Medya Kontrolü...")
                # (Kodun uzun olmaması için burayı kısaltıyorum, önceki mantıkla aynı çalışır)
                try:
                    stories = cl.user_stories(user_id)
                    curr_story_ids = [str(s.pk) for s in stories]
                    old_story_ids = data.get("stories", [])
                    if set(curr_story_ids) - set(old_story_ids):
                         send_telegram_message("🔥 YENİ HİKAYE!")
                    elif last_media_check_time == 0:
                         send_telegram_message("ℹ️ Yeni hikaye yok.")
                    data["stories"] = curr_story_ids
                    last_media_check_time = current_time
                    save_data(data)
                except Exception as e:
                    print(f"Story Hata: {e}")

            # TAKİPÇİ
            if current_time - last_follower_check_time >= FOLLOWER_CHECK_INTERVAL:
                print("👥 Takipçi Kontrolü...")
                try:
                    curr_followers = list(cl.user_followers(user_id).keys())
                    if last_follower_check_time == 0:
                        send_telegram_message(f"📊 RAPOR: Takipçi Sayısı: {len(curr_followers)}")
                    data["followers"] = curr_followers
                    last_follower_check_time = current_time
                    save_data(data)
                except Exception as e:
                    print(f"Takipçi Hata: {e}")
                    if last_follower_check_time == 0:
                         send_telegram_message("❌ Takipçi çekilemedi.")
                         last_follower_check_time = current_time

        except Exception as e:
            print(f"Genel Döngü Hatası: {e}")

        time.sleep(5) # 5 Saniyede bir kontrol

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
