# scraper.py - ToonStream Scraper (Final Version)
# Supports both Series and Movies URL patterns

import re
import time
import threading
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
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 1800

    def _get_cache(self, key):
        with self._cache_lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if time.time() - timestamp < self._cache_ttl:
                    return data
                else:
                    del self._cache[key]
        return None

    def _set_cache(self, key, data):
        with self._cache_lock:
            self._cache[key] = (data, time.time())

    def _get_page(self, url):
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
        cache_key = f"search:{query.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        search_url = f"{self.base_url}/?s={quote(query)}"
        soup = self._get_page(search_url)
        if not soup:
            return []

        results = []
        for a_tag in soup.select('a[href^="/series/"]'):
            href = a_tag.get("href", "")
            if not href:
                continue

            slug = href.replace("/series/", "").strip("/")
            if not slug:
                continue

            title_tag = a_tag.find_previous(["h2", "h3", "h4"])
            title = title_tag.get_text(strip=True) if title_tag else slug.replace("-", " ").title()

            results.append({
                "title": title,
                "slug": slug,
                "url": f"{self.base_url}{href}"
            })

        seen = set()
        unique_results = []
        for r in results:
            if r["slug"] not in seen:
                seen.add(r["slug"])
                unique_results.append(r)

        self._set_cache(cache_key, unique_results)
        return unique_results

    def find_best_match(self, query, target_slug=None):
        results = self.search_anime(query)
        if not results:
            return None

        if target_slug:
            for r in results:
                if r["slug"] == target_slug:
                    return r

        query_lower = query.lower()
        for r in results:
            if query_lower in r["title"].lower() or query_lower in r["slug"].lower():
                return r

        return results[0]

    def get_episode_list(self, series_slug):
        cache_key = f"episodes:{series_slug}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        series_url = f"{self.base_url}/series/{series_slug}"
        soup = self._get_page(series_url)
        if not soup:
            return []

        episodes = []
        pattern = re.compile(
            r"/episode/" + re.escape(series_slug) + r"-(\d+)x(\d+)/?",
            re.IGNORECASE
        )

        for a_tag in soup.select('a[href*="/episode/"]'):
            href = a_tag.get("href", "")
            match = pattern.search(href)
            if not match:
                continue

            season = int(match.group(1))
            episode = int(match.group(2))
            full_url = href if href.startswith("http") else f"{self.base_url}{href}"

            episodes.append({
                "season": season,
                "episode": episode,
                "url": full_url
            })

        seen = set()
        unique_eps = []
        for ep in episodes:
            key = (ep["season"], ep["episode"])
            if key not in seen:
                seen.add(key)
                unique_eps.append(ep)

        unique_eps.sort(key=lambda x: (x["season"], x["episode"]))
        self._set_cache(cache_key, unique_eps)
        return unique_eps

    def get_servers(self, episode_url):
        cache_key = f"servers:{episode_url}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        soup = self._get_page(episode_url)
        if not soup:
            return {"total_servers": 0, "servers": []}

        servers = []
        seen_urls = set()

        iframes = soup.select("iframe")
        for idx, iframe in enumerate(iframes):
            embed_url = iframe.get("data-src") or iframe.get("src")

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

        result = {"total_servers": len(servers), "servers": servers}
        self._set_cache(cache_key, result)
        return result

    def get_streaming_links(self, series_slug, season=1, episode=1):
        """
        Series এবং Movie দুটো URL প্যাটার্নই ট্রাই করে।
        যেকোনো একটি URL-এ সার্ভার পেলেই সেটি রিটার্ন করে।
        """
        possible_urls = [
            f"{self.base_url}/episode/{series_slug}-{season}x{episode}/",
            f"{self.base_url}/movies/{series_slug}/",
            f"{self.base_url}/movie/{series_slug}/",
            f"{self.base_url}/episode/{series_slug}-1x1/",
            f"{self.base_url}/series/{series_slug}/",
        ]

        tried = []
        for url in possible_urls:
            tried.append(url)
            server_data = self.get_servers(url)
            if server_data["total_servers"] > 0:
                return {
                    "success": True,
                    "data": {
                        "series_slug": series_slug,
                        "season": season,
                        "episode": episode,
                        "episode_url": url,
                        "total_servers": server_data["total_servers"],
                        "servers": server_data["servers"]
                    }
                }

        return {
            "success": False,
            "error": f"No servers found for slug: '{series_slug}'",
            "tried_urls": tried
        }
