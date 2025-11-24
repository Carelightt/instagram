import time
import json
import requests
import os
import threading
from datetime import datetime
from instagrapi import Client
from flask import Flask

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🕵️ Ultimate Stalker Bot Aktif (Session Modu)!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
IG_SESSION = os.environ.get("IG_SESSION") # <--- YENİ EKLENEN
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

MEDIA_CHECK_INTERVAL = 900
FOLLOWER_CHECK_INTERVAL = 3600

def send_telegram_message(message):
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "disable_web_page_preview": True}
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
    
# --- YENİ GİRİŞ YÖNTEMİ (TURBO MOD) ---
    try:
        if IG_SESSION:
            print("🔑 Session (Cookie) bulundu, dosyaya yazılıyor...")
            
            with open("session.json", "w") as f:
                f.write(IG_SESSION)
            
            # Ayarları yükle
            cl.load_settings("session.json")
            
            # BURAYA DİKKAT: cl.login SATIRINI SİLDİK!
            # Çünkü session varken tekrar login demek, Instagram'ı şüphelendiriyor.
            
            print("✅ Session yüklendi, ekstra giriş yapılmadan devam ediliyor!")
            
        else:
            print("⚠️ Session yok, mecburen normal giriş deneniyor...")
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("✅ Normal Giriş Başarılı!")
            
    except Exception as e:
        print(f"❌ Giriş Hatası: {e}")
        # Hata olsa bile devam etmeye çalışsın, belki session çalışır
        pass 
    # ----------------------------------------

    last_follower_check_time = 0
    # ... (Kodun geri kalanı aynı)
    # ----------------------------------------

    last_follower_check_time = 0

    while True:
        try:
            print(f"\n[{time.strftime('%H:%M')}] Kontrol başlıyor...")
            current_time = time.time()
            
            try:
                user_id = cl.user_id_from_username(TARGET_USERNAME)
            except Exception as e:
                print(f"Kullanıcı bulunamadı ({e}), bekleniyor...")
                time.sleep(60)
                continue

            data = load_data()
            
            # 1. PROFİL ANALİZİ
            try:
                full_info = cl.user_info(user_id)
                new_profile = {
                    "biography": full_info.biography,
                    "profile_pic_url": str(full_info.profile_pic_url),
                    "external_url": full_info.external_url,
                    "full_name": full_info.full_name
                }
                old_profile = data.get("profile", {})

                if old_profile:
                    if new_profile["biography"] != old_profile.get("biography"):
                        send_telegram_message(f"📝 BİYO DEĞİŞTİ!\nEski: {old_profile.get('biography')}\nYeni: {new_profile['biography']}")
                    if new_profile["external_url"] != old_profile.get("external_url"):
                         send_telegram_message(f"🔗 LİNK DEĞİŞTİ!\nYeni: {new_profile['external_url']}")
                data["profile"] = new_profile
            except: pass

            # 2. STORY
            try:
                stories = cl.user_stories(user_id)
                curr_story_ids = [str(s.pk) for s in stories]
                old_story_ids = data.get("stories", [])
                new_stories = set(curr_story_ids) - set(old_story_ids)
                for s_id in new_stories:
                    msg = "🔥 YENİ HİKAYE!"
                    story_obj = next((s for s in stories if str(s.pk) == s_id), None)
                    if story_obj and story_obj.music_metadata:
                         msg += f"\n🎵 Müzik: {story_obj.music_metadata.title}"
                    send_telegram_message(msg)
                data["stories"] = curr_story_ids
            except: pass

            # 3. MEDYA & ARŞİV
            try:
                medias = cl.user_medias(user_id, amount=20)
                curr_media_map = {str(m.pk): m for m in medias}
                old_media_map = data.get("medias", {})
                
                for m_id, m in curr_media_map.items():
                    if m_id not in old_media_map:
                        post_time = m.taken_at.timestamp()
                        is_old = (current_time - post_time) > (86400 * 2)
                        caption = m.caption_text if m.caption_text else ""
                        link = f"https://instagram.com/p/{m.code}"
                        
                        if is_old:
                             send_telegram_message(f"🔄 ARŞİVDEN DÖNEN!\nLink: {link}")
                        else:
                             msg = f"📸 YENİ GÖNDERİ!\n📝 {caption}\nLink: {link}"
                             if m.location: msg += f"\n📍 {m.location.name}"
                             send_telegram_message(msg)
                    else:
                        old_cap = old_media_map[m_id].get("caption", "")
                        new_cap = m.caption_text if m.caption_text else ""
                        if old_cap != new_cap:
                            send_telegram_message(f"✏️ AÇIKLAMA DEĞİŞTİ!\nYeni: {new_cap}\nLink: https://instagram.com/p/{m.code}")
                
                new_media_save = {}
                for m_id, m in curr_media_map.items():
                    new_media_save[m_id] = {"caption": m.caption_text if m.caption_text else "", "code": m.code}
                data["medias"] = new_media_save
            except: pass

            # 5. TAKİPÇİ (1 SAAT)
            if current_time - last_follower_check_time >= FOLLOWER_CHECK_INTERVAL:
                print("⏳ Takipçi kontrolü...")
                try:
                    curr_followers = list(cl.user_followers(user_id).keys())
                    curr_following = list(cl.user_following(user_id).keys())
                    
                    old_followers = data.get("followers", [])
                    old_following = data.get("following", [])
                    
                    if old_followers:
                        new_fol = set(curr_followers) - set(old_followers)
                        for uid in new_fol: send_telegram_message(f"🚨 YENİ TAKİPÇİ: {uid}") # API limit yememek için isim çekmiyoruz burada
                        
                        new_fng = set(curr_following) - set(old_following)
                        for uid in new_fng: send_telegram_message(f"👀 YENİ TAKİP ETTİ: https://instagram.com/{uid}")
                    else:
                        send_telegram_message(f"🕵️‍♂️ OPERASYON BAŞLADI!\nTakipçi: {len(curr_followers)}\nTakip Edilen: {len(curr_following)}")
                    
                    data["followers"] = curr_followers
                    data["following"] = curr_following
                    last_follower_check_time = current_time
                except Exception as e:
                    print(f"Takipçi hata: {e}")

            save_data(data)
            print(f"Tur bitti. Bekleniyor...")

        except Exception as e:
            print(f"Genel Hata: {e}")
            time.sleep(60)
        
        time.sleep(MEDIA_CHECK_INTERVAL)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
