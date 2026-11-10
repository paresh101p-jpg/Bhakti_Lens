#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BHAKTI LENS - FACEBOOK DAILY AUTO POSTER
=============================================================================
- Reads unposted 3:4 devotional image URLs from 'images_urls.txt'
- Uses Google Gemini Vision AI to scan image visual features
- Crafts rich, devotional Hindi spiritual captions with blessings & life wisdom
- Generates 15-20 trending devotional hashtags
- Publishes directly to Facebook Page using official Facebook Graph API
- Automatically manages queue: moves used URL to 'used_urls.txt'
- Runs on daily GitHub Actions schedule or locally
=============================================================================
"""

import os
import sys
import time
import json
import random
import requests
try:
    import google.generativeai as genai
except ImportError:
    genai = None

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URLS_FILE = os.path.join(BASE_DIR, "images_urls.txt")
USED_URLS_FILE = os.path.join(BASE_DIR, "used_urls.txt")
BACKUP_URLS_FILE = os.path.join(BASE_DIR, "images_urls_backup.txt")

# Environment / Credentials
FB_PAGE_ID = (os.environ.get("FB_PAGE_ID") or "").strip()
FB_PAGE_ACCESS_TOKEN = (os.environ.get("FB_PAGE_ACCESS_TOKEN") or os.environ.get("FB_ACCESS_TOKEN") or "").strip()
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()

# Local config fallback if running locally
CONFIG_FILE = os.path.join(BASE_DIR, "fb_config.json")
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
            cfg = json.load(cf)
            if not FB_PAGE_ID:
                FB_PAGE_ID = cfg.get("FB_PAGE_ID", "").strip()
            if not FB_PAGE_ACCESS_TOKEN:
                FB_PAGE_ACCESS_TOKEN = (cfg.get("FB_PAGE_ACCESS_TOKEN") or cfg.get("FB_ACCESS_TOKEN") or "").strip()
            if not GEMINI_API_KEY:
                GEMINI_API_KEY = cfg.get("GEMINI_API_KEY", "").strip()
    except Exception as e:
        print(f"[WARN] Could not read fb_config.json: {e}")

# Check permanent token file fallback
PERM_TOKEN_FILE = os.path.join(BASE_DIR, "fb_permanent_token.txt")
if not FB_PAGE_ACCESS_TOKEN and os.path.exists(PERM_TOKEN_FILE):
    try:
        with open(PERM_TOKEN_FILE, "r", encoding="utf-8") as pf:
            FB_PAGE_ACCESS_TOKEN = pf.read().strip()
    except Exception:
        pass

# Fallback for Gemini key from Auto-Insta-Krishna
if not GEMINI_API_KEY:
    alt_gemini = os.path.join(BASE_DIR, "..", "Auto-Insta-Krishna", "gemini_key.txt")
    if os.path.exists(alt_gemini):
        try:
            with open(alt_gemini, "r", encoding="utf-8") as gf:
                GEMINI_API_KEY = gf.read().strip()
        except Exception:
            pass

def get_rich_long_fallback():
    """Generates a rich, soulful, human-first devotional caption (100% compliant with zero keyword stuffing rule)."""
    return """✨ ॐ नमो भगवते वासुदेवाय नमः ✨
🌿 पावन सनातन प्रभात दर्शन 🌿

आज के इस पावन प्रभात पर प्रभु के इस दिव्य अलौकिक स्वरूप के दर्शन कर अपने दिन को सकारात्मक ऊर्जा, शांति और दिव्यता से परिपूर्ण बनाएं।

🌸 आज का पावन विचार:
"ईश्वर पर अटूट विश्वास और शुद्ध कर्म ही जीवन की हर कठिन परिस्थिति से पार पाने का सबसे बड़ा संबल है। जब मन में भक्ति और हृदय में सच्चाई हो, तो हर मार्ग सुगम हो जाता है।"

जीवन के 3 पावन सूत्र:
• प्रत्येक परिस्थिति में धैर्य और ईश्वर पर विश्वास
• सत्य, प्रेम और निस्वार्थ सेवा का मार्ग
• अहंकार का त्याग और पूर्ण समर्पण का भाव

नित्य मंगल कामना व आशीर्वाद:
प्रभु की असीम कृपा सदैव आप और आपके सम्पूर्ण परिवार पर बनी रहे। घर में सुख, शांति, समृद्धि, उत्तम स्वास्थ्य और सकारात्मक ऊर्जा का वास हो।

