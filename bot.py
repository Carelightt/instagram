import time
import json
import os
import threading
import requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "BOT BASLADI!"

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
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def get_time_str():
    return datetime.now().strftime("%H:%M %d.%m.%Y")

def calculate_time_ago(timestamp):
    if not timestamp: return ""
    try:
        diff = int(time.time()) - int(timestamp)
        if diff < 60: return "(Az önce)"
        minutes = diff // 60
        hours = minutes // 60
        mins_left = minutes % 60
        if hours > 0: return f"({hours}s {mins_left}dk önce)"
        else: return f"({minutes}dk önce)"
    except: return ""

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message, "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def deep_search(data, key):
    if isinstance(data, dict):
        if key in data: return data[key]
        for k, v in data.items():
            res = deep_search(v, key)
            if res is not None: return res
    elif isinstance(data, list):
        for item in data:
            res = deep_search(item, key)
            if res is not None: return res
    return None

# --- API ÇAĞRILARI ---
def call_basic_api(endpoint, payload_dict):
    url = f"https://{HOST_BASIC}{endpoint}"
    for i, key in enumerate(ALL_KEYS):
        try:
            headers = {"x-rapidapi-key": key, "x-rapidapi-host": HOST_BASIC, "Content-Type": "application/json", "User-Agent": USER_AGENT}
            response = requests.post(url, json=payload_dict, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if "stories" in endpoint: return data
                if deep_search(data, "follower_count") is not None: return data
            if response.status_code == 429: continue 
        except: continue
    return None

# --- PREMIUM API (RETRY MEKANİZMALI) ---
def fetch_full_list_premium(endpoint_type, user_id):
    url = f"https://{HOST_PREMIUM}/{endpoint_type}"
    all_usernames = []
    next_token = None
    page_count = 0
    MAX_PAGES = 30 
    
    current_key_index = 0
    
    while True:
        if page_count >= MAX_PAGES: break
        
        # SAYFAYI ÇEKMEK İÇİN 3 KEZ DENEME HAKKI (RETRY LOOP)
        success = False
        retry_count = 0
        
        while retry_count < 3:
            key = ALL_KEYS[current_key_index]
            querystring = {"user_id": str(user_id)}
            if next_token:
                querystring["next_max_id"] = next_token

            try:
                headers = {"x-rapidapi-key": key, "x-rapidapi-host": HOST_PREMIUM, "User-Agent": USER_AGENT}
                response = requests.get(url, headers=headers, params=querystring, timeout=20)
                
                # Limit dolduysa anahtar değiştir ve tekrar dene
                if response.status_code == 429 or response.status_code == 403:
                    current_key_index = (current_key_index + 1) % len(ALL_KEYS)
                    time.sleep(1)
                    continue # Retry loop içinde devam et
                
                if response.status_code == 200:
                    data = response.json()
                    new_users = parse_premium_list_chunk(data)
                    
                    if new_users:
                        all_usernames.extend(new_users)
                    
                    next_token = data.get("next_max_id")
                    page_count += 1
                    success = True
                    time.sleep(1) # API dinlensin
                    break # Retry loop'tan çık, sonraki sayfaya geç
                else:
                    # Başka hata (500 vs)
                    retry_count += 1
                    time.sleep(2)
                    
            except Exception as e:
                print(f"Hata: {e}")
                retry_count += 1
                time.sleep(2)
        
        # 3 kere denedik hala olmadıysa veya next_token yoksa döngüyü kır
        if not success or not next_token:
            break
            
    return list(set(all_usernames))

def parse_premium_list_chunk(raw_data):
    usernames = []
    try:
        items = raw_data.get('data', {}).get('items', []) or raw_data.get('users', []) or raw_data.get('items', [])
        for item in items:
            user_obj = item.get('user') if 'user' in item else item
            uname = user_obj.get('username')
            if uname: usernames.append(uname)
    except: pass
    return usernames

def parse_profile(data):
    try:
        fol = deep_search(data, "follower_count")
        fng = deep_search(data, "following_count")
        if fol is None:
            edge_fol = deep_search(data, "edge_followed_by")
            if edge_fol and isinstance(edge_fol, dict): fol = edge_fol.get("count")
        if fng is None:
            edge_fng = deep_search(data, "edge_follow")
            if edge_fng and isinstance(edge_fng, dict): fng = edge_fng.get("count")

        if fol is None: return None

        uid = deep_search(data, "pk") or deep_search(data, "id")
        name = deep_search(data, "full_name") or TARGET_USERNAME
        bio = deep_search(data, "biography") or ""
        url = deep_search(data, "external_url") or ""
        posts = deep_search(data, "media_count") or 0
        
        return {"id": uid, "followers": fol, "following": fng, "posts": posts, "bio": bio, "url": url, "full_name": name}
    except: return None

def get_robust_profile():
    endpoints = ["/api/instagram/userInfo", "/api/instagram/profile"]
    for ep in endpoints:
        raw = call_basic_api(ep, {"username": TARGET_USERNAME})
        if raw:
            parsed = parse_profile(raw)
            if parsed: return parsed
    return None

# --- DATA ---
def load_data():
    if not os.path.exists("data.json"): return {}
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

# --- KOMUTLAR ---
def handle_takipci(chat_id):
    send_telegram_message(f"{TARGET_USERNAME} takip listesi kontrol ediliyor...", chat_id)
    profile = get_robust_profile()
    d = load_data()
    saved_fol = d.get("followers_count", 0)
    saved_fng = d.get("following_count", 0)
    
    if profile:
        fol = max(profile['followers'], saved_fol)
        fng = max(profile['following'], saved_fng)
        msg = f"📊 RAPOR ({profile['full_name']}):\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}\n📅 {get_time_str()}"
        send_telegram_message(msg, chat_id)
        d["followers_count"] = fol
        d["following_count"] = fng
        if "id" in profile: d["user_id"] = profile["id"]
        save_data(d)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

def handle_story(chat_id):
    send_telegram_message("🔍 Hikaye kontrol...", chat_id)
    data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    if data:
        sl = deep_search(data, "result")
        if isinstance(sl, list):
            count = len(sl)
            if count > 0:
                last_taken = 0
                for s in sl:
                    taken = s.get('taken_at') or s.get('taken_at_timestamp')
                    if taken and taken > last_taken: last_taken = taken
                time_msg = calculate_time_ago(last_taken)
                send_telegram_message(f"🔥 {count} Adet Aktif Hikaye Var! {time_msg}", chat_id)
            else: send_telegram_message("ℹ️ Aktif hikaye yok.", chat_id)
        else: send_telegram_message("ℹ️ Aktif hikaye yok (Veri boş).", chat_id)
    else: send_telegram_message("❌ Veri alınamadı.", chat_id)

def handle_listem(chat_id):
    d = load_data()
    fng_list = d.get("following_list", [])
    fol_list = d.get("followers_list", [])
    real_fng = d.get("following_count", 0)
    real_fol = d.get("followers_count", 0)
    
    if not fng_list and not fol_list:
        send_telegram_message("📂 Hafıza boş! /kontrol yazıp doldur.", chat_id)
        return

    msg = f"BOT HAFIZASI:\n\n"
    msg += f"👉 Takip Edilen: {real_fng} (Listelenen: {len(fng_list)})\n"
    if fng_list:
        msg += ", ".join(fng_list[:50])
        if len(fng_list) > 50: msg += f"\n... ve {len(fng_list)-50} kişi daha."
    else: msg += "(Liste boş)"
    msg += "\n\n"
    msg += f"👤 Takipçi: {real_fol} (Listelenen: {len(fol_list)})\n"
    if fol_list:
        msg += ", ".join(fol_list[:50])
        if len(fol_list) > 50: msg += f"\n... ve {len(fol_list)-50} kişi daha."
    else: msg += "(Liste boş)"
    
    send_telegram_message(msg, chat_id)

# --- OTOMATİK / KONTROL ---
def check_full_status(manual=False, chat_id=None):
    if manual: send_telegram_message("Takip ediliyor.", chat_id)
    
    profile = get_robust_profile()
    if not profile:
        if manual: send_telegram_message("❌ Basic API Profil verisi vermedi.", chat_id)
        return

    curr_id = profile["id"]
    curr_fol = profile["followers"]
    curr_fng = profile["following"]
    curr_posts = profile["posts"]
    curr_bio = profile["bio"]
    curr_link = profile["url"]

    old_data = load_data()
    if not old_data.get("user_id") and curr_id:
        old_data["user_id"] = curr_id
        save_data(old_data)

    change = False
    if curr_fol != old_data.get("followers_count", 0): change = True
    if curr_fng != old_data.get("following_count", 0): change = True
    if not old_data.get("followers_list"): change = True

    final_fol_list = old_data.get("followers_list", [])
    final_fng_list = old_data.get("following_list", [])

    # LISTE ÇEKME
    if change or manual:
        if manual: send_telegram_message("Kontrol Etmeye Başlanıyor...", chat_id)
        
        raw_fol = fetch_full_list_premium("followers", curr_id)
        raw_fng = fetch_full_list_premium("following", curr_id)
        
        if raw_fol:
            diff_new = set(raw_fol) - set(final_fol_list)
            for user in diff_new:
                send_telegram_message(f"{user} ({TARGET_USERNAME})'yı takip etmeye başladı\n\n{get_time_str()}", chat_id)
            
            # İlk taramada "takipten çıktı" demesin diye sadece eski liste varsa kontrol et
            if final_fol_list:
                diff_lost = set(final_fol_list) - set(raw_fol)
                for user in diff_lost:
                    send_telegram_message(f"{user} ({TARGET_USERNAME})'yı takipten çıktı\n\n{get_time_str()}", chat_id)
            
            final_fol_list = raw_fol
            # Liste daha büyükse sayıyı ona eşitle
            if len(raw_fol) > curr_fol: curr_fol = len(raw_fol)

        if raw_fng:
            diff_new = set(raw_fng) - set(final_fng_list)
            for user in diff_new:
                send_telegram_message(f"({TARGET_USERNAME}) {user}'i takip etmeye başladı\n\n{get_time_str()}", chat_id)
            
            if final_fng_list:
                diff_lost = set(final_fng_list) - set(raw_fng)
                for user in diff_lost:
                    send_telegram_message(f"({TARGET_USERNAME}) {user}'i takipten çıktı\n\n{get_time_str()}", chat_id)

            final_fng_list = raw_fng
            if len(raw_fng) > curr_fng: curr_fng = len(raw_fng)

    if old_data.get("bio") and curr_bio != old_data["bio"]:
        send_telegram_message(f"📝 BİYOGRAFİ DEĞİŞTİ!\nEski: {old_data['bio']}\nYeni: {curr_bio}", chat_id)
    if curr_posts > old_data.get("posts_count", 0) and old_data.get("posts_count", 0) != 0:
        send_telegram_message("📸 YENİ GÖNDERİ PAYLAŞILDI!", chat_id)

    story_data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    curr_story_count = 0
    if story_data:
        sl = deep_search(story_data, "result")
        if isinstance(sl, list):
            curr_story_count = len(sl)
            if curr_story_count > old_data.get("latest_story_count", 0):
                last_taken = 0
                for s in sl:
                    taken = s.get('taken_at') or s.get('taken_at_timestamp')
                    if taken and taken > last_taken: last_taken = taken
                time_msg = calculate_time_ago(last_taken)
                send_telegram_message(f"🔥 YENİ HİKAYE! ({curr_story_count} adet) {time_msg}", chat_id)
    else:
        curr_story_count = old_data.get("latest_story_count", 0)

# --- BU KISMI DEĞİŞTİRDİK: ARTIK HER ZAMAN RAPOR ATACAK ---
    if manual:
        if not change: send_telegram_message("ℹ️ Listelerde değişiklik yok.", chat_id)
    
    # Saati al
    now = datetime.now().strftime("%H:%M")
    
    # Değişiklik olsun olmasın, her 15 dakikada bir bu mesaj gelir:
    msg = f"✅ 15 DAKİKALIK KONTROL ({now})\n"
    msg += f"👤 Takipçi: {curr_fol}\n"
    msg += f"👉 Takip Edilen: {curr_fng}"
    
    # Story bilgisini de ekleyelim
    if curr_story_count > 0:
        msg += f"\n🔥 {curr_story_count} Aktif Hikaye"
    else:
        msg += "\nℹ️ Hikaye Yok"

    send_telegram_message(msg, chat_id)

    save_data({
        "user_id": curr_id,
        "followers_count": curr_fol,
        "following_count": curr_fng,
        "posts_count": curr_posts,
        "latest_story_count": curr_story_count,
        "followers_list": final_fol_list,
        "following_list": final_fng_list,
        "bio": curr_bio,
        "external_url": curr_link,
        "profile_pic": ""
    })

def bot_loop():
    print("🚀 V12 BAŞLATILDI")
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
                    
                    if "/kontrol" in text: check_full_status(manual=True, chat_id=chat_id)
                    elif "/takipci" in text: handle_takipci(chat_id)
                    elif "/story" in text: handle_story(chat_id)
                    elif "/listem" in text: handle_listem(chat_id)
        except: time.sleep(1)
        
        if time.time() - last_auto_check >= CHECK_INTERVAL:
            check_full_status(manual=False)
            last_auto_check = time.time()
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
