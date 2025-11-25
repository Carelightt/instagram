import time
import json
import http.client
import os
import threading
import requests
from flask import Flask

# --- FLASK (Render İçin) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 7-MOTORLU DEV BOT AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🔥 7 ADET API ANAHTARI (Sırayla dener)
API_KEYS = [
    "524ea9ed97mshea5622f7563ab91p1c8a9bjsn4393885af79a", # Key 1
    "5afb01f5damsh15c163415ce684bp176beajsne525580cab71", # Key 2
    "fb54b1e3f9mshc8855c0c68842e0p11dc99jsndc587166854b", # Key 3
    "053bbb3bcfmshbd34360e5e5e514p11d706jsn762810d7d191", # Key 4
    "61cdb62a77mshfad122b72ee12d1p16a999jsn80009ce41384", # Key 5
    "e483ba3acamsh9304acbeffe26efp1f9e8ajsnabfb0e96a849", # Key 6
    "89b8e89b68mshde52c44e2beffadp17f4b4jsn35a7d495e79e"  # Key 7
]
RAPID_HOST = "instagram120.p.rapidapi.com"

# ⚡ SÜRE AYARI: 25 Dakika (1500 Saniye)
# 7000 istek / 4 = 1750 Tur.
# 1750 / 30 Gün = Günde ~58 Tur.
# 24 Saat / 58 = ~24.8 Dakika. (25 dk güvenli)
CHECK_INTERVAL = 1500 

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

