"""Provider implementations for Civ7ModManager"""
import logging
import re

from datetime import datetime
from typing import List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import AttributeValueList

from utilities.modinfo_parser import ModInfo
from utilities.constants import CIVFANATICS_BASE_URL, CIVFANATICS_CIV7_URL


class ParserError(Exception):
    """Error parsing html content"""


class CivFanaticsProvider:
    """Provider implementation for CivFanatics"""

    def __init__(self):
        self.base_url = CIVFANATICS_BASE_URL + CIVFANATICS_CIV7_URL
        self.logger = logging.getLogger('Civ7ModManager.CivFanaticsProvider')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

    async def search_mods(self, page: int = 1) -> Tuple[List[ModInfo], int]:
        """Get all available mods from CivFanatics on the specified page"""
        mods: List[ModInfo] = []
        total_pages = 1
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                params = {}

                if page > 1:
                    params["page"] = str(page)

                self.logger.info("Fetching mods from URL: %s with params: %s", self.base_url, params)

                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        self.logger.error("Failed to fetch mods: %s", response.status)
                        return mods, total_pages

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Gather all resource elements
                    resources = soup.select(".structItem--resource")

                    for resource in resources:
                        try:
                            # Author
                            author = resource.get("data-author")
                            if author is None:
                                raise ParserError("data-author")
                            if isinstance(author, AttributeValueList):
                                author = author[0]

                            # Main cell [title, url, id, version, description]
                            main_cell = resource.select_one(".structItem-cell--main")
                            if main_cell is None:
                                raise ParserError(".structItem-cell--main")

                            title_elem = main_cell.select_one(".structItem-title a")
                            if title_elem is None:
                                raise ParserError(".structItem-title a")
                            title: str = title_elem.text.strip()

                            resource_url = title_elem.get("href")
                            if resource_url is None:
                                raise ParserError(".structItem-title a href")
                            if isinstance(resource_url, AttributeValueList):
                                resource_url = resource_url[0]

                            url_match = re.search(r"/resources/(.+?)\.(\d+)/$", resource_url)
                            if url_match is None:
                                raise ParserError("resource ID")
                            resource_id = url_match.group(2)

                            version_elem = main_cell.select_one(".structItem-title span")
                            if version_elem is None:
                                raise ParserError(".structItem-title span")
                            version: str = version_elem.text.strip()

                            desc_elem = main_cell.select_one(".structItem-resourceTagLine")
                            if desc_elem is None:
                                raise ParserError(".structItem-resourceTagLine")
                            description = desc_elem.text.strip()

                            # Resourcemeta cell [last update, downloads]
                            resourcemeta_cell = resource.select_one(".structItem-cell--resourceMeta")
                            if resourcemeta_cell is None:
                                raise ParserError(".structItem-cell--resourceMeta")

                            time_elem = resourcemeta_cell.select_one("time")
                            if time_elem is None:
                                raise ParserError("time")
                            time_str = time_elem.get("datetime")
                            if time_str is None:
                                raise ParserError("time datetime")
                            if isinstance(time_str, AttributeValueList):
                                time_str = time_str[0]
                            last_update = datetime.fromisoformat(time_str)

                            dl_elem = resourcemeta_cell.select_one('.structItem-metaItem--downloads dd')
                            if dl_elem is None:
                                raise ParserError(".structItem-metaItem--downloads dd")
                            download_count = int(dl_elem.text.strip().replace(',', ''))

                            # Icon cell - extract icon URL if available
                            icon_cell = resource.select_one(".structItem-cell--icon")
                            if icon_cell is None:
                                raise ParserError(".structItem-cell--icon")

                            icon_url = ""
                            icon_elem = icon_cell.select_one("img")
                            if icon_elem:
                                icon_url = icon_elem.get("src", "")
                                if isinstance(icon_url, AttributeValueList):
                                    icon_url = icon_url[0]

                            # Create mod info
                            mod = ModInfo(
                                mod_id="",
                                web_id=resource_id,
                                display_name=title,
                                authors=author,
                                version=version,
                                tag_line=description,
                                download_count=download_count,
                                last_updated=last_update,
                                rating=0.0,
                                icon_url=icon_url,
                                file_path='',
                                provider="civfanatics",
                                affects_saves=None,
                            )
                            mods.append(mod)

                        except ParserError as e:
                            self.logger.warning("Could not find required element: %s", e)
                            continue

                    # Get pagination info
                    nav = soup.select_one(".pageNavWrapper")
                    if nav:
                        # Try to find max page from navigation links
                        nav_links = nav.select(".pageNav-page")
                        if nav_links:
                            page_numbers = []
                            for link in nav_links:
                                try:
                                    page_num = int(link.text.strip())
                                    page_numbers.append(page_num)
                                except (ValueError, TypeError):
                                    continue
                            if page_numbers:
                                total_pages = max(page_numbers)
                        else:
                            # If no page links found, check for total items count
                            total_items_label = nav.select_one(".pageNav-info")
                            if total_items_label:
                                total_match = re.search(r"of (\d+) items", total_items_label.text)
                                if total_match:
                                    total_items = int(total_match.group(1))
                                    total_pages = (total_items + 19) // 20
        except Exception as e:
            self.logger.error("Error searching mods: %s", e)
        finally:
            self.logger.info("Returning %s mods and %s total pages", len(mods), total_pages)
            return mods, total_pages

    async def download_mod(self, mod_info: ModInfo, destination: str) -> str | None:
        """Download a mod to the specified destination"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                url = 'https://forums.civfanatics.com/resources/' + mod_info.web_id + '/download'
                async with session.get(url) as response:
                    # Check if we were redirected to an external site
                    if str(response.url).startswith(("http://", "https://")) and \
                       not str(response.url).startswith("https://forums.civfanatics.com"):
                        self.logger.info("External download detected: %s", response.url)
                        return None

                    if response.status != 200:
                        self.logger.error("Failed to download mod: %s", response.status)
                        return None

                    if response.content_disposition is None:
                        self.logger.error("No content disposition header found")
                        return None
                    if response.content_disposition.filename is None:
                        self.logger.error("No filename found in content disposition header")
                        return None
                    destination = str(destination) + '\\' + response.content_disposition.filename
                    with open(destination, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)

                    return response.content_disposition.filename

        except Exception as e:
            self.logger.error("Error downloading mod: %s", e)
            return None

    async def download_mod_icon(self, mod: ModInfo) -> Optional[bytes]:
        """Download a mod's icon from CivFanatics

        Args:
            mod: The mod info containing the icon URL

        Returns:
            The icon binary data if successful, None otherwise
        """
        if not mod.icon_url:
            return None

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(mod.icon_url) as response:
                    if response.status != 200:
                        self.logger.error("Failed to download icon: %s", response.status)
                        return None

                    return await response.read()

        except Exception as e:
            self.logger.error("Error downloading mod icon: %s", e)
            return None
