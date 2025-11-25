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
    return "🚀 9 MOTORLU TAM FORMAT BOT AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🔥 9 ADET ANAHTAR
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

# API ADRESLERİ
HOST_BASIC = "instagram120.p.rapidapi.com"             
HOST_PREMIUM = "instagram-best-experience.p.rapidapi.com" 

# OTOMATİK KONTROL SIKLIĞI: 15 Dakika (900 Saniye)
CHECK_INTERVAL = 900

def get_time_str():
    # Format: Saat:Dakika Gün.Ay.Yıl (Örn: 14:30 25.11.2025)
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

# --- BASIC API (Sayılar) ---
def call_basic_api(endpoint, payload_dict):
    url = f"https://{HOST_BASIC}{endpoint}"
    for i, key in enumerate(ALL_KEYS):
        try:
            headers = {
                "x-rapidapi-key": key,
                "x-rapidapi-host": HOST_BASIC,
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload_dict, headers=headers, timeout=10)
            if response.status_code == 200: return response.json()
            if response.status_code == 429: continue
        except: continue
    return None

# --- PREMIUM API (Listeler) ---
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
            if response.status_code == 429: continue 
            if response.status_code == 403: continue

        except: continue
    return None

# --- VERİ İŞLEME ---
def load_data():
    if not os.path.exists("data.json"): 
        return {
            "user_id": None,
            "followers_count": 0, 
            "following_count": 0,
            "followers_list": [],
            "following_list": [],
            "posts_count": 0,
            "latest_story_count": 0,
            "bio": "",
            "profile_pic": "",
            "external_url": ""
        }
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

def parse_premium_list(raw_data):
    usernames = []
    try:
        items = raw_data.get('data', {}).get('items', []) or raw_data.get('users', []) or raw_data.get('items', [])
        for item in items:
            user_obj = item.get('user') if 'user' in item else item
            uname = user_obj.get('username')
            if uname: usernames.append(uname)
    except: pass
    return usernames

# --- MANUEL KOMUTLAR (HIZLI) ---
def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} sayılar kontrol ediliyor...", chat_id)
    
    profile_data = call_basic_api("/api/instagram/profile", {"username": TARGET_USERNAME})
    
    if profile_data:
        try:
            res = profile_data if 'username' in profile_data else profile_data.get('result') or profile_data.get('data')
            if isinstance(res, list): res = res[0]
            if 'user' in res: res = res['user']
            
            fol = res.get('follower_count', 0)
            fng = res.get('following_count', 0)
            name = res.get('full_name', TARGET_USERNAME)
            
            send_telegram_message(f"📊 RAPOR ({name}):\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}\n📅 {get_time_str()}", chat_id)
        except:
            send_telegram_message("❌ Veri okunamadı.", chat_id)
    else:
        send_telegram_message("❌ Basic API yanıt vermedi.", chat_id)

def handle_story(chat_id):
    send_telegram_message("🔍 Hikayeler kontrol ediliyor...", chat_id)
    
    story_data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    
    if story_data:
        sl = story_data.get('result', [])
        count = len(sl)
        if count > 0:
            send_telegram_message(f"🔥 {count} Adet Aktif Hikaye Var!", chat_id)
        else:
            send_telegram_message("ℹ️ Aktif hikaye yok.", chat_id)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

def handle_debug(chat_id):
    send_telegram_message(f"🛠️ Sistem Ayakta.\nAnahtar Sayısı: {len(ALL_KEYS)}\nHedef: {TARGET_USERNAME}", chat_id)

