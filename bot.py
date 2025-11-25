import time
import json
import os
import threading
import requests
import http.client # <-- Senin attığın örnekteki kütüphane
from flask import Flask

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 NATIVE-CLIENT BOT AKTİF!"

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

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

# --- SENİN ATTIĞIN ÖRNEK KOD YÖNTEMİ (HTTP.CLIENT) ---
def call_rapid_api(endpoint, payload_dict, chat_id=None):
    # Payload'ı stringe çevir (API böyle istiyor)
    payload = json.dumps(payload_dict)
    
    for i, key in enumerate(API_KEYS):
        try:
            conn = http.client.HTTPSConnection(RAPID_HOST, timeout=10)
            
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': RAPID_HOST,
                'Content-Type': "application/json"
            }
            
            conn.request("POST", endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            # Yanıtı çözümle
            try:
                decoded_data = data.decode("utf-8")
                json_data = json.loads(decoded_data)
            except:
                if chat_id: send_telegram_message(f"⚠️ JSON Hatası (Key {i+1}): Veri bozuk geldi.", chat_id)
                continue

            # API Hata Kontrolü
            if res.status != 200:
                error_msg = json_data.get("message", "Bilinmeyen Hata")
                # Eğer limit dolduysa diğer keye geç
                if "exceeded" in str(error_msg) or res.status == 429:
                    continue 
                # Eğer yetki yoksa (401/403)
                if res.status == 403 or res.status == 401:
                    if chat_id: send_telegram_message(f"⚠️ Key {i+1} Yetkisiz (Abone olunmamış olabilir).", chat_id)
                    continue
                
                # Diğer hatalar
                if chat_id: send_telegram_message(f"⚠️ API Hatası (Key {i+1}): {res.status} - {error_msg}", chat_id)
                continue

            return json_data

        except Exception as e:
            if chat_id: send_telegram_message(f"❌ Bağlantı Hatası (Key {i+1}): {str(e)}", chat_id)
            continue

    if chat_id: send_telegram_message("🚫 TÜM ANAHTARLAR DENENDİ VE BAŞARISIZ OLDU!", chat_id)
    return None

# --- VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists("data.json"):
        return {"followers": 0, "following": 0}
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

# --- KOMUTLAR ---
def handle_debug(chat_id):
    msg = "🛠️ DEBUG RAPORU:\n"
    msg += f"Target: {TARGET_USERNAME}\n"
    msg += f"Keys: {len(API_KEYS)} adet\n"
    msg += f"Host: {RAPID_HOST}\n"
    send_telegram_message(msg, chat_id)
    
    # Test isteği
    send_telegram_message("🧪 Test isteği atılıyor...", chat_id)
    data = call_rapid_api("/api/instagram/userInfo", {"username": "instagram"}, chat_id) # Test için 'instagram' kullanıyoruz
    if data:
        send_telegram_message("✅ API TEST BAŞARILI! Erişim var.", chat_id)
    else:
        send_telegram_message("❌ API TEST BAŞARISIZ.", chat_id)

def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} analiz ediliyor...", chat_id)
    
    # UserInfo isteği
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME}, chat_id)
    
    if data:
        # Veriyi bul
        res = data if 'username' in data else data.get('result') or data.get('data')
        
        if not res:
            send_telegram_message(f"❌ Kullanıcı bulunamadı veya veri boş. (Gelen: {str(data)[:100]})", chat_id)
            return

        fol = res.get('follower_count', 0)
        fng = res.get('following_count', 0)
        
        send_telegram_message(f"📊 SONUÇ:\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
        
        # Kaydet
        d = load_data()
        d["followers"] = fol
        d["following"] = fng
        save_data(d)
    else:
        send_telegram_message("❌ Veri çekilemedi (Tüm keyler denendi).", chat_id)

# --- BOT LOOP ---
def bot_loop():
    print("🚀 NATIVE MOD BAŞLATILDI")
    last_update_id = 0

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
                    
                    if "/debug" in text:
                        handle_debug(chat_id)
                    elif "/takipci" in text:
                        handle_takipci(chat_id)
                        
        except Exception as e:
            print(f"Telegram Hatası: {e}")
            time.sleep(2)
        
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
