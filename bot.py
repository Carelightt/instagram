import time
import json
import requests
import os
import threading
from instagrapi import Client
from flask import Flask

# --- FLASK (Render İçin) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Komut Dinliyor..."

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
IG_SESSION = os.environ.get("IG_SESSION")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ZAMANLAYICILAR (Saniye)
MEDIA_CHECK_INTERVAL = 900    # 15 Dakika (Otomatik kontrol süresi)
FOLLOWER_CHECK_INTERVAL = 3600 # 1 Saat (Otomatik kontrol süresi)

# --- YARDIMCI FONKSİYONLAR ---
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

# --- ANA BOT DÖNGÜSÜ ---
def bot_loop():
    cl = Client()
    print("Instagram'a giriş yapılıyor...")
    
    # 1. GİRİŞ İŞLEMİ
    try:
        if IG_SESSION:
            print("🔑 Session bulundu...")
            with open("session.json", "w") as f:
                f.write(IG_SESSION)
            cl.load_settings("session.json")
            print("✅ Session yüklendi (Login atlandı).")
        else:
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("✅ Normal Giriş Başarılı.")
    except Exception as e:
        print(f"❌ Giriş Hatası: {e}")
        pass

    # Başlangıç Mesajı
    send_telegram_message("🤖 Bot Online! Komutları bekliyorum:\n/takipci - Takipçi Analizi Yap\n/story - Hikaye Kontrolü Yap\n/kontrol - Durum Kontrolü")

    # Zamanlayıcı Değişkenleri
    last_follower_check_time = 0
    last_media_check_time = 0
    last_update_id = 0 # Telegram mesaj offseti

    while True:
        current_time = time.time()
        
        # Hedef ID'yi her turda garantiye alalım (Hata olursa döngü başa döner)
        try:
            user_id = cl.user_id_from_username(TARGET_USERNAME)
        except:
            time.sleep(30)
            continue

        # Veriyi yükle
        data = load_data()
        
        # ==========================================================
        # 1. TELEGRAM KOMUTLARINI DİNLE (POLLING)
        # ==========================================================
        try:
            # Son mesajları çek
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            resp = requests.get(tg_url).json()
            
            if resp.get("ok"):
                for result in resp["result"]:
                    last_update_id = result["update_id"] # Bu mesajı okundu say
                    
                    message = result.get("message", {})
                    text = message.get("text", "").lower()
                    chat_id = str(message.get("chat", {}).get("id"))
                    
                    # Sadece senin grubundan gelen mesajlara bak
                    if chat_id == str(TELEGRAM_CHAT_ID) or str(TELEGRAM_CHAT_ID) in chat_id:
                        
                        if "/takipci" in text or "/takip" in text:
                            send_telegram_message("🫡 Emredersiniz! Takipçi analizi başlatılıyor...")
                            last_follower_check_time = 0 # Süreyi sıfırla ki aşağıda hemen çalışsın
                        
                        elif "/story" in text:
                            send_telegram_message("🫡 Emredersiniz! Hikayeler taranıyor...")
                            last_media_check_time = 0 # Süreyi sıfırla ki aşağıda hemen çalışsın
                        
                        elif "/kontrol" in text:
                            send_telegram_message("✅ Sistem Aktif! Nöbetteyim.")

        except Exception as e:
            print(f"Telegram okuma hatası: {e}")

        # ==========================================================
        # 2. STORY & MEDYA KONTROLÜ (Otomatik veya Manuel tetiklenir)
        # ==========================================================
        if current_time - last_media_check_time >= MEDIA_CHECK_INTERVAL:
            print("📸 Medya/Story kontrolü yapılıyor...")
            try:
                # STORY
                stories = cl.user_stories(user_id)
                curr_story_ids = [str(s.pk) for s in stories]
                old_story_ids = data.get("stories", [])
                
                new_stories = set(curr_story_ids) - set(old_story_ids)
                if new_stories:
                    send_telegram_message(f"🔥 YENİ HİKAYE VAR! ({len(new_stories)} adet)")
                elif last_media_check_time == 0: # Eğer manuel komutla çalıştıysa ve yeni yoksa bilgi ver
                    send_telegram_message(f"ℹ️ Yeni hikaye yok. Aktif hikaye sayısı: {len(curr_story_ids)}")
                
                data["stories"] = curr_story_ids
                
                # MEDYA (POST)
                medias = cl.user_medias(user_id, amount=10) # Hızlı olsun diye 10
                curr_media_map = {str(m.pk): m for m in medias}
                old_media_map = data.get("medias", {})
                
                for m_id, m in curr_media_map.items():
                    if m_id not in old_media_map:
                        # Arşiv kontrolü vs. burada (kısaltıldı)
                        send_telegram_message(f"📸 YENİ GÖNDERİ!\nLink: https://instagram.com/p/{m.code}")
                
                # Kaydet
                new_media_save = {}
                for m_id, m in curr_media_map.items():
                    new_media_save[m_id] = {"code": m.code}
                data["medias"] = new_media_save
                
                # Süreyi güncelle
                last_media_check_time = current_time
                save_data(data)
                
            except Exception as e:
                print(f"Medya hatası: {e}")

        # ==========================================================
        # 3. TAKİPÇİ KONTROLÜ (Otomatik veya Manuel tetiklenir)
        # ==========================================================
        if current_time - last_follower_check_time >= FOLLOWER_CHECK_INTERVAL:
            print("👥 Takipçi kontrolü yapılıyor...")
            try:
                curr_followers = list(cl.user_followers(user_id).keys())
                curr_following = list(cl.user_following(user_id).keys())
                
                old_followers = data.get("followers", [])
                
                if old_followers:
                    # Değişiklik var mı?
                    new_fol = set(curr_followers) - set(old_followers)
                    for uid in new_fol: send_telegram_message(f"🚨 YENİ TAKİPÇİ: {uid}")
                    
                    if last_follower_check_time == 0: # Manuel komutsa rapor ver
                        send_telegram_message(f"📊 RAPOR:\nTakipçi: {len(curr_followers)}\nTakip Edilen: {len(curr_following)}\n(Değişiklik varsa yukarıda listelendi)")
                else:
                    # İlk veriler
                    send_telegram_message(f"🕵️‍♂️ BAŞLANGIÇ VERİLERİ:\nTakipçi: {len(curr_followers)}\nTakip Edilen: {len(curr_following)}")
                
                data["followers"] = curr_followers
                data["following"] = curr_following
                
                # Süreyi güncelle (Böylece 1 saat beklemeye başlar)
                last_follower_check_time = current_time
                save_data(data)
                
            except Exception as e:
                print(f"Takipçi hatası: {e}")
                if last_follower_check_time == 0:
                     send_telegram_message("❌ Takipçi listesi alınamadı (Instagram limitlemiş olabilir).")
                     last_follower_check_time = current_time # Sürekli denememesi için süreyi güncelle

        # Hızlı Döngü (Her 10 saniyede bir Telegram'a bakmak için)
        time.sleep(10)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
