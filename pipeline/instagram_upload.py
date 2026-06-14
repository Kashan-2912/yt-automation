"""Upload MP4 to Instagram Reels via official Meta Graph API.

Requires two env variables:
  INSTAGRAM_ACCOUNT_ID
  INSTAGRAM_ACCESS_TOKEN
"""
from __future__ import annotations

import os
import time
from pathlib import Path
import httpx

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def upload_to_tmpfiles(video_path: Path) -> str:
    """Upload a local file to tmpfiles.org and return a direct download URL."""
    upload_url = "https://tmpfiles.org/api/v1/upload"
    print(f"   [Instagram] Uploading video to tmpfiles.org for hosting...")
    
    with open(video_path, "rb") as f:
        files = {"file": f}
        for attempt in range(3):
            try:
                resp = httpx.post(upload_url, files=files, timeout=120.0)
                resp.raise_for_status()
                data = resp.json()
                viewer_url = data.get("data", {}).get("url")
                if not viewer_url:
                    raise ValueError(f"No URL in tmpfiles response: {data}")
                
                # Convert standard URL into a direct download URL
                direct_url = viewer_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                print(f"   [Instagram] Direct hosted URL: {direct_url}")
                return direct_url
            except Exception as e:
                print(f"   [Instagram] tmpfiles upload attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    raise


def publish_instagram_reel(video_path: Path, caption: str) -> str:
    """Upload and publish a Reel to Instagram. Returns published media ID."""
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "").strip()
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()

    if not account_id or not access_token:
        raise ValueError(
            "Missing INSTAGRAM_ACCOUNT_ID or INSTAGRAM_ACCESS_TOKEN in environment.\n"
            "Please add them to your .env file to enable Instagram uploads."
        )

    # 1. Get direct public hosted URL
    video_url = upload_to_tmpfiles(video_path)

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    # 2. Create media container
    print("   [Instagram] Initializing Reels container on Meta servers...")
    create_url = f"{BASE_URL}/{account_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": True,
    }

    resp = httpx.post(create_url, json=payload, headers=headers, timeout=60.0)
    resp.raise_for_status()
    container_id = resp.json().get("id")
    if not container_id:
        raise ValueError(f"Failed to create media container: {resp.text}")
    print(f"   [Instagram] Container created (ID: {container_id}). Waiting for processing...")

    # 3. Poll container status
    status_url = f"{BASE_URL}/{container_id}"
    params = {"fields": "status_code,status"}
    
    max_polls = 60
    for attempt in range(1, max_polls + 1):
        time.sleep(5)
        try:
            status_resp = httpx.get(status_url, params=params, headers=headers, timeout=30.0)
            status_resp.raise_for_status()
            data = status_resp.json()
            status_code = data.get("status_code", "")
            
            print(f"      Poll {attempt}: status={status_code}")
            
            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                raise RuntimeError(f"Meta processing failed: {data.get('status', 'Unknown error')}")
        except Exception as e:
            print(f"      [Instagram Poll Warning] Status check error: {e}")

    else:
        raise TimeoutError("Meta timed out processing the Reels container.")

    # 4. Publish container
    print("   [Instagram] Publishing Reel live to feed...")
    publish_url = f"{BASE_URL}/{account_id}/media_publish"
    publish_payload = {
        "creation_id": container_id,
    }

    publish_resp = httpx.post(publish_url, json=publish_payload, headers=headers, timeout=60.0)
    publish_resp.raise_for_status()
    media_id = publish_resp.json().get("id")
    if not media_id:
        raise ValueError(f"Failed to publish media: {publish_resp.text}")

    print(f"   [Instagram] SUCCESS! Published Reel Media ID: {media_id}")
    return media_id


def publish_facebook_reel(video_path: Path, caption: str) -> str:
    """Upload and publish a Reel to a Facebook Page. Returns published video ID."""
    page_id = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
    # Fallback to INSTAGRAM_ACCESS_TOKEN if FACEBOOK_ACCESS_TOKEN is not defined
    user_access_token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "").strip()
    if not user_access_token:
        user_access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()

    if not page_id or not user_access_token:
        raise ValueError(
            "Missing FACEBOOK_PAGE_ID or access token (FACEBOOK_ACCESS_TOKEN / INSTAGRAM_ACCESS_TOKEN) in environment.\n"
            "Please add them to your .env file to enable Facebook uploads."
        )

    # Resolve Page Access Token programmatically using the User Access Token
    print("   [Facebook] Retrieving Page Access Token...")
    token_url = f"{BASE_URL}/{page_id}"
    token_params = {
        "fields": "access_token",
        "access_token": user_access_token
    }
    try:
        token_resp = httpx.get(token_url, params=token_params, timeout=30.0)
        token_resp.raise_for_status()
        page_access_token = token_resp.json().get("access_token")
        if not page_access_token:
            raise ValueError(f"No access token returned for Page {page_id}. Make sure the user has admin role.")
    except Exception as e:
        raise RuntimeError(
            f"Failed to retrieve Page Access Token: {e}.\n"
            f"Make sure you added the pages_manage_posts permission and authorized the page."
        )

    # 1. Start Phase
    print("   [Facebook] Initializing Reels upload session...")
    start_url = f"{BASE_URL}/{page_id}/video_reels"
    payload = {
        "upload_phase": "start",
        "access_token": page_access_token
    }

    resp = httpx.post(start_url, data=payload, timeout=60.0)
    resp.raise_for_status()
    resp_data = resp.json()
    video_id = resp_data.get("video_id")
    upload_url = resp_data.get("upload_url")

    if not video_id or not upload_url:
        raise ValueError(f"Failed to initialize Facebook upload: {resp.text}")

    print(f"   [Facebook] Upload session initialized (Video ID: {video_id}).")

    # 2. Upload Phase (Binary payload to rupload.facebook.com)
    file_size = video_path.stat().st_size
    print(f"   [Facebook] Uploading binary video file ({file_size} bytes)...")

    headers = {
        "Authorization": f"OAuth {page_access_token}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream"
    }

    with open(video_path, "rb") as f:
        upload_resp = httpx.post(upload_url, headers=headers, content=f, timeout=120.0)
        upload_resp.raise_for_status()

    print("   [Facebook] Video upload completed successfully.")

    # 3. Finish/Publish Phase
    print("   [Facebook] Publishing Reel to Facebook Page feed...")
    finish_payload = {
        "access_token": page_access_token,
        "video_id": video_id,
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "description": caption
    }

    finish_resp = httpx.post(start_url, data=finish_payload, timeout=60.0)
    finish_resp.raise_for_status()
    finish_data = finish_resp.json()

    print(f"   [Facebook] SUCCESS! Published Reel. Response: {finish_data}")
    return video_id
