import time
import json
import http.client
import os
import threading
import requests
from flask import Flask

# --- FLASK (Render İçin) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 7-MOTORLU + KOMUTLU BOT AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🔥 7 ADET API ANAHTARI
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

# ⚡ OTOMATİK KONTROL SÜRESİ: 25 Dakika
CHECK_INTERVAL = 1500 

def send_telegram_message(message, chat_id=None):
    if not TELEGRAM_TOKEN: return
    target_chat = chat_id if chat_id else TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": target_chat, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

# --- API İSTEK FONKSİYONU ---
def call_rapid_api(endpoint, payload_dict):
    for i, key in enumerate(API_KEYS):
        try:
            conn = http.client.HTTPSConnection(RAPID_HOST)
            payload = json.dumps(payload_dict)
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': RAPID_HOST,
                'Content-Type': "application/json"
            }
            conn.request("POST", endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            json_data = json.loads(data.decode("utf-8"))
            
            # Limit kontrolü
            if isinstance(json_data, dict) and "message" in json_data and "exceeded" in str(json_data["message"]):
                print(f"⚠️ Key {i+1} Limit Doldu. Sıradakine geçiliyor...")
                continue
            
            return json_data
        except Exception as e:
            print(f"Hata (Key {i+1}): {e}")
            continue

    print("❌ TÜM KEYLER BAŞARISIZ!")
    return None

# --- VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists("data.json"):
        return {"followers": 0, "following": 0, "bio": "", "posts_count": 0, "highlight_count": 0, "latest_story_count": 0}
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

# --- FULL OTOMATİK KONTROL (4 KREDİ YER) ---
def check_full_status(manual=False, chat_id=None):
    print("🕵️‍♂️ Full kontrol yapılıyor...")
    
    # 1. Profil
    user_data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    if not user_data: return

    result = user_data if 'username' in user_data else user_data.get('result') or user_data.get('data')
    if not result: return

    curr_fol = result.get('follower_count', 0)
    curr_fng = result.get('following_count', 0)
    curr_bio = result.get('biography', "")
    curr_posts = result.get('media_count', 0)
    
    old_data = load_data()
    msgs = []
    
    # Değişim Analizi
    if curr_fol != old_data.get("followers", 0) and old_data.get("followers", 0) != 0:
        diff = curr_fol - old_data.get("followers", 0)
        msgs.append(f"{'🟢' if diff>0 else '🔴'} Takipçi: {curr_fol} ({diff:+})")
        
    if curr_fng != old_data.get("following", 0) and old_data.get("following", 0) != 0:
        diff = curr_fng - old_data.get("following", 0)
        msgs.append(f"{'👀' if diff>0 else '🔻'} Takip Edilen: {curr_fng} ({diff:+})")

    if curr_bio != old_data.get("bio", "") and old_data.get("bio", "") != "":
        msgs.append(f"📝 Biyo Değişti!\nYeni: {curr_bio}")

    if curr_posts > old_data.get("posts_count", 0) and old_data.get("posts_count", 0) != 0:
        msgs.append(f"📸 YENİ GÖNDERİ! (Toplam: {curr_posts})")
    
    # 2. Story
    story_data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    curr_story = 0
    if story_data:
        sl = story_data if isinstance(story_data, list) else story_data.get('result', []) or story_data.get('data', [])
        curr_story = len(sl)
        if curr_story > old_data.get("latest_story_count", 0):
            msgs.append(f"🔥 YENİ HİKAYE! (Aktif: {curr_story})")

    # 3. Highlights
    hl_data = call_rapid_api("/api/instagram/highlights", {"username": TARGET_USERNAME})
    curr_hl = 0
    if hl_data:
        hl = hl_data if isinstance(hl_data, list) else hl_data.get('result', []) or hl_data.get('data', [])
        curr_hl = len(hl)
        if curr_hl > old_data.get("highlight_count", 0) and old_data.get("highlight_count", 0) != 0:
            msgs.append(f"⭐ YENİ HIGHLIGHT! (Toplam: {curr_hl})")

    if msgs:
        send_telegram_message(f"🚨 {TARGET_USERNAME} GÜNCELLEME:\n" + "\n".join(msgs), chat_id)
    elif manual:
        send_telegram_message(f"✅ Temiz. Değişiklik yok.\nTakipçi: {curr_fol}\nHikaye: {curr_story}", chat_id)

    save_data({
        "followers": curr_fol, "following": curr_fng, "bio": curr_bio,
        "posts_count": curr_posts, "highlight_count": curr_hl, "latest_story_count": curr_story
    })

# --- KOMUT İŞLEYİCİLERİ ---
def handle_takipci(chat_id):
    send_telegram_message("🔍 Takipçiler sayılıyor... (1 Kredi)", chat_id)
    data = call_rapid_api("/api/instagram/userInfo", {"username": TARGET_USERNAME})
    if data:
        res = data if 'username' in data else data.get('result') or data.get('data')
        fol = res.get('follower_count', 0)
        fng = res.get('following_count', 0)
        send_telegram_message(f"📊 RAPOR:\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)
        
        # Veriyi güncelle ki otomatik kontrol şaşırmasın
        d = load_data()
        d["followers"] = fol
        d["following"] = fng
        save_data(d)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

def handle_story(chat_id):
    send_telegram_message("🔍 Hikayelere bakılıyor... (1 Kredi)", chat_id)
    data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    if data:
        sl = data if isinstance(data, list) else data.get('result', []) or data.get('data', [])
        count = len(sl)
        if count > 0:
            send_telegram_message(f"🔥 EVET! {count} adet aktif hikaye var.", chat_id)
        else:
            send_telegram_message("ℹ️ Şu an hiç hikaye yok.", chat_id)
        
        d = load_data()
        d["latest_story_count"] = count
        save_data(d)
    else:
        send_telegram_message("❌ Veri alınamadı.", chat_id)

# --- BOT LOOP ---
def bot_loop():
    print("🚀 Komutlu Mod Başlatıldı...")
    last_update_id = 0
    last_auto_check = time.time()

    while True:
        current_time = time.time()
        
        # Telegram Dinleme
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            resp = requests.get(tg_url).json()
            if resp.get("ok"):
                for result in resp["result"]:
                    last_update_id = result["update_id"]
                    message = result.get("message", {})
                    text = message.get("text", "").lower()
                    chat_id = message.get("chat", {}).get("id")
                    
                    if "/kontrol" in text:
                        send_telegram_message("🏎️ Full kontrol yapılıyor... (4 Kredi)", chat_id)
                        check_full_status(manual=True, chat_id=chat_id)
                    
                    elif "/takipci" in text or "/takip" in text:
                        handle_takipci(chat_id)
                        
                    elif "/story" in text:
                        handle_story(chat_id)

        except:
            pass
        
        # Otomatik Kontrol (25 Dakikada bir)
        if current_time - last_auto_check >= CHECK_INTERVAL:
            check_full_status(manual=False)
            last_auto_check = current_time
        
        time.sleep(5)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t2 = threading.Thread(target=bot_loop)
    t1.start()
    t2.start()