# --- ANA DETAYLI KONTROL (AĞIR) ---
def check_full_status(manual=False, chat_id=None):
    if manual: send_telegram_message("🕵️‍♂️ Detaylı FBI Analizi Başlatıldı...", chat_id)
    
    # 1. BASIC API: Profil ve Sayılar
    profile_data = call_basic_api("/api/instagram/profile", {"username": TARGET_USERNAME})
    if not profile_data: return

    try:
        res = profile_data if 'username' in profile_data else profile_data.get('result') or profile_data.get('data')
        if isinstance(res, list): res = res[0]
        if 'user' in res: res = res['user']

        curr_id = res.get('pk') or res.get('id')
        curr_fol_count = res.get('follower_count', 0)
        curr_fng_count = res.get('following_count', 0)
        curr_posts_count = res.get('media_count', 0)
        curr_bio = res.get('biography', "")
        curr_link = res.get('external_url', "")
        
    except: return

    old_data = load_data()
    
    # ID Kaydı
    if not old_data.get("user_id") and curr_id:
        old_data["user_id"] = curr_id
        save_data(old_data)

    # 2. DEĞİŞİM VAR MI?
    change_detected = False
    if curr_fol_count != old_data.get("followers_count", 0): change_detected = True
    if curr_fng_count != old_data.get("following_count", 0): change_detected = True
    if not old_data.get("followers_list"): change_detected = True 

    final_fol_list = old_data.get("followers_list", [])
    final_fng_list = old_data.get("following_list", [])

    # 3. DEĞİŞİM VARSA -> PREMIUM API İLE LİSTE ÇEK
    if change_detected or manual:
        if manual: send_telegram_message("🔍 Listeler taranıyor...", chat_id)
        
        raw_fol = call_premium_api("followers", curr_id)
        new_fol_list = parse_premium_list(raw_fol)
        
        raw_fng = call_premium_api("following", curr_id)
        new_fng_list = parse_premium_list(raw_fng)
        
        # Karşılaştırma: Gelen Takipçi
        if new_fol_list:
            diff_new = set(new_fol_list) - set(final_fol_list)
            for user in diff_new:
                # İSTEDİĞİN FORMAT 👇
                msg = f"{user} ({TARGET_USERNAME})'yı takip etmeye başladı\n\n{get_time_str()}"
                send_telegram_message(msg, chat_id)
            
            # Giden Takipçi (İstersen aç)
            # ...
            final_fol_list = new_fol_list

        # Karşılaştırma: Yeni Takip Ettikleri
        if new_fng_list:
            diff_new = set(new_fng_list) - set(final_fng_list)
            for user in diff_new:
                # İSTEDİĞİN FORMAT 👇
                msg = f"({TARGET_USERNAME}) {user}'i takip etmeye başladı\n\n{get_time_str()}"
                send_telegram_message(msg, chat_id)
            
            # Takipten Çıktıkları
            diff_lost = set(final_fng_list) - set(new_fng_list)
            for user in diff_lost:
                msg = f"({TARGET_USERNAME}) {user}'i takipten çıktı\n\n{get_time_str()}"
                send_telegram_message(msg, chat_id)

            final_fng_list = new_fng_list
    
    # 4. DİĞER KONTROLLER (Basic)
    if old_data.get("bio") and curr_bio != old_data["bio"]:
        send_telegram_message(f"📝 BİYOGRAFİ DEĞİŞTİ!\nYeni: {curr_bio}")
        
    if curr_posts_count > old_data.get("posts_count", 0) and old_data.get("posts_count", 0) != 0:
        send_telegram_message(f"📸 YENİ GÖNDERİ PAYLAŞILDI! (Toplam: {curr_posts_count})", chat_id)

    story_data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    curr_story_count = 0
    if story_data:
        sl = story_data.get('result', [])
        curr_story_count = len(sl)
        if curr_story_count > old_data.get("latest_story_count", 0):
            send_telegram_message(f"🔥 YENİ HİKAYE! ({curr_story_count} adet)", chat_id)

    if manual:
        send_telegram_message(f"✅ Analiz Tamamlandı.\nTakipçi: {curr_fol_count}\nTakip Edilen: {curr_fng_count}", chat_id)

    # KAYDET
    save_data({
        "user_id": curr_id,
        "followers_count": curr_fol_count,
        "following_count": curr_fng_count,
        "posts_count": curr_posts_count,
        "latest_story_count": curr_story_count,
        "followers_list": final_fol_list,
        "following_list": final_fng_list,
        "bio": curr_bio,
        "external_url": curr_link,
        "profile_pic": ""
    })

# --- LOOP ---
def bot_loop():
    print("🚀 9-MOTORLU TAM FORMAT BAŞLATILDI")
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
                    
                    # KOMUT KONTROLLERİ
                    if "/kontrol" in text:
                        check_full_status(manual=True, chat_id=chat_id)
                    elif "/takipci" in text or "/takip" in text:
                        handle_takipci(chat_id)
                    elif "/story" in text:
                        handle_story(chat_id)
                    elif "/debug" in text:
                        handle_debug(chat_id)
                        
        except:
            time.sleep(1)
        
        if time.time() - last_auto_check >= CHECK_INTERVAL:
            check_full_status(manual=False)
            last_auto_check = time.time()
        
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
