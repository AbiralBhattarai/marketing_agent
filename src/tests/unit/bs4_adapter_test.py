from os import scandir
import asyncio
from src.adapters.bs4_scraper_adapter import Bs4Scraper


async def main():
    url = "https://www.scribd.com/document/486960685/final-campaign-for-air-force-1"
    scraper = Bs4Scraper()
    res = await scraper.scrape_brand_site(url)
    print(res)


if __name__ == "__main__":
    asyncio.run(main())
