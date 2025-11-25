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
    return "🚀 REQUESTS NATIVE MOD AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 7 ADET ANAHTARIN
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

# --- SENİN ATTIĞIN ÖRNEK KOD YAPISI ---
def call_rapid_api(endpoint, payload_dict):
    url = f"https://{RAPID_HOST}{endpoint}"
    
    # 7 Anahtarı Sırayla Dene
    for i, key in enumerate(API_KEYS):
        try:
            # Senin attığın headers yapısının AYNISI
            headers = {
                "x-rapidapi-key": key,
                "x-rapidapi-host": RAPID_HOST,
                "Content-Type": "application/json"
            }
            
            # Senin attığın requests yapısının AYNISI (json=payload kullanıyoruz)
            # Timeout ekledim ki donmasın (10 sn)
            response = requests.post(url, json=payload_dict, headers=headers, timeout=10)
            
            # 1. Bağlantı Başarılı mı? (200 OK)
            if response.status_code == 200:
                return response.json()
            
            # 2. Limit Dolduysa (429) -> Diğer keye geç
            if response.status_code == 429:
                print(f"⚠️ Key {i+1} Limit Doldu. Sıradakine geçiliyor...")
                continue

            # 3. Diğer Hatalar (Loglayıp devam edelim)
            print(f"⚠️ API Hatası (Key {i+1}): {response.status_code} - {response.text}")
            continue

        except Exception as e:
            print(f"❌ Bağlantı Hatası (Key {i+1}): {e}")
            continue

    print("❌ TÜM ANAHTARLAR DENENDİ, SONUÇ YOK!")
    return None

# --- DATA YÖNETİMİ ---
def load_data():
    if not os.path.exists("data.json"): return {}
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

# --- KOMUT İŞLEYİCİLERİ ---
def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} analiz ediliyor...", chat_id)
    
    # API Çağrısı
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    
    if data:
        # API bazen direkt data, bazen result döner. Garantileyelim.
        res = data if 'username' in data else data.get('result') or data.get('data')
        
        if not res:
            send_telegram_message(f"❌ Kullanıcı Bulunamadı! (Veri boş)", chat_id)
            return

        fol = res.get('follower_count', 0)
        fng = res.get('following_count', 0)
        name = res.get('full_name', TARGET_USERNAME)
        
        send_telegram_message(f"📊 RAPOR ({name}):\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
        
        # Kaydet
        d = load_data()
        d["followers"] = fol
        d["following"] = fng
        save_data(d)
    else:
        send_telegram_message("❌ Veri çekilemedi (Tüm keyler hata verdi).", chat_id)

def handle_story(chat_id):
    send_telegram_message("🔍 Hikaye kontrol...", chat_id)
    data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    
    if data:
        sl = data if isinstance(data, list) else data.get('result', []) or data.get('data', [])
        count = len(sl)
        if count > 0:
            send_telegram_message(f"🔥 {count} Adet Aktif Hikaye Var!", chat_id)
        else:
            send_telegram_message("ℹ️ Aktif hikaye yok.", chat_id)
        
        d = load_data()
        d["latest_story_count"] = count
        save_data(d)
    else:
        send_telegram_message("❌ Veri çekilemedi.", chat_id)

# --- OTOMATİK KONTROL ---
def check_full_status():
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    if data:
        res = data if 'username' in data else data.get('result') or data.get('data')
        if res:
            fol = res.get('follower_count', 0)
            old = load_data().get("followers", 0)
            if fol != old and old != 0:
                diff = fol - old
                send_telegram_message(f"🚨 TAKİPÇİ DEĞİŞTİ!\nYeni: {fol} ({diff:+})")
                save_data({"followers": fol})

# --- BOT DÖNGÜSÜ ---
def bot_loop():
    print("🚀 REQUESTS MODU BAŞLATILDI")
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
                        
        except Exception as e:
            print(f"Loop Hatası: {e}")
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
