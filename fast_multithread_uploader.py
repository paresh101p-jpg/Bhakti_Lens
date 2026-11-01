#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
High-Speed Multi-Threaded Batch Uploader & Logo Watermarker for Bhakti Lens
Brands images with Logo.png, uploads to Catbox CDN, appends to images_urls.txt,
and moves to images/uploaded/.
"""

import os
import sys
import time
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "images")
UPLOADED_DIR = os.path.join(IMG_DIR, "uploaded")
URLS_FILE = os.path.join(BASE_DIR, "images_urls.txt")
BACKUP_URLS_FILE = os.path.join(BASE_DIR, "images_urls_backup.txt")
LOGO_PATH = os.path.join(BASE_DIR, "Logo.png")

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(UPLOADED_DIR, exist_ok=True)

curl_path = "curl"
if sys.platform == "win32" and os.path.exists(r"C:\Windows\System32\curl.exe"):
    curl_path = r"C:\Windows\System32\curl.exe"

lock = threading.Lock()
processed_count = 0
success_count = 0
failed_count = 0

def apply_logo_watermark(base_image_path, output_image_path):
    if not os.path.exists(LOGO_PATH):
        return base_image_path

    try:
        base = Image.open(base_image_path).convert("RGBA")
        logo = Image.open(LOGO_PATH).convert("RGBA")

        w, h = base.size
        logo_w = int(w * 0.16)
        logo_h = int(logo.size[1] * (logo_w / logo.size[0]))
        logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.92))
        logo.putalpha(alpha)

        margin = int(w * 0.035)
        pos = (w - logo_w - margin, margin)

        watermarked = Image.new("RGBA", base.size)
        watermarked.paste(base, (0, 0))
        watermarked.paste(logo, pos, mask=logo)

        final_rgb = watermarked.convert("RGB")
        final_rgb.save(output_image_path, "JPEG", quality=95, optimize=True)
        return output_image_path
    except Exception as e:
        return base_image_path

def upload_file_to_catbox(file_path):
    cmd = [
        curl_path, "-k", "-s",
        "-F", "reqtype=fileupload",
        "-F", "userhash=",
        "-F", f"fileToUpload=@{file_path}",
        "https://catbox.moe/user/api.php"
    ]
    for _ in range(3):
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            url = res.stdout.strip()
            if url.startswith("https://files.catbox.moe/"):
                return url
        except Exception:
            pass
        time.sleep(1)
    return None

def process_single_image(idx, fname, total):
    global processed_count, success_count, failed_count
    fpath = os.path.join(IMG_DIR, fname)
    if not os.path.exists(fpath):
        return None

    temp_branded = os.path.join(IMG_DIR, f"temp_brand_{idx}_{threading.get_ident()}.jpg")
    final_path = apply_logo_watermark(fpath, temp_branded)
    url = upload_file_to_catbox(final_path)

    if os.path.exists(temp_branded):
        try: os.remove(temp_branded)
        except Exception: pass

    with lock:
        processed_count += 1
        if url:
            success_count += 1
            with open(URLS_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            with open(BACKUP_URLS_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            dest = os.path.join(UPLOADED_DIR, fname)
            try:
                os.replace(fpath, dest)
            except Exception:
                pass
            print(f"[{processed_count}/{total}] ✅ {fname[:35]} -> {url}")
        else:
            failed_count += 1
            print(f"[{processed_count}/{total}] ❌ Failed: {fname}")

    return url

def main():
    print("=" * 70)
    print("  🚀 BHAKTI LENS - FAST MULTI-THREADED FACEBOOK QUEUE UPLOADER")
    print("=" * 70)

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [f for f in os.listdir(IMG_DIR) if os.path.isfile(os.path.join(IMG_DIR, f)) and f.lower().endswith(exts) and not f.startswith("temp_")]

    total = len(files)
    print(f"[FOUND] {total} new devotional image(s) to brand and upload.")

    if total == 0:
        print("[INFO] Queue is already up to date. Zero pending images.")
        return

    # Use 8 parallel workers for high-speed concurrent uploads
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_image, idx, fname, total) for idx, fname in enumerate(files, 1)]
        for f in as_completed(futures):
            pass

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"🎉 BATCH COMPLETE in {elapsed:.1f}s ({elapsed/60:.2f} mins)!")
    print(f"  - Successfully Uploaded: {success_count} / {total}")
    print(f"  - Failed: {failed_count}")
    print("=" * 70)

if __name__ == "__main__":
    main()