👉 दर्शन का पुण्य लाभ प्राप्त करें और कमेंट बॉक्स में जय श्री राम / जय श्री कृष्ण लिखकर अपनी पावन हाजिरी अवश्य लगाएं! इस दिव्य दर्शन को अपने प्रियजनों के साथ शेयर करें। 🙏

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌿 भक्ति लेंस (Bhakti Lens) | सनातन धर्म नित्य दर्शन 🌿
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#BhaktiLens #SanatanDharma #DailyDarshan #ShubhPrabhat"""


def generate_devotional_caption(image_url):
    """Uses Gemini Vision AI to inspect image and generate a heartfelt spiritual caption and tags."""
    if not GEMINI_API_KEY or genai is None:
        print("[WARN] No GEMINI_API_KEY found, using rich long-form SEO fallback caption.")
        return get_rich_long_fallback()

    genai.configure(api_key=GEMINI_API_KEY)
    
    # Download image temporarily into memory for Gemini Vision (with curl fallback)
    img_bytes = None
    try:
        import subprocess, tempfile
        tmp_img = os.path.join(tempfile.gettempdir(), "bl_gemini_tmp.jpg")
        res = subprocess.run(["curl" if sys.platform != "win32" else "curl.exe", "-s", "-L", "-f", "--retry", "3", "-o", tmp_img, image_url], timeout=30)
        if res.returncode == 0 and os.path.exists(tmp_img) and os.path.getsize(tmp_img) > 1000:
            with open(tmp_img, "rb") as f_tmp:
                img_bytes = f_tmp.read()
            try:
                os.remove(tmp_img)
            except Exception:
                pass
    except Exception as ce:
        print(f"[WARN] curl download attempt: {ce}")

    if not img_bytes:
        try:
            r = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            if r.status_code == 200:
                img_bytes = r.content
        except Exception as e:
            print(f"[WARN] requests image fetch: {e}")

    prompt = """
आप एक अत्यंत ज्ञानी, विनम्र और भावपूर्ण सनातनी आध्यात्मिक लेखक हैं।
दी गई दिव्य छवि (Image) को गहराई से देखिए (पहचानिए कौन से देव/देवी, मंदिर, घाट, भाव या प्रसंग है - जैसे हनुमान जी, महादेव, श्री राम, श्री कृष्ण, गणेश जी, माँ दुर्गा आदि)।
Facebook पेज 'Bhakti Lens' के लिए एक बहुत ही सुंदर, लंबा, भावपूर्ण और 100% human-first पोस्ट तैयार कीजिए।

अनिवार्य संरचना:
1. पहली पंक्ति: देवता/दृश्य के अनुसार शक्तिशाली वैदिक मंत्र व जयकारा (जैसे: 🚩 ॐ हं हनुमते नमः | जय श्री राम 🚩 या 🔱 ॐ नमः शिवाय 🔱 या 🪷 ॐ नमो भगवते वासुदेवाय नमः 🪷)
2. परम पावन दैनिक दर्शन (4-5 पंक्तियाँ): इस स्वरूप के दर्शन से मन में उठने वाली श्रद्धा, भक्ति, शांति और आज का पावन आध्यात्मिक संदेश।
3. दृश्य व पावन भाव (3-4 पंक्तियाँ): छवि में दिखाई देने वाले मंदिर, घाट, दीप, प्रकृति या भाव का सजीव एवं हृदयस्पर्शी वर्णन।
4. आध्यात्मिक सुविचार व जीवन सीख (3 बिंदुवार सीख):
   • ईश्वर पर अटूट विश्वास और भक्ति का महत्व
   • कठिन समय में धैर्य, कर्म और आत्मबल
   • निस्वार्थ सेवा, शांति और सत्य का मार्ग
5. नित्य मंगल कामना व आशीर्वाद: "प्रभु की दिव्य कृपा सदैव आप और आपके पूरे परिवार पर बनी रहे। घर में सुख, शांति, अच्छा स्वास्थ्य और सकारात्मक ऊर्जा का वास हो।"
6. एंगेजमेंट कॉल (CTA): "👉 दर्शन का पुण्य लाभ प्राप्त करें और कमेंट में प्रभु का नाम लिखकर अपनी हाजिरी अवश्य लगाएं! इस दिव्य दर्शन को अपने प्रियजनों के साथ शेयर करें। 🙏"
7. पेज सिग्नेचर: 🌿 भक्ति लेंस (Bhakti Lens) | सनातन धर्म नित्य दर्शन 🌿
8. केवल 3 से 5 प्रासंगिक एवं स्वच्छ हैशटैग्स (जैसे: #BhaktiLens #SanatanDharma #DailyDarshan #ShubhPrabhat)।

महत्वपूर्ण नियम:
- कतई कोई 'Searches & Topics Covered' या कीवर्ड डंप नहीं लिखना है। पोस्ट पूरी तरह आत्मीय, भक्तिमय और मानवीय होनी चाहिए।
"""

    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            if img_bytes:
                response = model.generate_content(
                    [{"mime_type": "image/jpeg", "data": img_bytes}, prompt],
                    request_options={"timeout": 15}
                )
            else:
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": 15}
                )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[INFO] Gemini model {m} fallback: {e}")
            continue

    return get_rich_long_fallback()


