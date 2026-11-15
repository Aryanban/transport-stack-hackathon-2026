#!/usr/bin/env python3
"""
Delhi Transport Stack Data Downloader & Synchronizer
Fetches latest metadata, sample datasets, and documentation from DTS API.
"""

import argparse
import json
import os
import shutil
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs" / "metadata"
DTS_API = "https://dts-backend.transportstack.in/api"

def sync_dts(max_datasets: int = 18):
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    print(f"Connecting to Delhi Transport Stack at {DTS_API}...")
    for did in range(1, max_datasets + 1):
        try:
            url = f"{DTS_API}/dataset/detail?id={did}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            res = urllib.request.urlopen(req)
            data = json.loads(res.read().decode())
            name = data.get("name")
            seq = data.get("sequenceId")
            print(f"[{did}] Found {seq}: {name}")

            docs = data.get("documentsByType", {})
            for dtype, doclist in docs.items():
                for doc in doclist:
                    furl = f"https://dts-backend.transportstack.in{doc.get('url', '')}"
                    file_key = doc.get("fileKey", "")
                    title = doc.get("title", "")
                    target_dir = DOCS_DIR if (file_key.endswith(".pdf") or file_key.endswith(".docx")) else DATA_DIR
                    clean_name = f"{did}_{title}_{file_key}".replace(" ", "_").replace("/", "_")
                    dest_file = target_dir / clean_name

                    if not dest_file.exists():
                        print(f"   Downloading {title} -> {clean_name}...")
                        try:
                            urllib.request.urlretrieve(furl, dest_file)
                            print(f"   ✓ OK ({dest_file.stat().st_size} bytes)")
                        except Exception as e:
                            print(f"   ✗ Download error: {e}")
        except Exception as e:
            pass

    print("\nSync completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delhi Transport Stack sync tool")
    parser.add_argument("--max", type=int, default=18, help="Max dataset IDs to query")
    args = parser.parse_args()
    sync_dts(args.max)
