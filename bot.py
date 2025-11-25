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
    return "🚀 EFSANE BOT AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 9 ADET ANAHTAR
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

# --- 1. MODÜL: BASIC API ---
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

# --- 2. MODÜL: PREMIUM API ---
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

# --- VERİ YÖNETİMİ ---
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

# --- PARSE FONKSİYONLARI (DÜZELTİLDİ) ---
def parse_basic_profile(data):
    """Basic API'den gelen profil verisini okur"""
    try:
        # Veri yapısı: result -> [0] -> user
        res_list = data.get('result', [])
        if not res_list: return None
        
        user_obj = res_list[0].get('user')
        if not user_obj: return None
        
        return {
            "id": user_obj.get('pk') or user_obj.get('id'),
            "followers": user_obj.get('follower_count', 0),
            "following": user_obj.get('following_count', 0),
            "posts": user_obj.get('media_count', 0),
            "bio": user_obj.get('biography', ""),
            "url": user_obj.get('external_url', ""),
            "pic": user_obj.get('profile_pic_url', "")
        }
    except: return None

def parse_premium_list(raw_data):
    """Premium API'den gelen listeyi okur"""
    usernames = []
    try:
        items = raw_data.get('data', {}).get('items', []) or raw_data.get('users', []) or raw_data.get('items', [])
        for item in items:
            user_obj = item.get('user') if 'user' in item else item
            uname = user_obj.get('username')
            if uname: usernames.append(uname)
    except: pass
    return usernames

# --- ANA KONTROL ---
def check_status(manual=False, chat_id=None):
    if manual: send_telegram_message("🕵️‍♂️ Analiz başlatılıyor...", chat_id)
    
    # A) BASIC API İLE VERİLERİ ÇEK
    raw_profile = call_basic_api("/api/instagram/profile", {"username": TARGET_USERNAME})
    
    if not raw_profile:
        if manual: send_telegram_message("❌ Temel API yanıt vermedi.", chat_id)
        return

    # VERİYİ AYIKLA (HATA BURADAYDI, ŞİMDİ DÜZELTİLDİ)
    profile = parse_basic_profile(raw_profile)
    
    if not profile:
        if manual: send_telegram_message("❌ Profil verisi okunamadı (Format hatası).", chat_id)
        return

    # Güncel Değerler
    curr_id = profile["id"]
    curr_fol_count = profile["followers"]
    curr_fng_count = profile["following"]
    curr_posts_count = profile["posts"]
    curr_bio = profile["bio"]
    curr_link = profile["url"]

    old_data = load_data()
    
    # ID Kaydı (İlk Kez)
    if not old_data.get("user_id") and curr_id:
        old_data["user_id"] = curr_id
        save_data(old_data)

    # --- DEĞİŞİM KONTROLÜ ---
    change_detected = False
    if curr_fol_count != old_data.get("followers_count", 0): change_detected = True
    if curr_fng_count != old_data.get("following_count", 0): change_detected = True
    if not old_data.get("followers_list"): change_detected = True 

    # Eski Listeler
    final_fol_list = old_data.get("followers_list", [])
    final_fng_list = old_data.get("following_list", [])

    # B) PREMIUM API (Sadece değişim varsa)
    if change_detected or manual:
        if manual: send_telegram_message("🔍 Detaylı liste taranıyor...", chat_id)
        
        # Liste Çek
        raw_fol = call_premium_api("followers", curr_id)
        new_fol_list = parse_premium_list(raw_fol)
        
        raw_fng = call_premium_api("following", curr_id)
        new_fng_list = parse_premium_list(raw_fng)
        
        # Takipçi Analizi (Gelen)
        if new_fol_list:
            diff_new = set(new_fol_list) - set(final_fol_list)
            for user in diff_new:
                send_telegram_message(f"{user} ({TARGET_USERNAME})'yı takip etmeye başladı\n\n{get_time_str()}", chat_id)
            
            # Takipçi Analizi (Giden)
            if final_fol_list:
                diff_lost = set(final_fol_list) - set(new_fol_list)
                for user in diff_lost:
                    send_telegram_message(f"{user} ({TARGET_USERNAME})'yı takipten çıktı\n\n{get_time_str()}", chat_id)
            
            final_fol_list = new_fol_list

        # Takip Edilen Analizi
        if new_fng_list:
            diff_new = set(new_fng_list) - set(final_fng_list)
            for user in diff_new:
                send_telegram_message(f"({TARGET_USERNAME}) {user}'i takip etmeye başladı\n\n{get_time_str()}", chat_id)
            
            diff_lost = set(final_fng_list) - set(new_fng_list)
            for user in diff_lost:
                send_telegram_message(f"({TARGET_USERNAME}) {user}'i takipten çıktı\n\n{get_time_str()}", chat_id)

            final_fng_list = new_fng_list
    
    # C) DİĞER KONTROLLER
    if old_data.get("bio") and curr_bio != old_data["bio"]:
        send_telegram_message(f"📝 BİYOGRAFİ DEĞİŞTİ!\nEski: {old_data['bio']}\nYeni: {curr_bio}")
        
    if curr_posts_count > old_data.get("posts_count", 0) and old_data.get("posts_count", 0) != 0:
        send_telegram_message(f"📸 YENİ GÖNDERİ! (Toplam: {curr_posts_count})", chat_id)

    story_data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    curr_story_count = 0
    if story_data:
        sl = story_data.get('result', [])
        curr_story_count = len(sl)
        if curr_story_count > old_data.get("latest_story_count", 0):
            send_telegram_message(f"🔥 YENİ HİKAYE! ({curr_story_count} adet)", chat_id)
    else:
        curr_story_count = old_data.get("latest_story_count", 0)

    # RAPOR (Şimdi sayılar doğru gelecek!)
    if manual:
        msg = f"✅ Analiz Tamamlandı.\nTakipçi: {curr_fol_count}\nTakip Edilen: {curr_fng_count}\n📅 {get_time_str()}"
        send_telegram_message(msg, chat_id)

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

# --- MANUEL KOMUTLAR ---
def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} sayıları kontrol ediliyor...", chat_id)
    raw = call_basic_api("/api/instagram/profile", {"username": TARGET_USERNAME})
    
    profile = parse_basic_profile(raw)
    if profile:
        msg = f"📊 RAPOR:\n👤 Takipçi: {profile['followers']}\n👉 Takip Edilen: {profile['following']}\n📅 {get_time_str()}"
        send_telegram_message(msg, chat_id)
    else:
        send_telegram_message("❌ Veri okunamadı.", chat_id)

def handle_story(chat_id):
    send_telegram_message("🔍 Hikayeler kontrol ediliyor...", chat_id)
    data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    if data:
        sl = data.get('result', [])
        count = len(sl)
        if count > 0: send_telegram_message(f"🔥 {count} Adet Aktif Hikaye Var!", chat_id)
        else: send_telegram_message("ℹ️ Aktif hikaye yok.", chat_id)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

# --- LOOP ---
def bot_loop():
    print("🚀 TAMİR EDİLMİŞ BOT BAŞLATILDI")
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
                    
                    if "/kontrol" in text:
                        check_status(manual=True, chat_id=chat_id)
                    elif "/takipci" in text or "/takip" in text:
                        handle_takipci(chat_id)
                    elif "/story" in text:
                        handle_story(chat_id)
                        
        except:
            time.sleep(1)
        
        if time.time() - last_auto_check >= CHECK_INTERVAL:
            check_status(manual=False)
            last_auto_check = time.time()
        
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
