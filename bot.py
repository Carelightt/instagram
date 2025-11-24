import time
import json
import requests
import os
import threading
from datetime import datetime
from instagrapi import Client
from flask import Flask

# --- FLASK (RENDER İÇİN AYAKTA TUTMA) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🕵️ Ultimate Stalker Bot Aktif!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR (ENV'DEN GELİR) ---
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ZAMANLAYICILAR (Saniye)
MEDIA_CHECK_INTERVAL = 900    # 15 Dakika (Post, Story, Bio, Yorum)
FOLLOWER_CHECK_INTERVAL = 3600 # 1 Saat (Takipçi Listesi - Ağır işlem)

# --- YARDIMCI FONKSİYONLAR ---
def send_telegram_message(message):
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "disable_web_page_preview": True}
    try:
        requests.post(url, data=data)
    except:
        pass

def send_telegram_photo(photo_url, caption):
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
    # Instagrapi bazen url, bazen path döner. Basitlik için sadece URL deniyoruz.
    try:
        requests.post(url, data=data, json={"photo": photo_url})
    except:
        send_telegram_message(caption + "\n(Fotoğraf yüklenemedi, link): " + str(photo_url))

def load_data():
    if not os.path.exists("takip_data.json"):
        return {
            "followers": [], "following": [], "stories": [], 
            "medias": {}, "profile": {}, "highlights": []
        }
    try:
        with open("takip_data.json", "r") as f:
            data = json.load(f)
            # Eksik anahtarları tamamla
            keys = ["followers", "following", "stories", "medias", "profile", "highlights"]
            for k in keys:
                if k not in data: 
                    data[k] = {} if k == "medias" or k == "profile" else []
            return data
    except:
        return {"followers": [], "following": [], "stories": [], "medias": {}, "profile": {}, "highlights": []}

def save_data(data):
    with open("takip_data.json", "w") as f:
        json.dump(data, f)

