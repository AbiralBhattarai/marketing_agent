from bs4 import BeautifulSoup
import aiohttp

from src.ports.output.scraper_port import ScraperPort

class Bs4Scraper(ScraperPort):

    async def scrape_brand_site(self, brand_site: str):
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SimpleScraper/1.0)"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(brand_site, headers=headers) as response:
                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")

        # Title
        title = soup.title.get_text(strip=True) if soup.title else ""

        # Headings (h1, h2, h3)
        headings = [
            tag.get_text(strip=True)
            for tag in soup.find_all(["h1", "h2", "h3"])
        ]

        # Paragraphs
        paragraphs = [
            p.get_text(strip=True)
            for p in soup.find_all("p")
        ]

        return {
            "title": title,
            "headings": headings,
            "paragraphs": paragraphs
        }