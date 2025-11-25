import time
import json
import os
import threading
import requests
from flask import Flask
from datetime import datetime

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 RÖNTGEN MODU AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ALL_KEYS = [
    "524ea9ed97mshea5622f7563ab91p1c8a9bjsn4393885af79a",
    "5afb01f5damsh15c163415ce684bp176beajsne525580cab71",
    "fb54b1e3f9mshc8855c0c68842e0p11dc99jsndc587166854b",
    "053bbb3bcfmshbd34360e5e5e514p11d706jsn762810d7d191",
    "61cdb62a77mshfad122b72ee12d1p16a999jsn80009ce41384",
    "e483ba3acamsh9304acbeffe26efp1f9e8ajsnabfb0e96a849",
    "89b8e89b68mshde52c44e2beffadp17f4b4jsn35a7d495e79e",
    "9db69421afmsh66f9eb3366b0aaep1578a5jsn4fd5350732fb",
    "98904adf97msh4ddedb72dcf0c6cp1debbejsn8f999318384b"
]

HOST_BASIC = "instagram120.p.rapidapi.com"             
HOST_PREMIUM = "instagram-best-experience.p.rapidapi.com" 
CHECK_INTERVAL = 900

def get_time_str():
    return datetime.now().strftime("%H:%M %d.%m.%Y")

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message, "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

# --- BASIC API ---
# Hem userInfo hem profile endpointini dener
def call_basic_api_raw(payload_dict):
    endpoints = ["/api/instagram/userInfo", "/api/instagram/profile"]
    
    for endpoint in endpoints:
        url = f"https://{HOST_BASIC}{endpoint}"
        for i, key in enumerate(ALL_KEYS):
            try:
                headers = {
                    "x-rapidapi-key": key,
                    "x-rapidapi-host": HOST_BASIC,
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json=payload_dict, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    return response.json() # Ham veriyi döndür
                
            except: continue
            
    return None

# --- PREMIUM API ---
def call_premium_api(endpoint_type, user_id):
    url = f"https://{HOST_PREMIUM}/{endpoint_type}"
    for i, key in enumerate(ALL_KEYS):
        try:
            querystring = {"user_id": str(user_id)}
            headers = {
                "x-rapidapi-key": key,
                "x-rapidapi-host": HOST_PREMIUM
            }
            response = requests.get(url, headers=headers, params=querystring, timeout=15)
            if response.status_code == 200: return response.json()
        except: continue
    return None

# --- PARSE ---
def parse_basic_profile(data):
    # Önceki sağlam mantık
    try:
        # İHTİMAL 1: result -> [0] -> user
        if "result" in data and isinstance(data["result"], list) and len(data["result"]) > 0:
            user_obj = data["result"][0].get("user")
            if user_obj: return user_obj
            
        # İHTİMAL 2: data -> user
        if "data" in data:
            if "user" in data["data"]: return data["data"]["user"]
            return data["data"]
            
        # İHTİMAL 3: user
        if "user" in data: return data["user"]
        
    except: pass
    return None

# --- KOMUTLAR ---
def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} aranıyor (Röntgen Modu)...", chat_id)
    
    # Ham veriyi çek
    raw_data = call_basic_api_raw({"username": TARGET_USERNAME})
    
    if not raw_data:
        send_telegram_message("❌ Hiçbir API yanıt vermedi.", chat_id)
        return

    # Parse etmeye çalış
    user_obj = parse_basic_profile(raw_data)
    
    if user_obj:
        # Başarılıysa yaz
        fol = user_obj.get('follower_count', 0)
        fng = user_obj.get('following_count', 0)
        send_telegram_message(f"📊 BAŞARILI:\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
    else:
        # BAŞARISIZSA HAM VERİYİ GÖSTER (HATA AYIKLAMA)
        json_str = json.dumps(raw_data, indent=2)
        # Mesaj çok uzunsa kes
        msg = f"⚠️ FORMAT HATASI! Gelen Veri Şöyle:\n\n{json_str[:3500]}"
        send_telegram_message(msg, chat_id)

# --- STORY (Bu zaten çalışıyor ama kalsın) ---
def handle_story(chat_id):
    url = f"https://{HOST_BASIC}/api/instagram/stories"
    payload = {"username": TARGET_USERNAME}
    
    for key in ALL_KEYS:
        try:
            headers = {"x-rapidapi-key": key, "x-rapidapi-host": HOST_BASIC, "Content-Type": "application/json"}
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                sl = data.get('result', [])
                send_telegram_message(f"🔥 {len(sl)} Adet Hikaye Var.", chat_id)
                return
        except: continue
    send_telegram_message("❌ Story verisi alınamadı.", chat_id)

# --- LOOP ---
def bot_loop():
    print("🚀 RÖNTGEN MODU BAŞLATILDI")
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
                    
                    if "/takipci" in text:
                        handle_takipci(chat_id)
                    elif "/story" in text:
                        handle_story(chat_id)
        except:
            time.sleep(1)
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