# --- BOT MANTIĞI ---
def bot_loop():
    cl = Client()
    print("Instagram'a giriş yapılıyor...")
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        print("✅ Giriş Başarılı!")
    except Exception as e:
        print(f"❌ Giriş Hatası: {e}")
        return

    last_follower_check_time = 0

    while True:
        try:
            print(f"\n[{time.strftime('%H:%M')}] Kontrol başlıyor...")
            current_time = time.time()
            
            # Hedef ID Bul
            try:
                user_id = cl.user_id_from_username(TARGET_USERNAME)
            except:
                print("Kullanıcı bulunamadı, 1 dk bekleniyor.")
                time.sleep(60)
                continue

            data = load_data()
            
            # ==========================================================
            # 1. PROFİL ANALİZİ (Bio, Foto, Link)
            # ==========================================================
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
                    # Bio Değişikliği
                    if new_profile["biography"] != old_profile.get("biography"):
                        msg = f"📝 BİYO DEĞİŞTİ!\nEski: {old_profile.get('biography')}\nYeni: {new_profile['biography']}"
                        send_telegram_message(msg)
                    
                    # Profil Fotosu
                    # URL'ler zamanla değişebilir, bu basit kontrol her zaman %100 çalışmaz ama değişimleri yakalar.
                    if new_profile["profile_pic_url"] != old_profile.get("profile_pic_url"):
                         # Foto URL'leri token içerdiği için her saat değişebilir, o yüzden sadece çok bariz farkları uyarmak zor.
                         # Ama yine de loglayalım.
                         pass 
                    
                    # Link Değişikliği
                    if new_profile["external_url"] != old_profile.get("external_url"):
                         msg = f"🔗 LİNK DEĞİŞTİ!\nYeni Link: {new_profile['external_url']}"
                         send_telegram_message(msg)

                data["profile"] = new_profile
            except Exception as e:
                print(f"Profil analiz hatası: {e}")

            # ==========================================================
            # 2. STORY & MÜZİK ANALİZİ
            # ==========================================================
            try:
                stories = cl.user_stories(user_id)
                curr_story_ids = [str(s.pk) for s in stories]
                old_story_ids = data.get("stories", [])
                
                new_stories = set(curr_story_ids) - set(old_story_ids)
                
                for s_id in new_stories:
                    # Story detayını bul
                    story_obj = next((s for s in stories if str(s.pk) == s_id), None)
                    if story_obj:
                        msg = f"🔥 YENİ HİKAYE!"
                        
                        # Müzik/Mood Analizi
                        if hasattr(story_obj, 'music_metadata') and story_obj.music_metadata:
                            music = story_obj.music_metadata
                            msg += f"\n🎵 Müzik: {music.title} - {music.artist_name}"
                        
                        send_telegram_message(msg)
                
                data["stories"] = curr_story_ids
            except Exception as e:
                print(f"Story hatası: {e}")

            # ==========================================================
            # 3. GÖNDERİLER, CAPTION, SİLİNENLER, KONUM, YORUMLAR
            # ==========================================================
            try:
                # Son 20 medyayı çek
                medias = cl.user_medias(user_id, amount=20)
                curr_media_map = {str(m.pk): m for m in medias}
                old_media_map = data.get("medias", {}) # Bu sadece ID ve Caption tutacak
                
                # A. YENİ GÖNDERİ & ARŞİVDEN DÖNEN
                for m_id, m in curr_media_map.items():
                    if m_id not in old_media_map:
                        # Bu ID veritabanımızda yok. Yeni mi? Arşivden mi?
                        # Timestamp kontrolü: Eğer post 2 gün öncesinden eskiyse "Arşivden Dönen"dir.
                        post_time = m.taken_at.timestamp()
                        is_old_post = (current_time - post_time) > (86400 * 2) # 2 gün
                        
                        caption_txt = m.caption_text if m.caption_text else "Açıklama yok"
                        
                        if is_old_post:
                             msg = f"🔄 ARŞİVDEN DÖNEN GÖNDERİ!\nEski bir gönderi profile geri eklendi.\nLink: https://instagram.com/p/{m.code}"
                             send_telegram_message(msg)
                        else:
                             msg = f"📸 YENİ GÖNDERİ!\n📝: {caption_txt}\nLink: https://instagram.com/p/{m.code}"
                             # Konum Var mı?
                             if m.location:
                                 msg += f"\n📍 Konum: {m.location.name} (https://maps.google.com/?q={m.location.lat},{m.location.lng})"
                             send_telegram_message(msg)
                    else:
                        # B. CAPTION (AÇIKLAMA) DEĞİŞİKLİĞİ
                        old_caption = old_media_map[m_id].get("caption", "")
                        new_caption = m.caption_text if m.caption_text else ""
                        if old_caption != new_caption:
                            send_telegram_message(f"✏️ AÇIKLAMA DÜZENLENDİ!\nPost: https://instagram.com/p/{m.code}\nEski: {old_caption}\nYeni: {new_caption}")

                # C. SİLİNEN GÖNDERİ KONTROLÜ
                # Eğer eski listemizde olan bir gönderi, yeni çektiğimiz 20'lik listede yoksa...
                # DİKKAT: Gönderi 20. sıradan geriye düştüğü için de listede olmayabilir. 
                # O yüzden silindi demek için "yakın zamanda atılmış" olması lazım.
                # (Basitlik için bu kısmı sadece 'Eğer son 5 gönderiden biriyse ve kaybolduysa' diye kısıtlayabiliriz ama karmaşıklaşır.
                # Şimdilik pas geçiyorum, çok false positive verir.)

                # D. FLÖRT / YORUM TESPİTİ (Son 3 gönderiye bak)
                # Sadece alev, kalp gibi emojileri arayalım
                recent_medias = medias[:3]
                for m in recent_medias:
                    try:
                        comments = cl.media_comments(m.pk, amount=20)
                        flirt_emojis = ["🔥", "😍", "❤️", "😘", "🥰", "🥵"]
                        for c in comments:
                            # Kendi yorumu değilse ve emoji içeriyorsa
                            if str(c.user.pk) != str(user_id) and any(e in c.text for e in flirt_emojis):
                                # Bu yorumu daha önce bildirdik mi? (Basit bir check lazım yoksa spamlar)
                                # Veritabanı şişmesin diye burayı şimdilik sadece konsola yazıyorum.
                                # Telegram'a açmak istersen alttaki satırı aç:
                                # send_telegram_message(f"💬 FLÖRT UYARISI!\n{c.user.username}, şu posta şunu yazdı: {c.text}\nLink: https://instagram.com/p/{m.code}")
                                pass
                    except:
                        pass

                # Veritabanını güncelle (Sadece gerekli alanları kaydet)
                new_media_save = {}
                for m_id, m in curr_media_map.items():
                    new_media_save[m_id] = {
                        "caption": m.caption_text if m.caption_text else "",
                        "code": m.code,
                        "taken_at": m.taken_at.timestamp()
                    }
                data["medias"] = new_media_save

            except Exception as e:
                print(f"Medya işlem hatası: {e}")

            # ==========================================================
            # 4. HIGHLIGHTS (ÖNE ÇIKANLAR)
            # ==========================================================
            try:
                highlights = cl.user_highlights(user_id)
                curr_high_ids = [str(h.pk) for h in highlights]
                old_high_ids = data.get("highlights", [])
                
                new_highs = set(curr_high_ids) - set(old_high_ids)
                if new_highs:
                    send_telegram_message(f"⭐ YENİ ÖNE ÇIKAN!\nProfile yeni bir highlight eklendi.")
                
                data["highlights"] = curr_high_ids
            except:
                pass

            # ==========================================================
            # 5. TAKİPÇİ KONTROLÜ (1 SAATTE BİR)
            # ==========================================================
            if current_time - last_follower_check_time >= FOLLOWER_CHECK_INTERVAL:
                print("⏳ Takipçi listesi kontrol ediliyor...")
                try:
                    curr_followers = cl.user_followers(user_id)
                    curr_following = cl.user_following(user_id)
                    
                    curr_followers_ids = list(curr_followers.keys())
                    curr_following_ids = list(curr_following.keys())
                    
                    old_followers_ids = data.get("followers", [])
                    old_following_ids = data.get("following", [])
                    
                    if old_followers_ids:
                        # Yeni Gelen
                        new_followers = set(curr_followers_ids) - set(old_followers_ids)
                        for uid in new_followers:
                            u = curr_followers[uid]
                            send_telegram_message(f"🚨 YENİ TAKİPÇİ: {u.username} ({u.full_name})")

                        # Yeni Giden (Takip Ettiği)
                        new_following = set(curr_following_ids) - set(old_following_ids)
                        for uid in new_following:
                            u = curr_following[uid]
                            send_telegram_message(f"👀 YENİ TAKİP ETTİ: {u.username}\nLink: https://instagram.com/{u.username}")

                    data["followers"] = curr_followers_ids
                    data["following"] = curr_following_ids
                    last_follower_check_time = current_time
                except Exception as e:
                    print(f"Takipçi hata: {e}")

            # VERİYİ KAYDET
            save_data(data)
            print(f"Tur bitti. {MEDIA_CHECK_INTERVAL} saniye bekleniyor.")

        except Exception as e:
            print(f"GENEL HATA: {e}")
            time.sleep(60)
        
        time.sleep(MEDIA_CHECK_INTERVAL)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
