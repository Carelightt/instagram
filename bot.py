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
    return "🚀 BOT ÇALIŞIYOR!"

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

# 15 Dakikada bir otomatik kontrol
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

# --- BASIC API (SURVIVOR MODU: SAĞLAMI BULANA KADAR DENE) ---
def call_basic_api_robust(endpoint, payload_dict):
    url = f"https://{HOST_BASIC}{endpoint}"
    
    for i, key in enumerate(ALL_KEYS):
        try:
            headers = {
                "x-rapidapi-key": key,
                "x-rapidapi-host": HOST_BASIC,
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload_dict, headers=headers, timeout=10)
            
            if response.status_code != 200:
                continue # Hata varsa geç

            data = response.json()
            
            # --- SAĞLAMLIK KONTROLÜ ---
            # Gelen veri boş mu dolu mu?
            # Eğer 'result' listesi boşsa veya follower_count yoksa bu anahtar BOZUKTUR.
            # Hemen diğer anahtara geçsin.
            parsed = parse_basic_profile(data)
            
            if endpoint == "/api/instagram/stories":
                return data # Story için parse gerekmez, direkt döndür
            
            if parsed:
                # Eğer takipçi sayısı 0 geliyorsa şüphelidir ama belki gerçekten 0'dır.
                # Yine de veri yapısı doğruysa bunu kabul edelim.
                return parsed # İŞLENMİŞ TEMİZ VERİYİ DÖNDÜR
            
            # Parse edilemediyse (None döndüyse) demek ki veri bozuk, devam et.
            
        except: 
            continue
            
    return None # Hiçbiri çalışmadı

# --- PARSE (SENİN ATTIĞIN JSON YAPISINA GÖRE) ---
def parse_basic_profile(data):
    try:
        # Yapı: {"result": [ {"user": {...}} ]}
        if "result" in data and isinstance(data["result"], list) and len(data["result"]) > 0:
            user_obj = data["result"][0].get("user")
            if user_obj:
                return {
                    "id": user_obj.get('pk') or user_obj.get('id'),
                    "followers": user_obj.get('follower_count', 0),
                    "following": user_obj.get('following_count', 0),
                    "posts": user_obj.get('media_count', 0),
                    "bio": user_obj.get('biography', ""),
                    "url": user_obj.get('external_url', ""),
                    "pic": user_obj.get('profile_pic_url', "")
                }
        return None
    except:
        return None

# --- PREMIUM API ---
def call_premium_api(endpoint_type, user_id):
    url = f"https://{HOST_PREMIUM}/{endpoint_type}"
    for key in ALL_KEYS:
        try:
            querystring = {"user_id": str(user_id)}
            headers = {"x-rapidapi-key": key, "x-rapidapi-host": HOST_PREMIUM}
            response = requests.get(url, headers=headers, params=querystring, timeout=15)
            if response.status_code == 200: return response.json()
        except: continue
    return None

# --- VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists("data.json"): return {}
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

# --- KOMUT: /takipci (CANLI KONTROL) ---
def handle_takipci(chat_id):
    send_telegram_message(f"🔍 {TARGET_USERNAME} canlı kontrol ediliyor...", chat_id)
    
    # DİKKAT: call_basic_api_robust fonksiyonu artık direkt TEMİZ VERİ dönüyor.
    # Dosyadan okumuyoruz, direkt API'den gelen taze veri.
    profile = call_basic_api_robust("/api/instagram/profile", {"username": TARGET_USERNAME})
    
    if profile:
        fol = profile["followers"]
        fng = profile["following"]
        
        send_telegram_message(f"📊 CANLI RAPOR:\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}\n📅 {get_time_str()}", chat_id)
        
        # Şimdi dosyayı güncelleyelim ki otomatik kontrol şaşırmasın
        d = load_data()
        d["followers_count"] = fol
        d["following_count"] = fng
        # Eğer ID yoksa onu da ekle
        if "id" in profile: d["user_id"] = profile["id"]
        save_data(d)
    else:
        send_telegram_message("❌ Veri alınamadı (Tüm API anahtarları denendi).", chat_id)

