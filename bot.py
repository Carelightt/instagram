import time
import json
import requests
import os
import threading
from instagrapi import Client
from flask import Flask

# --- FLASK AYARLARI (RENDER İÇİN GEREKLİ) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Calisiyor Kanka!"

def run_flask():
    # Render'ın verdiği portu dinle, yoksa 5000 kullan
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- BOT AYARLARI (ARTIK ENV'DEN ALIYOR) ---
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STORY_CHECK_INTERVAL = 900   # 15 dk
FOLLOWER_CHECK_INTERVAL = 3600 # 1 Saat

def send_telegram_message(message):
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

def load_data():
    if not os.path.exists("takip_data.json"):
        return {"followers": [], "following": [], "stories": []}
    try:
        with open("takip_data.json", "r") as f:
            data = json.load(f)
            if "stories" not in data: data["stories"] = []
            return data
    except:
        return {"followers": [], "following": [], "stories": []}

def save_data(data):
    # Render'da dosyalar geçicidir, restartta silinir. Bilgin olsun.
    with open("takip_data.json", "w") as f:
        json.dump(data, f)

def bot_loop():
    cl = Client()
    print("Instagram'a giriş yapılıyor...")
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        print("Giriş Başarılı!")
    except Exception as e:
        print(f"Giriş Hatası: {e}")
        return

    last_follower_check_time = 0

    while True:
        try:
            current_time = time.time()
            try:
                user_id = cl.user_id_from_username(TARGET_USERNAME)
            except:
                time.sleep(60)
                continue
            
            data = load_data()
            old_story_ids = data.get("stories", [])
            
            # --- HİKAYE KONTROL ---
            try:
                stories = cl.user_stories(user_id)
                curr_story_ids = [str(story.pk) for story in stories]
                new_stories = set(curr_story_ids) - set(old_story_ids)
                
                if new_stories:
                    send_telegram_message(f"🔥 YENİ HİKAYE!\n{TARGET_USERNAME} yeni hikaye attı!")
                    data["stories"] = curr_story_ids
                    save_data(data)
                elif set(curr_story_ids) != set(old_story_ids):
                    data["stories"] = curr_story_ids
                    save_data(data)
            except Exception as e:
                print(f"Story hata: {e}")

            # --- TAKİPÇİ KONTROL ---
            if current_time - last_follower_check_time >= FOLLOWER_CHECK_INTERVAL:
                try:
                    curr_followers = cl.user_followers(user_id)
                    curr_following = cl.user_following(user_id)
                    
                    curr_followers_ids = list(curr_followers.keys())
                    curr_following_ids = list(curr_following.keys())
                    
                    old_followers_ids = data.get("followers", [])
                    old_following_ids = data.get("following", [])
                    
                    if old_followers_ids:
                        new_followers = set(curr_followers_ids) - set(old_followers_ids)
                        for uid in new_followers:
                            u = curr_followers[uid]
                            send_telegram_message(f"🚨 YENİ TAKİPÇİ: {u.username}")

                        new_following = set(curr_following_ids) - set(old_following_ids)
                        for uid in new_following:
                            u = curr_following[uid]
                            send_telegram_message(f"👀 YENİ TAKİP ETTİ: {u.username}")
                    
                    data["followers"] = curr_followers_ids
                    data["following"] = curr_following_ids
                    save_data(data)
                    last_follower_check_time = current_time
                except Exception as e:
                    print(f"Takipçi hata: {e}")

        except Exception as e:
            print(f"Genel Hata: {e}")
            time.sleep(60)
        
        time.sleep(STORY_CHECK_INTERVAL)

if __name__ == "__main__":
    # Flask'ı ayrı thread'de, Botu ayrı thread'de başlat
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    
    t1.start()
    t2.start()