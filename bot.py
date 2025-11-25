import time
import json
import os
import threading
import requests
import http.client
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 KONUŞKAN BOT AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# AYARLAR
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
        # Timeout'u kısa tutalım ki mesaj atarken bot donmasın
        requests.post(url, data=data, timeout=3)
    except:
        pass

def call_rapid_api(endpoint, payload_dict, chat_id=None):
    payload = json.dumps(payload_dict)
    
    for i, key in enumerate(API_KEYS):
        try:
            # Kullanıcıya bilgi ver (Bunu normalde yapmayız ama debug için şart)
            if chat_id: 
                # Sadece mesajı düzenlemek yerine yeni mesaj atalım ki akışı gör
                # Çok spam olmasın diye sadece hata alırsak yazdıracağız aşağıda
                pass

            conn = http.client.HTTPSConnection(RAPID_HOST, timeout=5) # 5 Saniye Timeout!
            
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': RAPID_HOST,
                'Content-Type': "application/json"
            }
            
            conn.request("POST", endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            try:
                json_data = json.loads(data.decode("utf-8"))
            except:
                if chat_id: send_telegram_message(f"⚠️ Key {i+1}: Veri bozuk geldi (JSON değil).", chat_id)
                continue

            # BAŞARILI DURUM
            if res.status == 200:
                return json_data
            
            # HATA DURUMLARI
            error_msg = json_data.get("message", "Bilinmeyen Hata")
            
            # Eğer kullanıcı bulunamadıysa DİĞER KEYLERİ DENEME, DİREKT ÇIK.
            # Çünkü kullanıcı yoksa 100 tane key de olsa bulamaz.
            if res.status == 404 or "Not Found" in str(error_msg):
                if chat_id: send_telegram_message(f"❌ KULLANICI BULUNAMADI! ({TARGET_USERNAME})", chat_id)
                return None

            if chat_id: send_telegram_message(f"⚠️ Key {i+1} Başarısız: {res.status} - {error_msg}", chat_id)
            continue

        except Exception as e:
            if chat_id: send_telegram_message(f"⚠️ Key {i+1} Bağlantı Hatası: {str(e)}", chat_id)
            continue

    if chat_id: send_telegram_message("🚫 TÜM ANAHTARLAR DENENDİ, SONUÇ YOK!", chat_id)
    return None

# ... (Load/Save Data kısıımları aynı) ...
def load_data():
    if not os.path.exists("data.json"): return {}
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

# --- KOMUTLAR ---
def handle_debug(chat_id):
    send_telegram_message("🧪 Test isteği atılıyor...", chat_id)
    # Test için 'instagram' kullanıcısını deniyoruz, çünkü kesin var.
    data = call_rapid_api("/api/instagram/userInfo", {"username": "instagram"}, chat_id)
    if data:
        send_telegram_message("✅ API TEST BAŞARILI! (Instagram hesabı çekildi)", chat_id)
    else:
        send_telegram_message("❌ API TEST BAŞARISIZ.", chat_id)

def handle_takipci(chat_id):
    send_telegram_message(f"🔍 Hedef: {TARGET_USERNAME} aranıyor...", chat_id)
    
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME}, chat_id)
    
    if data:
        # API bazen 'result', bazen 'data' döndürür, kontrol edelim
        print(f"Gelen Veri: {data}") # Loga bas
        res = data if 'username' in data else data.get('result') or data.get('data')
        
        if not res:
            send_telegram_message(f"❌ API cevap döndü ama içi boş! Kullanıcı adı yanlış olabilir mi? ({TARGET_USERNAME})", chat_id)
            return

        fol = res.get('follower_count', 0)
        fng = res.get('following_count', 0)
        name = res.get('full_name', target_username)
        
        send_telegram_message(f"📊 RAPOR ({name}):\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
        
        d = load_data()
        d["followers"] = fol
        d["following"] = fng
        save_data(d)
    else:
        # Buraya düşerse call_rapid_api zaten hata mesajı atmış demektir
        pass

# --- LOOP ---
def bot_loop():
    print("🚀 GEVEZE MOD BAŞLATILDI")
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
