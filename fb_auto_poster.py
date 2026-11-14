#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BHAKTI LENS - FACEBOOK & INSTAGRAM DUAL AUTO POSTER
=============================================================================
- Reads unposted 3:4 devotional image URLs from 'images_urls.txt'
- Uses Google Gemini Vision AI to inspect image aesthetics
- Crafts short, clean, deeply spiritual devotional captions (NO extra long fluff)
- Posts simultaneously to:
    1. Facebook Page ('Bhakti Lens')
    2. Instagram Professional Account ('@Bhakti_Lens1')
- Automatically manages queue: moves posted URL to 'used_urls.txt'
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
IG_ACCOUNT_ID = (os.environ.get("IG_ACCOUNT_ID") or "").strip()
IG_USERNAME = (os.environ.get("IG_USERNAME") or "Bhakti_Lens1").strip()
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()

# Local config fallback if running locally
CONFIG_FILE = os.path.join(BASE_DIR, "fb_config.json")
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
            cfg = json.load(cf)
            if not FB_PAGE_ID:
                FB_PAGE_ID = str(cfg.get("FB_PAGE_ID", "")).strip()
            if not FB_PAGE_ACCESS_TOKEN:
                FB_PAGE_ACCESS_TOKEN = (cfg.get("FB_PAGE_ACCESS_TOKEN") or cfg.get("FB_ACCESS_TOKEN") or "").strip()
            if not IG_ACCOUNT_ID:
                IG_ACCOUNT_ID = str(cfg.get("IG_ACCOUNT_ID", "")).strip()
            if not IG_USERNAME and cfg.get("IG_USERNAME"):
                IG_USERNAME = str(cfg.get("IG_USERNAME")).strip()
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


def get_short_devotional_fallback():
    """Generates a clean, short, aesthetic devotional caption (zero clutter)."""
    return """✨ ॐ नमो भगवते वासुदेवाय नमः ✨

प्रभु के इस दिव्य पावन स्वरूप के दर्शन कर अपने दिन की शुरुआत सकारात्मक ऊर्जा और शांति से करें। प्रभु की कृपा सदैव आप और आपके परिवार पर बनी रहे। 🌸🙏

👉 कमेंट में 'जय श्री राम' / 'जय श्री कृष्ण' लिखकर प्रभु का आशीर्वाद प्राप्त करें!

🌿 Bhakti Lens | सनातन धर्म 🌿
#BhaktiLens #SanatanDharma #DailyDarshan #Bhakti"""


def generate_devotional_caption(image_url):
    """Uses Gemini Vision AI to inspect image and generate a short, clean, impactful spiritual caption."""
    if not GEMINI_API_KEY or genai is None:
        print("[WARN] No GEMINI_API_KEY found or genai missing, using short fallback caption.")
        return get_short_devotional_fallback()

    import io, subprocess, tempfile

    # Step 1: Download and prepare image for fast vision processing
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
आप एक सनातनी आध्यात्मिक लेखक हैं।
दी गई छवि (Image) को देखकर पहचानिए कि इसमें कौन से देव/देवी या पावन दृश्य हैं (जैसे: श्री राम, महादेव, श्री कृष्ण, हनुमान जी, माँ दुर्गा आदि)।
'Bhakti Lens' (@Bhakti_Lens1) के लिए एक अत्यंत सुंदर, संक्षिप्त (Short & Crisp), भावपूर्ण पोस्ट तैयार कीजिए।

अनिवार्य संरचना (बहुत ही संक्षिप्त रखें, अधिकतम 35-50 शब्द):
1. शीर्ष पंक्ति: देवता के अनुसार 1 शक्तिशाली पावन जयकारा / मंत्र (जैसे: 🚩 ॐ श्री रामाय नमः 🚩 या 🔱 हर हर महादेव 🔱 या 🪷 ॐ नमो भगवते वासुदेवाय नमः 🪷)
2. 2-3 पंक्तियों का सुंदर, मधुर आध्यात्मिक भाव / आशीर्वाद (बिना किसी लंबे पैराग्राफ या कहानी के)
3. एक पंक्ति का एंगेजमेंट कॉल: '👉 कमेंट में प्रभु का नाम लिखकर पावन हाजिरी लगाएं! 🙏'
4. पेज सिग्नेचर:
🌿 Bhakti Lens | सनातन धर्म 🌿
5. केवल 4-5 प्रासंगिक हैशटैग्स: #BhaktiLens #SanatanDharma #DailyDarshan #Bhakti

