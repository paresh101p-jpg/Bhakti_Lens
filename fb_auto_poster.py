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
    from google import genai
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        genai = None

try:
    from PIL import Image
except ImportError:
    Image = None

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
    """Uses Gemini Vision AI to inspect image and generate a rich, heartfelt spiritual caption and tags."""
    if not GEMINI_API_KEY or genai is None:
        print("[WARN] No GEMINI_API_KEY found or genai missing, using rich long-form fallback caption.")
        return get_rich_long_fallback()

    import io, subprocess, tempfile

    # Step 1: Download and prepare image with thumbnail resizing for fast vision processing
    pil_img = None
    tmp_img = os.path.join(tempfile.gettempdir(), f"bl_gemini_tmp_{int(time.time())}.jpg")
    try:
        curl_bin = "curl.exe" if sys.platform == "win32" else "curl"
        res = subprocess.run([curl_bin, "-s", "-L", "-f", "--retry", "3", "-o", tmp_img, image_url], timeout=30)
        if res.returncode == 0 and os.path.exists(tmp_img) and os.path.getsize(tmp_img) > 1000:
            if Image:
                pil_img = Image.open(tmp_img)
                pil_img.load()
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                pil_img.thumbnail((512, 512))
    except Exception as ce:
        print(f"[WARN] curl image download error: {ce}")

    if pil_img is None:
        try:
            r = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            if r.status_code == 200:
                if Image:
                    pil_img = Image.open(io.BytesIO(r.content))
                    pil_img.load()
                    if pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")
                    pil_img.thumbnail((512, 512))
        except Exception as re:
            print(f"[WARN] requests image download error: {re}")

    prompt = """
आप एक अत्यंत ज्ञानी, विनम्र और भावपूर्ण सनातनी आध्यात्मिक लेखक हैं।
दी गई दिव्य छवि (Image) को गहराई से देखिए और पहचानिए कि इसमें कौन से देव/देवी, मंदिर, घाट, भाव, आभूषण, वेशभूषा, आयुध या पावन दृश्य है (जैसे: श्री राम, महादेव, श्री कृष्ण, हनुमान जी, माँ दुर्गा, गणेश जी, गंगा आरती आदि)।
Facebook पेज 'Bhakti Lens' के लिए एक बहुत ही सुंदर, विस्तृत (Long), भावपूर्ण और 100% human-first पोस्ट तैयार कीजिए।

अनिवार्य संरचना:
1. शीर्ष पंक्ति: देवता/स्वरूप के अनुसार शक्तिशाली वैदिक मंत्र व पावन जयकारा (जैसे: 🚩 ॐ श्री रामाय नमः | सियावर रामचंद्र की जय 🚩 या 🔱 ॐ नमः शिवाय 🔱 | हर हर महादेव 🚩 या 🪷 ॐ नमो भगवते वासुदेवाय नमः 🪷)
2. पावन श्लोक / चौपाई व सरल अर्थ: स्वरूप से संबंधित एक प्रामाणिक संस्कृत श्लोक या चौपाई तथा उसका सहज, सुंदर हिंदी अर्थ।
3. दिव्य दर्शन व छवि का सजीव वर्णन (विस्तृत पैराग्राफ): छवि में प्रभु के स्वरूप (मुखमंडल का तेज, नयन, वेशभूषा, आयुध/अलंकार, पृष्ठभूमि के मंदिर, शिखर, दीप, सूर्योदय/प्राकृतिक छटा) का अत्यंत सुंदर, मंत्रमुग्ध करने वाला सजीव वर्णन।
4. पौराणिक कथा / आध्यात्मिक रहस्य: इस स्वरूप की महिमा, मर्यादा, शक्ति, भक्ति या इतिहास से जुड़ा एक गहरा आध्यात्मिक प्रसंग।
5. जीवन के 4 पावन सूत्र व सीख (बिंदुवार):
   • मर्यादा, संयम और सत्यनिष्ठा
   • कठिन से कठिन परिस्थिति में धैर्य और धर्म पर अडिग रहना
   • अहंकार का त्याग और समर्पण भाव
   • जन-कल्याण और निस्वार्थ सेवा
6. नित्य मंगल कामना व आशीर्वाद: 'प्रभु की असीम कृपा सदैव आप और आपके सम्पूर्ण परिवार पर बनी रहे। आपके जीवन में सुख, शांति, समृद्धि, उत्तम स्वास्थ्य और सकारात्मक ऊर्जा का वास हो।'
7. एंगेजमेंट कॉल (CTA): '👉 आज के इस पावन दर्शन का पुण्य लाभ प्राप्त करें और कमेंट बॉक्स में प्रभु का नाम लिखकर अपनी पावन हाजिरी अवश्य लगाएं! इस दिव्य दर्शन को अपने परिजनों और मित्रों के साथ साझा करें। 🙏'
8. पेज सिग्नेचर:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌿 भक्ति लेंस (Bhakti Lens) | सनातन धर्म नित्य दर्शन 🌿
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. केवल 4-5 स्वच्छ एवं प्रासंगिक हैशटैग्स (जैसे: #BhaktiLens #SanatanDharma #DailyDarshan #ShubhPrabhat)

महत्वपूर्ण नियम:
- कतई कोई 'Searches & Topics Covered' या कीवर्ड डंप नहीं लिखना है।
- कोई फ्रीक्वेंसी नंबर (432Hz/528Hz) नहीं लिखना है।
- भाषा शुद्ध, गरिमामयी, भावपूर्ण, आत्मीय और लंबी (Long & Deep) होनी चाहिए।
"""

    # Primary: New official google-genai SDK with modern models
    if hasattr(genai, "Client"):
        for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash"]:
            try:
                client = genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": 60000})
                contents = [pil_img, prompt] if pil_img is not None else [prompt]
                response = client.models.generate_content(model=m, contents=contents)
                if response and response.text:
                    if os.path.exists(tmp_img):
                        try:
                            os.remove(tmp_img)
                        except Exception:
                            pass
                    return response.text.strip()
            except Exception as me:
                print(f"[INFO] google.genai model {m} attempt: {me}")
                continue

    # Secondary fallback: Legacy google.generativeai SDK
    if hasattr(genai, "configure") and hasattr(genai, "GenerativeModel"):
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            for m in ["gemini-1.5-flash", "gemini-1.5-pro"]:
                try:
                    model = genai.GenerativeModel(m)
                    contents = [pil_img, prompt] if pil_img is not None else prompt
                    response = model.generate_content(contents, request_options={"timeout": 30})
                    if response and response.text:
                        if os.path.exists(tmp_img):
                            try:
                                os.remove(tmp_img)
                            except Exception:
                                pass
                        return response.text.strip()
                except Exception as lme:
                    print(f"[INFO] google.generativeai model {m} attempt: {lme}")
                    continue
        except Exception as lge:
            print(f"[WARN] google.generativeai error: {lge}")

    if os.path.exists(tmp_img):
        try:
            os.remove(tmp_img)
        except Exception:
            pass

    return get_rich_long_fallback()


