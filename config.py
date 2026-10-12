# config.py - সব কনফিগারেশন এক জায়গায়

BASE_URL = "https://toonstream.us"
SEARCH_URL = f"{BASE_URL}/?s={{query}}"

# HTTP Headers (Cloudflare বাইপাসের জন্য)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL + "/",
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
CACHE_TTL = 3600  # 1 hour