def get_direct_page_access_token(page_id, token):
    """
    If the provided token is a User Access Token, automatically fetch the
    dedicated Page Access Token for this Page to avoid '#200 App not allowed
    to publish to other users timelines' error.
    """
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}?fields=access_token&access_token={token}"
        res = requests.get(url, timeout=15)
        data = res.json()
        if "access_token" in data:
            print(f"  -> [AUTH] Successfully resolved dedicated Page Access Token for Page {page_id}")
            return data["access_token"]
    except Exception as e:
        print(f"  [WARN] Page access token exchange attempt: {e}")
    return token


def post_to_facebook(image_url, caption):
    """Publishes photo + caption directly to Facebook Page via Graph API."""
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("❌ [ERROR] Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN!")
        print("   Please provide your Permanent Facebook Page Access Token in fb_config.json or Environment Variables.")
        return False

    # Automatically resolve dedicated Page Token
    effective_token = get_direct_page_access_token(FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN)

    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    payload = {
        "url": image_url,
        "caption": caption,
        "access_token": effective_token
    }

    try:
        res = requests.post(url, data=payload, timeout=60)
        res_data = res.json()
        if "id" in res_data:
            post_id = res_data.get("post_id", res_data["id"])
            print(f"  ✅ [SUCCESS] Published to Facebook Page successfully!")
            print(f"     Post ID: {post_id}")
            return True
        else:
            print(f"  ❌ [FB API ERROR]: {json.dumps(res_data, indent=2)}")
            return False
    except Exception as e:
        print(f"  ❌ [REQUEST ERROR]: {e}")
        return False


def main():
    print("=" * 65)
    print("  🌸 BHAKTI LENS - FACEBOOK AUTO POST ENGINE")
    print("=" * 65)

    if not os.path.exists(URLS_FILE):
        print(f"[INFO] No images_urls.txt found. Creating template...")
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("Please add image URLs to images_urls.txt or run image uploader.")
        return

    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]

    if not urls:
        print("⚠️ [QUEUE EMPTY] No pending images found in 'images_urls.txt'!")
        if os.path.exists(BACKUP_URLS_FILE):
            print("🔄 Reloading queue from backup pool for continuous auto-posting...")
            with open(BACKUP_URLS_FILE, "r", encoding="utf-8") as bf:
                b_urls = [line.strip() for line in bf if line.strip() and line.strip().startswith("http")]
            if b_urls:
                random.shuffle(b_urls)
                urls = b_urls[:]
                with open(URLS_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(urls) + "\n")
                print(f"✅ Reloaded {len(urls)} images from backup pool.")
            else:
                return
        else:
            return

    chosen_url = urls.pop(0)
    print(f"\n[1/3] Selected Image from Queue: {chosen_url}")

    print("\n[2/3] Analyzing image visual aesthetics with Gemini Vision AI...")
    caption = generate_devotional_caption(chosen_url)
    print("-----------------------------------------------------------------")
    print(caption[:300] + ("..." if len(caption) > 300 else ""))
    print("-----------------------------------------------------------------")

    print("\n[3/3] Posting to Facebook Page 'Bhakti Lens'...")
    success = post_to_facebook(chosen_url, caption)

    if success:
        # Move URL to used
        with open(USED_URLS_FILE, "a", encoding="utf-8") as f:
            f.write(chosen_url + "\n")
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(urls) + "\n")
        print(f"  -> Queue updated. Remaining in active queue: {len(urls)}")
    else:
        print("  -> Post failed. URL preserved in queue for retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()

