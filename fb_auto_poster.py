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
import google.generativeai as genai

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URLS_FILE = os.path.join(BASE_DIR, "images_urls.txt")
USED_URLS_FILE = os.path.join(BASE_DIR, "used_urls.txt")
BACKUP_URLS_FILE = os.path.join(BASE_DIR, "images_urls_backup.txt")

# Environment / Credentials
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Local config fallback if running locally
CONFIG_FILE = os.path.join(BASE_DIR, "fb_config.json")
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
            cfg = json.load(cf)
            if not FB_PAGE_ID:
                FB_PAGE_ID = cfg.get("FB_PAGE_ID", "")
            if not FB_PAGE_ACCESS_TOKEN:
                FB_PAGE_ACCESS_TOKEN = cfg.get("FB_PAGE_ACCESS_TOKEN", "")
            if not GEMINI_API_KEY:
                GEMINI_API_KEY = cfg.get("GEMINI_API_KEY", "")
    except Exception as e:
        print(f"[WARN] Could not read fb_config.json: {e}")


def generate_devotional_caption(image_url):
    """Uses Gemini Vision AI to inspect image and generate a heartfelt spiritual caption & tags."""
    if not GEMINI_API_KEY:
        print("[WARN] No GEMINI_API_KEY found, using serene default caption.")
        return (
            "🙏 ॐ नमो भगवते वासुदेवाय नमः 🙏\n\n"
            "ईश्वर का स्मरण हर विपत्ति को शक्ति और हर अंधकार को प्रकाश में बदल देता है।\n"
            "आज का दिन आपके और आपके परिवार के लिए सुख, शांति और समृद्धि लेकर आए।\n\n"
            "✨ भक्ति लेंस (Bhakti Lens) ✨\n\n"
            "#Bhakti #BhaktiLens #SanatanDharma #DailyDarshan #SpiritualVibes #Mandir #Blessings #HarHarMahadev #JaiShreeRam #RadheKrishna"
        )

    genai.configure(api_key=GEMINI_API_KEY)
    
    # Download image temporarily into memory for Gemini Vision
    try:
        r = requests.get(image_url, timeout=30)
        r.raise_for_status()
        img_bytes = r.content
    except Exception as e:
        print(f"[WARN] Failed to fetch image for Gemini vision: {e}")
        img_bytes = None

    prompt = """
आप एक अत्यंत ज्ञानी, विनम्र और भावपूर्ण सनातनी आध्यात्मिक लेखक हैं।
इस दी गई दिव्य छवि (Image) को ध्यानपूर्वक देखिए और Facebook पेज 'Bhakti Lens' के लिए एक बहुत ही सुंदर, मनमोहक और वायरल होने वाला भक्तिमय पोस्ट लिखिए।

संरचना (Format):
1. पहली पंक्ति: देवता/दृश्य के अनुसार एक शक्तिशाली मंत्र या जयकारा (जैसे: 🌸 जय श्री राम 🌸 / 🔱 हर हर महादेव 🔱 / 🪷 जय श्री कृष्ण 🪷)
2. मुख्य भाव (3-4 पंक्तियाँ): इस छवि के दर्शन से मन में उठने वाला दिव्य भाव, सकारात्मक ऊर्जा और आज का सुंदर आध्यात्मिक संदेश।
3. जीवन दर्शन / प्रेरणादायक सीख (2 पंक्तियाँ): ईश्वर पर विश्वास, कर्म और शांति का एक मीठा संदेश।
4. आशीर्वाद पंक्ति: "प्रभु की कृपा सदैव आप और आपके परिवार पर बनी रहे। कमेंट में प्रभु का नाम लिखकर दर्शन का लाभ लें। 🙏"
5. पेज सिग्नेचर: 🌿 भक्ति लेंस (Bhakti Lens) | नित्य दर्शन 🌿
6. 15 से 20 ट्रेंडिंग, उच्च रीच वाले हिंदी और इंग्लिश भक्ति हैशटैग्स (जैसे: #BhaktiLens #Sanatan #DailyDarshan #Mahadev #Krishna #Ram #Bhakti #Hinduism #TempleVibes #DivineEnergy आदि)

नोट: शुद्ध, सरल, आत्मीय और हृदयस्पर्शी हिंदी में लिखें। किसी भ्रामक या अनावश्यक बात का उल्लेख न करें।
"""

    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            if img_bytes:
                response = model.generate_content([
                    {"mime_type": "image/jpeg", "data": img_bytes},
                    prompt
                ])
            else:
                response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[INFO] Gemini model {m} fallback: {e}")
            continue

    # Fallback caption
    return (
        "🙏 जय श्री राम | हर हर महादेव | ॐ नमो भगवते वासुदेवाय 🙏\n\n"
        "जिनके हृदय में ईश्वर का वास होता है, उनके जीवन में कभी अंधेरा नहीं हो सकता।\n"
        "प्रभु के इस दिव्य स्वरूप के दर्शन करें और उनका आशीर्वाद प्राप्त करें।\n\n"
        "🌿 भक्ति लेंस (Bhakti Lens) | नित्य दर्शन 🌿\n\n"
        "#BhaktiLens #Sanatan #DailyDarshan #HarHarMahadev #JaiShreeRam #RadheKrishna #Hinduism #SpiritualVibes #Blessings"
    )


def post_to_facebook(image_url, caption):
    """Publishes photo + caption directly to Facebook Page via Graph API."""
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("❌ [ERROR] Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN!")
        print("   Please provide your Permanent Facebook Page Access Token in fb_config.json or Environment Variables.")
        return False

    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
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


if __name__ == "__main__":
    main()
