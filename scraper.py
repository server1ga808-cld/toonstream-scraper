# scraper.py - ToonStream স্ক্র্যাপার
import re
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import quote
from config import BASE_URL, HEADERS, REQUEST_TIMEOUT, MAX_RETRIES


class ToonStreamScraper:
    """ToonStream.us থেকে ডেটা স্ক্র্যাপ করার ক্লাস"""

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.scraper.headers.update(HEADERS)
        self.base_url = BASE_URL

    def _get_page(self, url):
        """একটি পেজ ডাউনলোড করে BeautifulSoup অবজেক্ট রিটার্ন করে।"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.scraper.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"[ERROR] Failed to fetch {url}: {e}")
                    return None
        return None

    def search_anime(self, query):
        """
        টাইটেল বা কীওয়ার্ড দিয়ে অ্যানিমে খোঁজে।
        রিটার্ন: [{'title': ..., 'slug': ..., 'url': ...}, ...]
        """
        search_url = f"{self.base_url}/?s={quote(query)}"
        soup = self._get_page(search_url)
        if not soup:
            return []

        results = []
        # সিরিজ লিংকগুলো খুঁজে বের করা
        for a_tag in soup.select('a[href^="/series/"]'):
            href = a_tag.get("href", "")
            if not href:
                continue
            # slug এক্সট্রাক্ট করা
            slug = href.replace("/series/", "").strip("/")
            if not slug:
                continue

            # টাইটেল খোঁজা (প্যারেন্ট কার্ড থেকে)
            title_tag = a_tag.find_previous(["h2", "h3", "h4"])
            title = title_tag.get_text(strip=True) if title_tag else slug.replace("-", " ").title()

            results.append({
                "title": title,
                "slug": slug,
                "url": f"{self.base_url}{href}"
            })

        # ডুপ্লিকেট সরানো
        seen = set()
        unique_results = []
        for r in results:
            if r["slug"] not in seen:
                seen.add(r["slug"])
                unique_results.append(r)

        return unique_results

    def find_best_match(self, query, target_slug=None):
        """
        সার্চ রেজাল্ট থেকে সবচেয়ে ভালো ম্যাচ খুঁজে বের করে।
        - যদি target_slug দেওয়া হয়, তবে সেটির সাথে সরাসরি ম্যাচ খোঁজে।
        - অন্যথায়, টাইটেলের সাথে মিল খোঁজে।
        """
        results = self.search_anime(query)
        if not results:
            return None

        # ১. slug দিয়ে সরাসরি ম্যাচ
        if target_slug:
            for r in results:
                if r["slug"] == target_slug:
                    return r

        # ২. টাইটেলের সাথে আংশিক ম্যাচ (fuzzy)
        query_lower = query.lower()
        for r in results:
            if query_lower in r["title"].lower() or query_lower in r["slug"].lower():
                return r

        # ৩. কোনোটিই না মিললে, প্রথম রেজাল্ট রিটার্ন করা
        return results[0]
        def get_episode_list(self, series_slug):
    """
    একটি সিরিজের সব এপিসোডের লিস্ট বের করে।
    রিটার্ন: [{'season': 1, 'episode': 1, 'url': ...}, ...]
    """
    series_url = f"{self.base_url}/series/{series_slug}"
    soup = self._get_page(series_url)
    if not soup:
        return []

    episodes = []
    # এপিসোড লিংক প্যাটার্ন: /episode/{slug}x{season}x{episode}/
    pattern = re.compile(r"/episode/" + re.escape(series_slug) + r"-(\d+)x(\d+)/?", re.IGNORECASE)

    for a_tag in soup.select('a[href*="/episode/"]'):
        href = a_tag.get("href", "")
        match = pattern.search(href)
        if not match:
            continue

        season = int(match.group(1))
        episode = int(match.group(2))

        # ফুল URL তৈরি
        if href.startswith("http"):
            full_url = href
        else:
            full_url = f"{self.base_url}{href}"

        episodes.append({
            "season": season,
            "episode": episode,
            "url": full_url
        })

    # ডুপ্লিকেট সরানো এবং সিজন-এপিসোড অনুযায়ী সাজানো
    seen = set()
    unique_eps = []
    for ep in episodes:
        key = (ep["season"], ep["episode"])
        if key not in seen:
            seen.add(key)
            unique_eps.append(ep)

    unique_eps.sort(key=lambda x: (x["season"], x["episode"]))
    return unique_eps

def get_servers(self, episode_url):
    """
    একটি এপিসোড পেজ থেকে সব সার্ভারের iframe URL ডাইনামিকভাবে বের করে।
    সার্ভারের সংখ্যা ৫, ৭, বা যতগুলোই থাকুক—সবগুলো রিটার্ন করবে।
    রিটার্ন: {'total_servers': int, 'servers': [{'server_number': int, 'embed_url': str}, ...]}
    """
    soup = self._get_page(episode_url)
    if not soup:
        return {"total_servers": 0, "servers": []}

    servers = []
    seen_urls = set()

    # পদ্ধতি ১: সরাসরি iframe ট্যাগ থেকে data-src বের করা
    iframes = soup.select("iframe")
    for idx, iframe in enumerate(iframes):
        embed_url = iframe.get("data-src") or iframe.get("src")

        # about:blank, javascript:, বা খালি লিংক বাদ দেওয়া
        if not embed_url:
            continue
        if embed_url.startswith("about:blank") or embed_url.startswith("javascript:"):
            continue
        if embed_url in seen_urls:
            continue

        seen_urls.add(embed_url)
        servers.append({
            "server_number": len(servers) + 1,
            "embed_url": embed_url
        })

    # পদ্ধতি ২: যদি iframe ট্যাগে না পাওয়া যায়, তবে HTML সোর্সে regex দিয়ে খোঁজা
    if not servers:
        html = str(soup)
        data_src_matches = re.findall(r'data-src=["\']([^"\']+)["\']', html)
        for url in data_src_matches:
            if url.startswith("about:blank") or url.startswith("javascript:"):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            servers.append({
                "server_number": len(servers) + 1,
                "embed_url": url
            })

    return {
        "total_servers": len(servers),
        "servers": servers
    }

def get_streaming_links(self, series_slug, season=None, episode=None):
    """
    একটি নির্দিষ্ট এপিসোডের সব স্ট্রিমিং লিংক বের করার মেইন ফাংশন।
    - season/episode না দিলে প্রথম এপিসোড নেবে।
    """
    episodes = self.get_episode_list(series_slug)
    if not episodes:
        return {"success": False, "error": "No episodes found"}

    # নির্দিষ্ট এপিসোড খোঁজা
    target_ep = None
    if season is not None and episode is not None:
        for ep in episodes:
            if ep["season"] == season and ep["episode"] == episode:
                target_ep = ep
                break
    else:
        target_ep = episodes[0]

    if not target_ep:
        return {"success": False, "error": f"Episode S{season}E{episode} not found"}

    # সার্ভার লিংক বের করা
    server_data = self.get_servers(target_ep["url"])

    return {
        "success": True,
        "data": {
            "series_slug": series_slug,
            "season": target_ep["season"],
            "episode": target_ep["episode"],
            "episode_url": target_ep["url"],
            "total_servers": server_data["total_servers"],
            "servers": server_data["servers"]
        }
    }
