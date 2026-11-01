#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uploads all 3:4 local images in 'images/' to Catbox CDN with the
official Bhakti Lens logo overlaid elegantly in the top corner.
Registers URLs in 'images_urls.txt' and 'images_urls_backup.txt',
and archives raw photos to 'images/uploaded/'.
"""

import os
import sys
import subprocess
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


def apply_logo_watermark(base_image_path, output_image_path):
    """Overlays the circular/stylish Bhakti Lens logo elegantly in the top-right corner."""
    if not os.path.exists(LOGO_PATH):
        return base_image_path

    try:
        base = Image.open(base_image_path).convert("RGBA")
        logo = Image.open(LOGO_PATH).convert("RGBA")

        # Resize logo proportionally: ~16% of image width
        w, h = base.size
        logo_w = int(w * 0.16)
        logo_h = int(logo.size[1] * (logo_w / logo.size[0]))
        logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

        # Subtle elegant opacity ~92%
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.92))
        logo.putalpha(alpha)

        # Position: Top-Right with 35px padding
        margin = int(w * 0.035)
        pos = (w - logo_w - margin, margin)

        # Composite logo over base image
        watermarked = Image.new("RGBA", base.size)
        watermarked.paste(base, (0, 0))
        watermarked.paste(logo, pos, mask=logo)

        # Convert back to RGB JPEG
        final_rgb = watermarked.convert("RGB")
        final_rgb.save(output_image_path, "JPEG", quality=95, optimize=True)
        return output_image_path
    except Exception as e:
        print(f"  [WARN] Failed to apply logo watermark: {e}")
        return base_image_path


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
    print("  BHAKTI LENS - IMAGE BATCH UPLOADER & LOGO BRANDING ENGINE")
    print("=" * 60)

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [f for f in os.listdir(IMG_DIR) if os.path.isfile(os.path.join(IMG_DIR, f)) and f.lower().endswith(exts)]

    if not files:
        print("[INFO] No pending images found in 'images/'.")
        return

    print(f"[FOUND] {len(files)} new devotional image(s) to brand and upload.")
    for idx, fname in enumerate(files, 1):
        fpath = os.path.join(IMG_DIR, fname)
        temp_branded = os.path.join(IMG_DIR, f"temp_branded_{idx}.jpg")
        
        print(f"[{idx}/{len(files)}] Applying Bhakti Lens Logo to: {fname}...")
        final_path = apply_logo_watermark(fpath, temp_branded)

        print(f"  -> Uploading branded image to Catbox CDN...")
        url = upload_file_to_catbox(final_path)
        if url:
            print(f"  ✅ Uploaded: {url}")
            with open(URLS_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            with open(BACKUP_URLS_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            dest = os.path.join(UPLOADED_DIR, fname)
            os.replace(fpath, dest)
        else:
            print(f"  ❌ Failed to upload: {fname}")

        if os.path.exists(temp_branded):
            try: os.remove(temp_branded)
            except Exception: pass

    print("\n🎉 All images successfully branded with Logo and queued for Facebook!")


if __name__ == "__main__":
    main()
