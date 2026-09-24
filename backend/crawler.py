import base64
import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def crawl_site(url: str, multi_page: bool = False, max_pages: int = 5) -> list:
    visited, to_visit, pages = set(), [url], []
    domain = urlparse(url).netloc
    limit = max_pages if multi_page else 1

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        while to_visit and len(pages) < limit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            try:
                r = await client.get(current)
                soup = BeautifulSoup(r.text, "html.parser")
                title = soup.title.get_text(strip=True) if soup.title else ""
                headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)][:20]
                nav_items = [a.get_text(strip=True) for a in soup.select("nav a") if a.get_text(strip=True)][:20]
                text_content = soup.get_text(separator=" ", strip=True)[:3000]
                pages.append({
                    "url": current,
                    "title": title,
                    "headings": headings,
                    "nav_items": nav_items,
                    "text_content": text_content,
                    "forms_count": len(soup.find_all("form")),
                    "images_count": len(soup.find_all("img")),
                })
                if multi_page:
                    for a in soup.find_all("a", href=True):
                        link = urljoin(current, a["href"]).split("#")[0]
                        if urlparse(link).netloc == domain and link not in visited and link not in to_visit:
                            to_visit.append(link)
            except Exception as e:
                pages.append({"url": current, "error": str(e)})
    return pages


async def capture_screenshot(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            screenshot_bytes = await page.screenshot()
            await browser.close()
            return base64.b64encode(screenshot_bytes).decode()
    except Exception as e:
        logger.warning(f"Screenshot capture failed for {url}: {e}")
        return None


def summarize_pages(pages: list) -> str:
    lines = []
    for p in pages:
        if "error" in p:
            lines.append(f"- {p['url']} -> ERROR: {p['error']}")
            continue
        lines.append(
            f"- {p['url']} | title: {p['title']} | headings: {p['headings']} | "
            f"nav: {p['nav_items']} | forms: {p['forms_count']} | images: {p['images_count']} | "
            f"content: {p['text_content'][:600]}"
        )
    return "\n".join(lines)