# --- AKILLI ROTASYONLU API İSTEK FONKSİYONU ---
def call_rapid_api(endpoint, payload_dict):
    # Anahtarları sırayla dene
    for i, key in enumerate(API_KEYS):
        try:
            conn = http.client.HTTPSConnection(RAPID_HOST)
            payload = json.dumps(payload_dict)
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': RAPID_HOST,
                'Content-Type': "application/json"
            }
            conn.request("POST", endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            # Yanıtı çözümle
            json_data = json.loads(data.decode("utf-8"))
            
            # Eğer hata mesajı varsa (mesela limit dolduysa)
            if isinstance(json_data, dict) and "message" in json_data and "exceeded" in str(json_data["message"]):
                print(f"⚠️ Anahtar {i+1} Limiti Doldu. Diğerine geçiliyor...")
                continue # Döngüye devam et, sıradaki anahtarı dene
            
            # Başarılıysa veriyi döndür (ve döngüden çık)
            return json_data

        except Exception as e:
            print(f"Bağlantı hatası (Key {i+1}): {e}")
            continue # Hata varsa diğer anahtarı dene

    # Hiçbir anahtar çalışmazsa
    print("❌ KRİTİK: TÜM 7 ANAHTAR DA DENENDİ, HEPSİ BAŞARISIZ!")
    return None

# --- VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists("data.json"):
        return {"followers": 0, "following": 0, "bio": "", "posts_count": 0, "highlight_count": 0, "latest_story_count": 0}
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

# --- KONTROL MEKANİZMASI ---
def check_instagram_status(manual_check=False, chat_id=None):
    print("🕵️‍♂️ Kontrol yapılıyor...")
    
    # 1. PROFİL
    user_data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    
    if not user_data:
        if manual_check: send_telegram_message("❌ Sistem Hatası: Veri alınamadı (API Sorunu).", chat_id)
        return

    try:
        result = user_data if 'username' in user_data else user_data.get('result') or user_data.get('data')
        
        # Bazen API boş dönerse
        if not result:
            if manual_check: send_telegram_message("❌ Kullanıcı verisi boş döndü.", chat_id)
            return

        curr_followers = result.get('follower_count', 0)
        curr_following = result.get('following_count', 0)
        curr_bio = result.get('biography', "")
        curr_posts_count = result.get('media_count', 0)
        
        old_data = load_data()
        messages = []
        
        # Analizler
        diff_fol = curr_followers - old_data.get("followers", 0)
        if diff_fol != 0 and old_data.get("followers", 0) != 0:
            emoji = "🟢" if diff_fol > 0 else "🔴"
            messages.append(f"{emoji} Takipçi: {curr_followers} ({diff_fol:+})")
            
        diff_fng = curr_following - old_data.get("following", 0)
        if diff_fng != 0 and old_data.get("following", 0) != 0:
            emoji = "👀" if diff_fng > 0 else "🔻"
            messages.append(f"{emoji} Takip Edilen: {curr_following} ({diff_fng:+})")

        if curr_bio != old_data.get("bio", "") and old_data.get("bio", "") != "":
            messages.append(f"📝 Biyo Değişti!\nYeni: {curr_bio}")

        if curr_posts_count > old_data.get("posts_count", 0) and old_data.get("posts_count", 0) != 0:
            messages.append(f"📸 YENİ GÖNDERİ! (Toplam: {curr_posts_count})")
        
        # 2. HİKAYE
        story_data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME})
        curr_story_count = 0
        if story_data:
            stories_list = story_data if isinstance(story_data, list) else story_data.get('result', []) or story_data.get('data', [])
            curr_story_count = len(stories_list)
            if curr_story_count > old_data.get("latest_story_count", 0):
                messages.append(f"🔥 YENİ HİKAYE! (Aktif: {curr_story_count})")
        
        # 3. ÖNE ÇIKANLAR
        hl_data = call_rapid_api("/api/instagram/highlights", {"username": TARGET_USERNAME})
        curr_hl_count = 0
        if hl_data:
            hl_list = hl_data if isinstance(hl_data, list) else hl_data.get('result', []) or hl_data.get('data', [])
            curr_hl_count = len(hl_list)
            if curr_hl_count > old_data.get("highlight_count", 0) and old_data.get("highlight_count", 0) != 0:
                messages.append(f"⭐ YENİ HIGHLIGHT! (Toplam: {curr_hl_count})")

        # Gönderim
        if messages:
            full_msg = f"🚨 {TARGET_USERNAME} RAPORU:\n" + "\n".join(messages)
            send_telegram_message(full_msg, chat_id)
        elif manual_check:
            # 7 Keyimiz olduğu için artık korkmadan detaylı rapor verebiliriz
            send_telegram_message(f"✅ Durum Stabil.\nTakipçi: {curr_followers}\nTakip Edilen: {curr_following}\nHikaye: {curr_story_count}", chat_id)

        # Kaydet
        new_data = {
            "followers": curr_followers,
            "following": curr_following,
            "bio": curr_bio,
            "posts_count": curr_posts_count,
            "highlight_count": curr_hl_count,
            "latest_story_count": curr_story_count
        }
        save_data(new_data)
        
    except Exception as e:
        print(f"Analiz Hatası: {e}")
        if manual_check: send_telegram_message(f"⚠️ Hata: {e}", chat_id)

def bot_loop():
    print("🚀 7 Motorlu Mod Başlatıldı...")
    last_update_id = 0
    last_auto_check = time.time()

    while True:
        current_time = time.time()
        
        # Telegram Komutları (/kontrol vs.)
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            resp = requests.get(tg_url).json()
            if resp.get("ok"):
                for result in resp["result"]:
                    last_update_id = result["update_id"]
                    message = result.get("message", {})
                    text = message.get("text", "").lower()
                    chat_id = message.get("chat", {}).get("id")
                    
                    if "/kontrol" in text:
                        send_telegram_message("🏎️ Manuel kontrol (7 Key devrede)...", chat_id)
                        check_instagram_status(manual_check=True, chat_id=chat_id)
        except:
            pass
        
        # Otomatik Kontrol (25 Dakikada bir)
        if current_time - last_auto_check >= CHECK_INTERVAL:
            check_instagram_status(manual_check=False)
            last_auto_check = current_time
        
        time.sleep(5)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
