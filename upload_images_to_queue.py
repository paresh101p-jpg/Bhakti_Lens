#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uploads all 3:4 local images in 'images/' to Catbox CDN,
registers URLs in 'images_urls.txt' and 'images_urls_backup.txt',
and archives them to 'images/uploaded/' to keep workspace clean.
"""

import os
import sys
import subprocess

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "images")
UPLOADED_DIR = os.path.join(IMG_DIR, "uploaded")
URLS_FILE = os.path.join(BASE_DIR, "images_urls.txt")
BACKUP_URLS_FILE = os.path.join(BASE_DIR, "images_urls_backup.txt")

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(UPLOADED_DIR, exist_ok=True)

def upload_file_to_catbox(file_path):
    curl_path = "curl"
    if sys.platform == "win32" and os.path.exists(r"C:\Windows\System32\curl.exe"):
        curl_path = r"C:\Windows\System32\curl.exe"

    cmd = [
        curl_path, "-k", "-s",
        "-F", "reqtype=fileupload",
        "-F", f"fileToUpload=@{file_path}",
        "https://catbox.moe/user/api.php"
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
        url = res.stdout.strip()
        if url.startswith("https://files.catbox.moe/"):
            return url
    except Exception as e:
        print(f"  [ERROR] Catbox upload: {e}")
    return None

def main():
    print("=" * 60)
    print("  BHAKTI LENS - IMAGE BATCH UPLOADER & CDN SYNC")
    print("=" * 60)

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [f for f in os.listdir(IMG_DIR) if os.path.isfile(os.path.join(IMG_DIR, f)) and f.lower().endswith(exts)]

    if not files:
        print("[INFO] No pending images found in 'images/'. Add some 3:4 photos here!")
        return

    print(f"[FOUND] {len(files)} new devotional image(s) to process.")
    for idx, fname in enumerate(files, 1):
        fpath = os.path.join(IMG_DIR, fname)
        print(f"[{idx}/{len(files)}] Uploading: {fname}...")
        url = upload_file_to_catbox(fpath)
        if url:
            print(f"  ✅ Uploaded: {url}")
            with open(URLS_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            with open(BACKUP_URLS_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            # Move to uploaded
            dest = os.path.join(UPLOADED_DIR, fname)
            os.replace(fpath, dest)
        else:
            print(f"  ❌ Failed to upload: {fname}")

    print("\n🎉 All images successfully synced to CDN and queued for Facebook posting!")

if __name__ == "__main__":
    main()