# --- KOMUT: /story ---
def handle_story(chat_id):
    send_telegram_message("🔍 Hikaye kontrol...", chat_id)
    # Story için robust fonksiyona özel durum ekledik, ham data dönecek
    data = call_basic_api_robust("/api/instagram/stories", {"username": TARGET_USERNAME})
    
    if data:
        sl = data.get('result', [])
        count = len(sl)
        if count > 0: send_telegram_message(f"🔥 {count} Adet Aktif Hikaye Var!", chat_id)
        else: send_telegram_message("ℹ️ Aktif hikaye yok.", chat_id)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

# --- OTOMATİK DÖNGÜ ---
def check_full_status(manual=False, chat_id=None):
    if manual: send_telegram_message("🕵️‍♂️ Manuel FBI Taraması...", chat_id)
    
    profile = call_basic_api_robust("/api/instagram/profile", {"username": TARGET_USERNAME})
    if not profile:
        if manual: send_telegram_message("❌ API Hatası.", chat_id)
        return

    curr_id = profile["id"]
    curr_fol = profile["followers"]
    curr_fng = profile["following"]
    curr_posts = profile["posts"]
    curr_bio = profile["bio"]
    curr_link = profile["url"]

    old_data = load_data()
    
    # DEĞİŞİM VAR MI?
    change = False
    if curr_fol != old_data.get("followers_count", 0): change = True
    if curr_fng != old_data.get("following_count", 0): change = True
    if not old_data.get("followers_list"): change = True

    final_fol_list = old_data.get("followers_list", [])
    final_fng_list = old_data.get("following_list", [])

    # PREMIUM KONTROL (Değişim varsa)
    if change or manual:
        if manual: send_telegram_message("🔍 Listeler çekiliyor...", chat_id)
        
        raw_fol = call_premium_api("followers", curr_id)
        new_fol = parse_premium_list(raw_fol)
        
        raw_fng = call_premium_api("following", curr_id)
        new_fng = parse_premium_list(raw_fng)
        
        if new_fol:
            diff_new = set(new_fol) - set(final_fol_list)
            for user in diff_new:
                send_telegram_message(f"{user} ({TARGET_USERNAME})'yı takip etmeye başladı\n\n{get_time_str()}", chat_id)
            final_fol_list = new_fol

        if new_fng:
            diff_new = set(new_fng) - set(final_fng_list)
            for user in diff_new:
                send_telegram_message(f"({TARGET_USERNAME}) {user}'i takip etmeye başladı\n\n{get_time_str()}", chat_id)
            final_fng_list = new_fng

    # DİĞERLERİ
    if old_data.get("bio") and curr_bio != old_data["bio"]:
        send_telegram_message(f"📝 BİYOGRAFİ DEĞİŞTİ!\nEski: {old_data['bio']}\nYeni: {curr_bio}")
    
    if curr_posts > old_data.get("posts_count", 0) and old_data.get("posts_count", 0) != 0:
        send_telegram_message("📸 YENİ GÖNDERİ PAYLAŞILDI!", chat_id)

    if manual:
        send_telegram_message(f"✅ Bitti.\nTakipçi: {curr_fol}\nTakip Edilen: {curr_fng}", chat_id)

    save_data({
        "user_id": curr_id,
        "followers_count": curr_fol,
        "following_count": curr_fng,
        "posts_count": curr_posts,
        "followers_list": final_fol_list,
        "following_list": final_fng_list,
        "bio": curr_bio,
        "external_url": curr_link,
        "latest_story_count": old_data.get("latest_story_count", 0) # Story'yi burada ellemedik
    })

def bot_loop():
    print("🚀 FİNAL SÜRÜM BAŞLATILDI")
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
                        check_full_status(manual=True, chat_id=chat_id)
                    elif "/takipci" in text:
                        handle_takipci(chat_id)
                    elif "/story" in text:
                        handle_story(chat_id)
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