सख्त नियम:
- कोई लंबा निबंध, कोई 4-5 पॉइंट्स/बुलेटिन, कोई कहानी, कोई व्यर्थ टेक्स्ट बिल्कुल न लिखें।
- पोस्ट छोटी, मीठी, आकर्षक और तुरंत पढ़ने योग्य होनी चाहिए।
"""

    # Primary: New official google-genai SDK
    if hasattr(genai, "Client"):
        for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite"]:
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
                except Exception:
                    continue
        except Exception as lge:
            print(f"[WARN] google.generativeai error: {lge}")

    if os.path.exists(tmp_img):
        try:
            os.remove(tmp_img)
        except Exception:
            pass

    return get_short_devotional_fallback()


def post_to_facebook(image_url, caption):
    """Publishes photo + caption directly to Facebook Page via Graph API."""
    if not FB_PAGE_ACCESS_TOKEN:
        print("❌ [FB ERROR] Missing FB_PAGE_ACCESS_TOKEN!")
        return False, None

    target_id = "me"
    page_name = "Bhakti Lens"
    try:
        me_res = requests.get(f"https://graph.facebook.com/v21.0/me?access_token={FB_PAGE_ACCESS_TOKEN}", timeout=15).json()
        if "id" in me_res:
            target_id = me_res["id"]
            page_name = me_res.get("name", "Bhakti Lens")
            print(f"  -> [FB AUTH] Connected to Facebook Page: '{page_name}' (ID: {target_id})")
        else:
            if FB_PAGE_ID:
                target_id = FB_PAGE_ID
    except Exception:
        if FB_PAGE_ID:
            target_id = FB_PAGE_ID

    url = f"https://graph.facebook.com/v21.0/{target_id}/photos"
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
            print(f"  ✅ [FB SUCCESS] Published to Facebook Page '{page_name}'! (Post ID: {post_id})")
            return True, target_id
        else:
            print(f"  ❌ [FB API ERROR]: {json.dumps(res_data, indent=2)}")
            return False, target_id
    except Exception as e:
        print(f"  ❌ [FB REQUEST ERROR]: {e}")
        return False, target_id


def get_instagram_account_id(page_id, token):
    """Fetches connected Instagram Business/Creator Account ID for the Facebook Page."""
    if IG_ACCOUNT_ID:
        return IG_ACCOUNT_ID
    try:
        target = page_id if page_id and page_id != "me" else (FB_PAGE_ID or "me")
        url = f"https://graph.facebook.com/v21.0/{target}?fields=instagram_business_account&access_token={token}"
        res = requests.get(url, timeout=15).json()
        if "instagram_business_account" in res and "id" in res["instagram_business_account"]:
            ig_id = res["instagram_business_account"]["id"]
            print(f"  -> [IG AUTH] Connected Instagram Account ID: {ig_id} (@{IG_USERNAME})")
            return ig_id
        else:
            print(f"  -> [IG AUTH] instagram_business_account field: {res}")
    except Exception as e:
        print(f"  [WARN] Could not auto-detect Instagram Account ID: {e}")
    return None


def post_to_instagram(image_url, caption, ig_id, token):
    """Publishes photo + caption directly to Instagram Professional Account via Graph API."""
    if not ig_id:
        print(f"  ⚠️ [IG SKIPPED] Instagram Business ID not linked to FB Page yet.")
        print(f"     Please link Instagram '@{IG_USERNAME}' with 'Bhakti Lens' Facebook Page in Meta Business Suite.")
        return False

    try:
        # Step 1: Create media container
        create_url = f"https://graph.facebook.com/v21.0/{ig_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": token
        }
        c_res = requests.post(create_url, data=payload, timeout=30).json()
        if "id" not in c_res:
            print(f"  ❌ [IG CONTAINER ERROR]: {json.dumps(c_res, indent=2)}")
            return False

        container_id = c_res["id"]
        print(f"  -> Instagram Media Container created: {container_id}. Waiting for processing...")
        time.sleep(8)

        # Step 2: Publish media container
        pub_url = f"https://graph.facebook.com/v21.0/{ig_id}/media_publish"
        pub_payload = {
            "creation_id": container_id,
            "access_token": token
        }
        p_res = requests.post(pub_url, data=pub_payload, timeout=30).json()
        if "id" in p_res:
            print(f"  ✅ [IG SUCCESS] Published to Instagram @{IG_USERNAME} successfully! (Media ID: {p_res['id']})")
            return True
        else:
            print(f"  ❌ [IG PUBLISH ERROR]: {json.dumps(p_res, indent=2)}")
            return False
    except Exception as e:
        print(f"  ❌ [IG REQUEST ERROR]: {e}")
        return False


def main():
    print("=" * 65)
    print("  🌸 BHAKTI LENS - FACEBOOK & INSTAGRAM DUAL AUTO POSTER")
    print(f"  Channels: Facebook ('Bhakti Lens') + Instagram (@{IG_USERNAME})")
    print("=" * 65)

    if not os.path.exists(URLS_FILE):
        print(f"[INFO] No images_urls.txt found. Creating template...")
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("")
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

    print("\n[2/3] Generating clean, concise devotional caption with Gemini Vision AI...")
    caption = generate_devotional_caption(chosen_url)
    print("-----------------------------------------------------------------")
    print(caption)
    print("-----------------------------------------------------------------")

    print(f"\n[3/3] Publishing to Facebook ('Bhakti Lens') and Instagram (@{IG_USERNAME})...")
    fb_ok, page_id = post_to_facebook(chosen_url, caption)

    ig_id = get_instagram_account_id(page_id, FB_PAGE_ACCESS_TOKEN)
    ig_ok = post_to_instagram(chosen_url, caption, ig_id, FB_PAGE_ACCESS_TOKEN)

    if fb_ok or ig_ok:
        # Move URL to used
        with open(USED_URLS_FILE, "a", encoding="utf-8") as f:
            f.write(chosen_url + "\n")
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(urls) + "\n")
        print(f"\n🎉 [COMPLETE] Queue updated. Remaining in active queue: {len(urls)}")
    else:
        print("\n❌ [FAILED] Both Facebook and Instagram publishing failed. URL preserved in queue.")
        sys.exit(1)


if __name__ == "__main__":
    main()
