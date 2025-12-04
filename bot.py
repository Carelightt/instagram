import time
import json
import os
import threading
import requests
import re
from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 V15.1 FIRÇACI MOD AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ANAHTARLAR (Senin 9'lu çete)
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

# --- DOSYA İŞLEMLERİ ---
def download_file(file_id):
    try:
        path_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        path_resp = requests.get(path_url).json()
        file_path = path_resp['result']['file_path']
        dl_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        content = requests.get(dl_url).text
        return content
    except Exception as e:
        print(f"Dosya indirme hatası: {e}")
        return None

def extract_usernames(text_content):
    try:
        data = json.loads(text_content)
        candidates = []
        if isinstance(data, list): candidates = data
        elif isinstance(data, dict):
            candidates = data.get('users') or data.get('relationships_following') or data.get('relationships_followers') or []
        
        usernames = []
        for item in candidates:
            if isinstance(item, dict):
                u = item.get('string_list_data', [{}])[0].get('value') or item.get('username') or item.get('value')
                if u: usernames.append(u)
            elif isinstance(item, str):
                usernames.append(item)
        if usernames: return list(set(usernames))
    except: pass

    usernames = re.findall(r'\b[a-zA-Z0-9._]{2,30}\b', text_content)
    valid_users = [u for u in usernames if not u.isdigit() and len(u) > 1]
    return list(set(valid_users))

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

def load_data():
    if not os.path.exists("data.json"): return {}
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

# --- DOSYA İŞLEME (UYARILI VERSİYON) ---
def handle_document(file_id, caption, chat_id):
    # Eğer caption (açıklama) yoksa veya boşsa
    if not caption:
        send_telegram_message("🤬 Lan hangisi bu? Dosyayı atarken altına 'takipci' ya da 'takip' yaz ki anlayalım! Tekrar at.", chat_id)
        return

    # Hangi listeyi güncelliyoruz?
    mode = ""
    if "takipci" in caption.lower() or "followers" in caption.lower():
        mode = "followers"
        list_key = "followers_list"
        count_key = "followers_count"
        label = "Takipçi"
    elif "takip" in caption.lower() or "following" in caption.lower():
        mode = "following"
        list_key = "following_list"
        count_key = "following_count"
        label = "Takip Edilen"
    else:
        # Caption var ama saçma sapan bir şey yazmışsa
        send_telegram_message("🧐 Kanka ne yazdın anlamadım. 'takipci' mi 'takip' mi? Dosyayı tekrar at.", chat_id)
        return

    # Buraya geldiyse her şey yolunda, indir ve işle
    send_telegram_message(f"📂 {label} listesi alındı, analiz ediliyor...", chat_id)
    
    content = download_file(file_id)
    if not content:
        send_telegram_message("❌ Dosya indirilemedi.", chat_id)
        return

    new_list = extract_usernames(content)
    if not new_list:
        send_telegram_message("❌ Dosyada kullanıcı adı bulunamadı. Formatı kontrol et.", chat_id)
        return

    d = load_data()
    old_list = d.get(list_key, [])
    
    added = []
    removed = []
    
    if old_list:
        added = list(set(new_list) - set(old_list))
        removed = list(set(old_list) - set(new_list))
    else:
        send_telegram_message(f"ℹ️ İlk {label} yüklemesi. Kaydedildi.", chat_id)

    msg = f"📊 {label} Analizi:\n"
    msg += f"Toplam: {len(new_list)}\n\n"
    
    if added:
        msg += "🟢 YENİ GELENLER:\n" + "\n".join(added) + "\n\n"
    if removed:
        msg += "🔴 GİDENLER:\n" + "\n".join(removed) + "\n\n"
    
    if not added and not removed and old_list:
        msg += "✅ Değişiklik Yok."

    send_telegram_message(msg, chat_id)

    d[list_key] = new_list
    d[count_key] = len(new_list)
    save_data(d)

# --- OTOMATİK KONTROL ---
def check_counts(chat_id=None):
    profile = get_robust_profile()
    if not profile: return

    curr_fol = profile["followers"]
    curr_fng = profile["following"]
    curr_posts = profile["posts"]
    curr_bio = profile["bio"]
    
    old_data = load_data()
    
    msg = ""
    # Takipçi Sayısı Değişimi
    if curr_fol != old_data.get("followers_count", 0):
        diff = curr_fol - old_data.get("followers_count", 0)
        icon = "🚨" if diff > 0 else "❌"
        msg += f"{icon} Takipçi Sayısı Değişti! ({diff:+})\n"
        msg += f"Eski: {old_data.get('followers_count', 0)} -> Yeni: {curr_fol}\n"
        msg += "👉 Detay için listeyi indirip bota at!\n\n"
        
    # Takip Edilen Sayısı Değişimi
    if curr_fng != old_data.get("following_count", 0):
        diff = curr_fng - old_data.get("following_count", 0)
        icon = "👀" if diff > 0 else "🚫"
        msg += f"{icon} Takip Edilen Sayısı Değişti! ({diff:+})\n"
        msg += f"Eski: {old_data.get('following_count', 0)} -> Yeni: {curr_fng}\n"
        msg += "👉 Detay için listeyi indirip bota at!\n\n"

    # Story Kontrol
    story_data = call_basic_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    curr_story = 0
    time_msg = ""
    story_list_text = ""
    
    if story_data:
        sl = deep_search(story_data, "result")
        if isinstance(sl, list) and len(sl) > 0:
            curr_story = len(sl)
            if curr_story > old_data.get("latest_story_count", 0):
                 msg += f"🔥 YENİ HİKAYE! ({curr_story} Adet)\n"
            
            # Liste oluştur
            last_taken = 0
            for i, s in enumerate(sl, 1):
                t = s.get('taken_at') or s.get('taken_at_timestamp')
                if t and t > last_taken: last_taken = t
                st_ago = calculate_time_ago(t)
                type_vid = "Video" if s.get("video_versions") else "Foto"
                story_list_text += f"   • {i}. {type_vid} {st_ago}\n"
            
            time_msg = calculate_time_ago(last_taken)
    
    # Diğerleri
    if old_data.get("bio") and curr_bio != old_data["bio"]:
        msg += f"📝 BİYOGRAFİ DEĞİŞTİ!\n"
    if curr_posts > old_data.get("posts_count", 0):
        msg += "📸 YENİ GÖNDERİ PAYLAŞILDI!\n"
    
    # Mesaj Gönderimi
    if msg: send_telegram_message(msg, chat_id)
    elif chat_id: # Manuelse her türlü rapor ver
        rep = f"✅ Durum Stabil ({get_time_str()})\n"
        rep += f"👤 Takipçi: {curr_fol}\n"
        rep += f"👉 Takip Edilen: {curr_fng}\n"
        if curr_story > 0:
            rep += f"🔥 Hikaye: {curr_story} {time_msg}\n{story_list_text}"
        else:
            rep += "ℹ️ Hikaye: Yok"
        send_telegram_message(rep, chat_id)

    old_data["followers_count"] = curr_fol
    old_data["following_count"] = curr_fng
    old_data["posts_count"] = curr_posts
    old_data["latest_story_count"] = curr_story
    old_data["bio"] = curr_bio
    old_data["external_url"] = profile["url"]
    if "id" in profile: old_data["user_id"] = profile["id"]
    save_data(old_data)

def bot_loop():
    print("🚀 V15.1 BAŞLATILDI")
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
                    text = message.get("text", "").lower() if "text" in message else ""
                    chat_id = message.get("chat", {}).get("id")
                    
                    # DOSYA GELDİ Mİ?
                    if "document" in message:
                        file_id = message["document"]["file_id"]
                        caption = message.get("caption", "") # Caption yoksa boş string gelir
                        handle_document(file_id, caption, chat_id)
                    
                    elif "/kontrol" in text:
                        check_counts(chat_id=chat_id)

        except Exception as e: 
            time.sleep(1)
        
        if time.time() - last_auto_check >= CHECK_INTERVAL:
            check_counts(chat_id=TELEGRAM_CHAT_ID)
            last_auto_check = time.time()
        
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
