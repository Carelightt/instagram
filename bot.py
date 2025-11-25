import time
import json
import os
import threading
import requests
import sys
from flask import Flask

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 DEBUG MODU AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

API_KEYS = [
    "524ea9ed97mshea5622f7563ab91p1c8a9bjsn4393885af79a",
    "5afb01f5damsh15c163415ce684bp176beajsne525580cab71",
    "fb54b1e3f9mshc8855c0c68842e0p11dc99jsndc587166854b",
    "053bbb3bcfmshbd34360e5e5e514p11d706jsn762810d7d191",
    "61cdb62a77mshfad122b72ee12d1p16a999jsn80009ce41384",
    "e483ba3acamsh9304acbeffe26efp1f9e8ajsnabfb0e96a849",
    "89b8e89b68mshde52c44e2beffadp17f4b4jsn35a7d495e79e"
]
RAPID_HOST = "instagram120.p.rapidapi.com"
CHECK_INTERVAL = 1500 

def log(message):
    """Logları anında ekrana basan fonksiyon"""
    print(message, flush=True)

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data, timeout=5)
    except:
        pass

def call_rapid_api(endpoint, payload_dict):
    url = f"https://{RAPID_HOST}{endpoint}"
    
    # Eğer hedef kullanıcı adı yoksa hata ver
    if not payload_dict.get("username"):
        log("❌ HATA: TARGET_USERNAME Environment Variable ayarlanmamış!")
        return None

    for i, key in enumerate(API_KEYS):
        log(f"🔄 [Key {i+1}] deneniyor... ({endpoint})")
        try:
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': RAPID_HOST,
                'Content-Type': "application/json"
            }
            
            # Timeout 3 saniye yapıldı (Hızlı geçiş için)
            response = requests.post(url, json=payload_dict, headers=headers, timeout=3)
            
            log(f"📡 [Key {i+1}] Kod: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                log(f"⚠️ [Key {i+1}] Limiti dolmuş.")
                continue
            else:
                log(f"⚠️ [Key {i+1}] Hata: {response.text}")
                continue

        except Exception as e:
            log(f"❌ [Key {i+1}] Bağlantı Hatası: {e}")
            continue

    log("❌❌ TÜM KEYLER BAŞARISIZ OLDU!")
    return None

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

def check_full_status(manual=False, chat_id=None):
    log("🕵️‍♂️ Full kontrol başlıyor...")
    
    user_data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    if not user_data: 
        if manual: send_telegram_message("❌ Veri alınamadı (API Hatası).", chat_id)
        return

    result = user_data if 'username' in user_data else user_data.get('result') or user_data.get('data')
    if not result: 
        if manual: send_telegram_message("❌ API boş veri döndü.", chat_id)
        return

    curr_fol = result.get('follower_count', 0)
    curr_fng = result.get('following_count', 0)
    
    # ... (Diğer analiz kodları aynı) ...
    if manual:
        send_telegram_message(f"✅ VERİ GELDİ!\nTakipçi: {curr_fol}\nTakip Edilen: {curr_fng}", chat_id)

    # Basitlik için sadece sayıları güncelleyelim testte
    save_data({"followers": curr_fol, "following": curr_fng})

def handle_takipci(chat_id):
    send_telegram_message("🔍 Hızlı kontrol (3sn timeout)...", chat_id)
    log("--- Takipçi Komutu İşleniyor ---")
    
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    
    if data:
        res = data if 'username' in data else data.get('result') or data.get('data')
        fol = res.get('follower_count', 0)
        fng = res.get('following_count', 0)
        send_telegram_message(f"📊 RAPOR:\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
        log(f"✅ Başarılı: {fol} takipçi.")
    else:
        send_telegram_message("❌ Hiçbir API anahtarı çalışmadı. Loglara bak.", chat_id)

def handle_story(chat_id):
    send_telegram_message("🔍 Story kontrol...", chat_id)
    data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    if data:
        sl = data if isinstance(data, list) else data.get('result', []) or data.get('data', [])
        count = len(sl)
        if count > 0:
            send_telegram_message(f"🔥 {count} hikaye var.", chat_id)
        else:
            send_telegram_message("ℹ️ Hikaye yok.", chat_id)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

def bot_loop():
    log("🚀 DEBUG MODU BAŞLATILDI")
    last_update_id = 0
    last_auto_check = time.time()

    while True:
        current_time = time.time()
        
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            resp = requests.get(tg_url, timeout=10).json()
            if resp.get("ok"):
                for result in resp["result"]:
                    last_update_id = result["update_id"]
                    message = result.get("message", {})
                    text = message.get("text", "").lower()
                    chat_id = message.get("chat", {}).get("id")
                    
                    if "/takipci" in text:
                        handle_takipci(chat_id)
                    elif "/story" in text:
                        handle_story(chat_id)
        except Exception as e:
            pass # Telegram hatası logu kirletmesin
        
        if current_time - last_auto_check >= CHECK_INTERVAL:
            check_full_status(manual=False)
            last_auto_check = current_time
        
        time.sleep(5)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
