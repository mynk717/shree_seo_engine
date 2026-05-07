import json
import os
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

# Pointing to the local engine folder
load_dotenv()

CACHE_PATH = "shopify_token_cache.json"

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")

def _now_utc():
    return datetime.now(timezone.utc)

def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None

def _save_cache(token, expires_in):
    payload = {
        "access_token": token,
        "fetched_at": _now_utc().isoformat(),
        "expires_at": (_now_utc() + timedelta(seconds=int(expires_in))).isoformat(),
        "store": SHOPIFY_STORE,
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

def _cache_is_valid(cache):
    if not cache:
        return False
    token = cache.get("access_token")
    expires_at = cache.get("expires_at")
    store = cache.get("store")
    if not token or not expires_at or store != SHOPIFY_STORE:
        return False
    try:
        exp = datetime.fromisoformat(expires_at)
        return exp > (_now_utc() + timedelta(minutes=5))
    except Exception:
        return False

def get_access_token(force_refresh=False):
    if not SHOPIFY_STORE or not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
        raise RuntimeError("Missing SHOPIFY_STORE, CLIENT_ID, or CLIENT_SECRET in .env file.")

    if not force_refresh:
        cache = _load_cache()
        if _cache_is_valid(cache):
            return cache["access_token"], "cache"

    # The exact 2026 POST request from your documentation
    url = f"https://{SHOPIFY_STORE}/admin/oauth/access_token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
    }
    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()
    data = response.json()

    token = data.get("access_token")
    # Default to 24 hours (86400 seconds) if not provided
    expires_in = data.get("expires_in", 86400) 
    
    if not token:
        raise RuntimeError(f"Shopify token response missing access_token: {data}")

    _save_cache(token, expires_in)
    return token, "fresh"

def get_validated_token():
    try:
        return get_access_token(force_refresh=False)
    except Exception:
        return get_access_token(force_refresh=True)