#!/usr/bin/env python3
"""
Run this ONCE on your local machine to get a YouTube OAuth refresh token.
Then store the token file path (or its contents) as a GitHub Actions secret.

Usage:
  .venv/bin/python scripts/youtube_auth.py

Prerequisites:
  1. Google Cloud Console → create project → enable "YouTube Data API v3"
     https://console.cloud.google.com/apis/library/youtube.googleapis.com
  2. Credentials → Create OAuth client ID → Desktop app → Download JSON
  3. Save that JSON as  secrets/client_secret.json  (gitignored)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SECRETS = REPO_ROOT / "secrets"


def main() -> None:
    client_secret = SECRETS / "client_secret.json"
    token_out = SECRETS / "youtube_token.json"

    if not client_secret.is_file():
        print(
            "❌ Missing secrets/client_secret.json\n\n"
            "Steps:\n"
            "  1. Go to https://console.cloud.google.com/\n"
            "  2. Create a project (or pick one)\n"
            "  3. Enable YouTube Data API v3:\n"
            "     https://console.cloud.google.com/apis/library/youtube.googleapis.com\n"
            "  4. Go to Credentials → Create OAuth client ID → Desktop app\n"
            "  5. Download JSON → save as secrets/client_secret.json\n"
        )
        sys.exit(1)

    print("Opening browser for Google OAuth…")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0)

    SECRETS.mkdir(parents=True, exist_ok=True)
    token_out.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n✅ Token saved to {token_out}")

    # Also print the refresh token so user can add it to GitHub Secrets
    token_data = json.loads(creds.to_json())
    print("\n── For GitHub Actions ──")
    print("Add these as Repository Secrets (Settings → Secrets → Actions):\n")
    print(f"  YT_REFRESH_TOKEN = {token_data.get('refresh_token', '???')}")
    print(f"  YT_CLIENT_ID     = {token_data.get('client_id', '???')}")
    print(f"  YT_CLIENT_SECRET_VALUE = {token_data.get('client_secret', '???')}")
    print("\nDone. Never commit secrets/ to git.")


if __name__ == "__main__":
    main()
