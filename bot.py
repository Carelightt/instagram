import time
import json
import os
import threading
import requests
from flask import Flask

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 USERINFO MODU AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 7 ANAHTAR (Aynı kalıyor)
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

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def call_rapid_api(endpoint, payload_dict, chat_id=None):
    url = f"https://{RAPID_HOST}{endpoint}"
    
    for i, key in enumerate(API_KEYS):
        try:
            headers = {
                "x-rapidapi-key": key,
                "x-rapidapi-host": RAPID_HOST,
                "Content-Type": "application/json"
            }
            # Timeout 10 saniye
            response = requests.post(url, json=payload_dict, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            if response.status_code == 429:
                continue

            # Diğer hataları logla ama kullanıcıyı boğma
            print(f"Key {i+1} Hata: {response.status_code}")
            continue

        except Exception as e:
            print(f"Key {i+1} Bağlantı: {e}")
            continue

    if chat_id: send_telegram_message("🚫 TÜM ANAHTARLAR DENENDİ, VERİ YOK!", chat_id)
    return None

def load_data():
    if not os.path.exists("data.json"): return {}
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

# --- VERİ AYIKLAMA (PARSING) ---
def parse_instagram_data(data):
    """
    Senin attığın JSON yapısına göre veriyi cımbızla çeker.
    Yol: result -> [0] -> user -> follower_count
    """
    try:
        # 1. Katman: result listesi
        result_list = data.get('result', [])
        if not result_list or len(result_list) == 0:
            return None
        
        # 2. Katman: Listenin ilk elemanı
        first_item = result_list[0]
        
        # 3. Katman: user objesi
        user_obj = first_item.get('user')
        if not user_obj:
            return None
            
        # 4. Katman: Hedef veriler
        return {
            "followers": user_obj.get('follower_count', 0),
            "following": user_obj.get('following_count', 0),
            "full_name": user_obj.get('full_name', TARGET_USERNAME),
            "bio": user_obj.get('biography', ""),
            "posts": user_obj.get('media_count', 0),
            "is_private": user_obj.get('is_private', False)
        }
    except Exception as e:
        print(f"Parse Hatası: {e}")
        return None

# --- KOMUTLAR ---
def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} (UserInfo) çekiliyor...", chat_id)
    
    # SENİN BULDUĞUN DOĞRU ENDPOINT
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME}, chat_id)
    
    if data:
        # Veriyi cımbızla çekelim
        parsed = parse_instagram_data(data)
        
        if not parsed:
            # Ham veriyi görelim ki hata neredeymiş anlayalım
            debug_cut = str(data)[:500]
            send_telegram_message(f"❌ Veri yapısı bozuk veya kullanıcı yok.\nGelen: {debug_cut}", chat_id)
            return

        fol = parsed["followers"]
        fng = parsed["following"]
        name = parsed["full_name"]
        
        send_telegram_message(f"📊 RAPOR ({name}):\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
        
        d = load_data()
        d["followers"] = fol
        d["following"] = fng
        save_data(d)
    else:
        # call_rapid_api zaten hata mesajı atıyor
        pass

def handle_story(chat_id):
    send_telegram_message("🔍 Hikaye kontrol...", chat_id)
    data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME}, chat_id)
    
    if data:
        # Story yapısı da genelde result listesi içindedir
        sl = data.get('result', [])
        count = len(sl)
        
        if count > 0:
            send_telegram_message(f"🔥 {count} Adet Aktif Hikaye Var!", chat_id)
        else:
            send_telegram_message("ℹ️ Aktif hikaye yok.", chat_id)
        
        d = load_data()
        d["latest_story_count"] = count
        save_data(d)
    else:
        pass

# --- OTOMATİK KONTROL ---
def check_full_status():
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    if data:
        parsed = parse_instagram_data(data)
        if parsed:
            fol = parsed["followers"]
            old = load_data().get("followers", 0)
            
            if fol != old and old != 0:
                diff = fol - old
                emoji = "🟢" if diff > 0 else "🔴"
                send_telegram_message(f"{emoji} TAKİPÇİ DEĞİŞTİ!\nYeni: {fol} ({diff:+})")
            
            # Veriyi güncelle
            d = load_data()
            d["followers"] = fol
            save_data(d)

# --- BOT DÖNGÜSÜ ---
def bot_loop():
    print("🚀 USERINFO MODU BAŞLATILDI")
    last_update_id = 0
    last_auto_check = time.time()

    while True:
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
                        
        except Exception:
            time.sleep(1)
        
        if time.time() - last_auto_check >= CHECK_INTERVAL:
            check_full_status()
            last_auto_check = time.time()
        
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
