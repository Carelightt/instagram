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
    return "🚀 FBI MODU AKTİF!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 7 ANAHTAR
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

# Her kontrolde çok fazla istek attığımız için (Profil + Post + Follower + Following + Story)
# Süreyi biraz uzattık ki kota dayanabilsin.
# 40 Dakika = 2400 Saniye
CHECK_INTERVAL = 2400 

def get_time_str():
    """İstediğin format: saat/dakika gün.ay.yıl"""
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

def call_rapid_api(endpoint, payload_dict):
    url = f"https://{RAPID_HOST}{endpoint}"
    for i, key in enumerate(API_KEYS):
        try:
            headers = {
                "x-rapidapi-key": key,
                "x-rapidapi-host": RAPID_HOST,
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload_dict, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429:
                continue # Limit doldu, diğerine geç
            
            print(f"⚠️ API Hatası (Key {i+1}): {response.status_code}")
        except:
            continue
    return None

# --- VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists("data.json"): 
        return {
            "followers_list": [], 
            "following_list": [], 
            "posts_map": {}, # {id: caption}
            "bio": "", 
            "profile_pic": "",
            "external_url": "",
            "highlight_count": 0
        }
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("data.json", "w") as f: json.dump(data, f)

# --- DETAYLI ANALİZ ---
def check_full_status(manual=False, chat_id=None):
    if manual: send_telegram_message("🕵️‍♂️ FBI Analizi Başlatıldı... (Biraz sürebilir)", chat_id)
    
    # 1. PROFİL KONTROLÜ (Bio, Foto, Link)
    profile_data = call_rapid_api("/api/instagram/profile", {"username": TARGET_USERNAME})
    if not profile_data: return

    p_res = profile_data if 'username' in profile_data else profile_data.get('result') or profile_data.get('data')
    if not p_res: return

    # Verileri al
    curr_bio = p_res.get('biography', "")
    curr_pic = p_res.get('hd_profile_pic_url_info', {}).get('url') or p_res.get('profile_pic_url', "")
    curr_link = p_res.get('external_url', "")
    user_id = p_res.get('pk') or p_res.get('id')

    old_data = load_data()
    
    # Biyo Değişikliği
    if old_data.get("bio") and curr_bio != old_data["bio"]:
        send_telegram_message(f"📝 BİYOGRAFİ DEĞİŞTİ!\nEski: {old_data['bio']}\nYeni: {curr_bio}")

    # Link Değişikliği
    if old_data.get("external_url") and curr_link != old_data["external_url"]:
        send_telegram_message(f"🔗 LİNK DEĞİŞTİ!\nYeni: {curr_link}")

    # Profil Fotosu (Basit kontrol, URL değişirse uyarır)
    # URL'ler bazen token yüzünden değişebilir, o yüzden sadece çok bariz değişimde uyarmak lazım ama şimdilik açalım.
    if old_data.get("profile_pic") and curr_pic and curr_pic[:50] != old_data["profile_pic"][:50]:
         send_telegram_message(f"🖼️ PROFİL FOTOĞRAFI DEĞİŞTİ!")

    # 2. GÖNDERİ ANALİZİ (Yeni, Silinen, Edit, Konum, Arşivden Dönen)
    posts_data = call_rapid_api("/api/instagram/posts", {"username": TARGET_USERNAME})
    curr_posts_map = {}
    
    if posts_data:
        p_list = posts_data.get('edges', []) or posts_data.get('result', {}).get('feed', {}).get('edges', []) or []
        
        for edge in p_list:
            node = edge.get('node', {})
            pid = node.get('id')
            code = node.get('shortcode')
            caption = node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', "")
            location = node.get('location', {}).get('name') if node.get('location') else None
            taken_at = node.get('taken_at_timestamp', time.time())
            
            curr_posts_map[pid] = {"code": code, "caption": caption, "time": taken_at, "loc": location}
            
            # YENİ GÖNDERİ Mİ? (Listemizde yoksa)
            if pid not in old_data.get("posts_map", {}):
                # Arşivden mi döndü yoksa taze mi? (2 gün sınırı)
                is_old = (time.time() - taken_at) > 172800 
                
                link = f"https://instagram.com/p/{code}"
                msg = ""
                
                if is_old:
                    msg = f"🔄 ARŞİVDEN DÖNEN GÖNDERİ!\nLink: {link}"
                else:
                    msg = f"📸 YENİ GÖNDERİ/REELS!\n📝: {caption}\nLink: {link}"
                
                if location: msg += f"\n📍 Konum: {location}"
                
                send_telegram_message(msg, chat_id)
            
            # CAPTION EDİT Mİ?
            elif pid in old_data.get("posts_map", {}):
                old_cap = old_data["posts_map"][pid].get("caption", "")
                if old_cap != caption:
                    send_telegram_message(f"✏️ AÇIKLAMA DÜZENLENDİ!\nEski: {old_cap}\nYeni: {caption}\nLink: https://instagram.com/p/{code}")

        # SİLİNEN GÖNDERİ VAR MI?
        # (Eski listede olup yeni listede olmayanlar)
        # Not: API sadece son 12-24 postu çeker. Eğer çok eski postlar listeden düştüyse silindi sanabilir.
        # Bu yüzden sadece 'yakın zamanda kaydedilmiş' olanları kontrol etmek daha güvenli ama şimdilik basit tutuyoruz.
        # Bu özellik bazen false alarm verebilir.
        pass 

    # 3. KİMİ TAKİP ETTİ / KİM TAKİP ETTİ (EN ÖNEMLİSİ)
    # Sadece ilk sayfayı (yaklaşık 20-50 kişi) çekiyoruz, çünkü en yeniler en üstte olur.
    
    # --- TAKİPÇİLER (FOLLOWERS) ---
    fol_data = call_rapid_api("/api/instagram/followers", {"id": user_id, "first": 50}) # ID ile çalışır genelde
    curr_fol_list = []
    
    if fol_data:
        edges = fol_data.get('edges', []) or fol_data.get('data', {}).get('user', {}).get('edge_followed_by', {}).get('edges', [])
        for e in edges:
            n = e.get('node', {})
            curr_fol_list.append(n.get('username'))
            
        # Analiz
        old_fol_list = old_data.get("followers_list", [])
        if old_fol_list:
            new_followers = set(curr_fol_list) - set(old_fol_list)
            for user in new_followers:
                # İSTEDİĞİN FORMAT
                msg = f"{user} ({TARGET_USERNAME})'yı takip etmeye başladı\n\n{get_time_str()}"
                send_telegram_message(msg, chat_id)

    # --- TAKİP EDİLENLER (FOLLOWING) ---
    fng_data = call_rapid_api("/api/instagram/following", {"id": user_id, "first": 50})
    curr_fng_list = []
    
    if fng_data:
        edges = fng_data.get('edges', []) or fng_data.get('data', {}).get('user', {}).get('edge_follow', {}).get('edges', [])
        for e in edges:
            n = e.get('node', {})
            curr_fng_list.append(n.get('username'))
            
        # Analiz
        old_fng_list = old_data.get("following_list", [])
        if old_fng_list:
            new_following = set(curr_fng_list) - set(old_fng_list)
            for user in new_following:
                # İSTEDİĞİN FORMAT
                msg = f"({TARGET_USERNAME}) {user}'i takip etmeye başladı\n\n{get_time_str()}"
                send_telegram_message(msg, chat_id)

    # 4. HİKAYE (STORY)
    story_data = call_rapid_api("/api/instagram/stories", {"username": TARGET_USERNAME})
    if story_data:
        sl = story_data if isinstance(story_data, list) else story_data.get('result', [])
        # Müzik analizi için story detayına bakmak gerekir, burada sadece var mı yok mu bakıyoruz
        if len(sl) > old_data.get("latest_story_count", 0):
             send_telegram_message(f"🔥 YENİ HİKAYE ATILDI! ({len(sl)} adet)")

    # 5. HIGHLIGHTS
    hl_data = call_rapid_api("/api/instagram/highlights", {"username": TARGET_USERNAME})
    curr_hl = 0
    if hl_data:
        l = hl_data if isinstance(hl_data, list) else hl_data.get('result', [])
        curr_hl = len(l)
        if curr_hl > old_data.get("highlight_count", 0):
             send_telegram_message("⭐ YENİ ÖNE ÇIKAN (HIGHLIGHT) EKLENDİ!")

    # VERİLERİ KAYDET
    # Listeleri sadece doluysa güncelle ki API hatasında veri kaybolmasın
    final_fol = curr_fol_list if curr_fol_list else old_data.get("followers_list", [])
    final_fng = curr_fng_list if curr_fng_list else old_data.get("following_list", [])
    final_posts = curr_posts_map if curr_posts_map else old_data.get("posts_map", {})
    
    save_data({
        "bio": curr_bio,
        "profile_pic": curr_pic,
        "external_url": curr_link,
        "followers_list": final_fol,
        "following_list": final_fng,
        "posts_map": final_posts,
        "highlight_count": curr_hl,
        "latest_story_count": len(sl) if story_data else old_data.get("latest_story_count", 0)
    })
    
    if manual: send_telegram_message("✅ Manuel Analiz Tamamlandı.", chat_id)

# --- KOMUT İŞLEYİCİLERİ ---
def handle_takipci(chat_id):
    send_telegram_message("🔍 Hızlı takipçi sayısı kontrolü...", chat_id)
    # Hızlıca sadece sayıya bakmak için profil endpointi yeterli
    data = call_rapid_api("/api/instagram/profile", {"username": TARGET_USERNAME})
    if data:
        res = data if 'username' in data else data.get('result') or data.get('data')
        fol = res.get('follower_count', 0)
        fng = res.get('following_count', 0)
        send_telegram_message(f"📊 {TARGET_USERNAME}:\n👤 Takipçi: {fol}\n👉 Takip Edilen: {fng}", chat_id)

def bot_loop():
    print("🚀 FBI MODU BAŞLATILDI")
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
                        
        except Exception:
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