def post_to_facebook(image_url, caption):
    """Publishes photo + caption directly to Facebook Page via Graph API."""
    if not FB_PAGE_ACCESS_TOKEN:
        print("❌ [ERROR] Missing FB_PAGE_ACCESS_TOKEN!")
        print("   Please provide your Permanent Facebook Page Access Token in fb_config.json or Environment Variables.")
        return False

    # Check token identity via /me to automatically resolve the correct Page endpoint
    target_id = "me"
    page_name = "Bhakti Lens"
    try:
        me_res = requests.get(f"https://graph.facebook.com/v19.0/me?access_token={FB_PAGE_ACCESS_TOKEN}", timeout=15).json()
        if "id" in me_res:
            target_id = me_res["id"]
            page_name = me_res.get("name", "Bhakti Lens")
            print(f"  -> [AUTH] Connected to Facebook Page: '{page_name}' (ID: {target_id})")
        else:
            print(f"  -> [AUTH] /me query info: {me_res}")
            if FB_PAGE_ID:
                target_id = FB_PAGE_ID
    except Exception as me_err:
        print(f"  [WARN] /me lookup failed: {me_err}")
        if FB_PAGE_ID:
            target_id = FB_PAGE_ID

    url = f"https://graph.facebook.com/v19.0/{target_id}/photos"
    payload = {
        "url": image_url,
        "caption": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }

    try:
        res = requests.post(url, data=payload, timeout=60)
        res_data = res.json()
        if "id" in res_data:
            post_id = res_data.get("post_id", res_data["id"])
            print(f"  ✅ [SUCCESS] Published to Facebook Page '{page_name}' successfully!")
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

