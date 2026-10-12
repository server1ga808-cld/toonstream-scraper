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
