import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.fawanews.sc/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
OUTPUT_FILE = "fawa_playlist.m3u8"


def get_soup(url, retries=3):
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            else:
                print(f"[!] Status {resp.status_code} for {url}")
        except Exception as e:
            print(f"[!] Retry {i+1}/{retries} - Error: {e}")
            time.sleep(2)
    return None


def extract_m3u8_from_script(html):
    patterns = [
        r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        r'src\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        r'url\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        r'"(https?://[^"]+\.m3u8[^"]*)"',
        r"(https?://[^\s'\"]+\.m3u8[^\s'\"]*)"
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def scrape_fawanews():
    print("[*] Connecting to fawanews.sc...")
    soup = get_soup(BASE_URL)
    if not soup:
        print("[!] Failed to load main page.")
        return []

    streams = []
    links = soup.find_all("a", href=re.compile(r"/watch/"))

    if not links:
        links = soup.find_all("a", href=True)
        links = [a for a in links if a.get_text(strip=True) and ("Live" in a.text or "Match" in a.text or "vs" in a.text)]

    print(f"[*] Found {len(links)} potential live links.")

    for link in links:
        try:
            title = link.get_text(strip=True)
            href = link.get("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = urljoin(BASE_URL, href)

            print(f"[-] Checking: {title[:30]}...")
            detail_soup = get_soup(href)
            if not detail_soup:
                continue

            iframe = detail_soup.find("iframe")
            if iframe and iframe.get("src"):
                stream_url = iframe.get("src")
                if not stream_url.startswith("http"):
                    stream_url = urljoin(href, stream_url)
                print("   [i] Found iframe, scraping inside...")
                iframe_soup = get_soup(stream_url)
                if iframe_soup:
                    m3u8 = extract_m3u8_from_script(str(iframe_soup))
                    if m3u8:
                        streams.append({"title": title, "url": m3u8})
                        print(f"   [+] Found stream: {title}")
                        continue

            if not streams or streams[-1]["title"] != title:
                m3u8 = extract_m3u8_from_script(str(detail_soup))
                if m3u8:
                    streams.append({"title": title, "url": m3u8})
                    print(f"   [+] Found stream directly: {title}")
                    continue

            print(f"   [-] No stream found for {title[:20]}...")
            time.sleep(1)

        except Exception as e:
            print(f"   [x] Error processing link: {e}")
            continue

    return streams


def generate_m3u8(streams, filename=OUTPUT_FILE):
    if not streams:
        print("[!] No streams found to generate playlist.")
        return

    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("#PLAYLIST: FawaNews Live Streams (Auto-Updated)\n\n")

        for item in streams:
            title = item["title"].replace(",", "").strip()
            url = item["url"]
            f.write(f'#EXTINF:-1 tvg-logo="" group-title="Fawa Sports", {title}\n')
            f.write(f"{url}\n\n")

    print(f"[+] Playlist generated successfully: {filename}")
    print(f"[+] Total streams: {len(streams)}")


if __name__ == "__main__":
    print("[*] Starting FawaNews Scraper...")
    all_streams = scrape_fawanews()
    if all_streams:
        generate_m3u8(all_streams)
    else:
        print("[!] No streams extracted. The site structure might have changed.")
