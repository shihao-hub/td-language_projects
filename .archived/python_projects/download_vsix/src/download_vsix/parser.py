"""Parser module for extracting extension information from VS Code marketplace."""

import re
from dataclasses import dataclass
from typing import Final

from bs4 import BeautifulSoup
from httpx import HTTPStatusError, RequestError, TimeoutException

from download_vsix.exceptions import NetworkError, VersionNotFoundError
from download_vsix.utils import build_download_url

# Constants
MARKETPLACE_URL: Final = "https://marketplace.visualstudio.com"
USER_AGENT: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class ExtensionInfo:
    """Extension information data class."""

    item_name: str      # Full item name (e.g., denoland.vscode-deno)
    publisher: str      # Publisher name (fieldA, e.g., denoland)
    extension_name: str # Extension name (fieldB, e.g., vscode-deno)
    version: str       # Latest version (e.g., 3.43.3)
    download_url: str  # Complete download URL

    def __str__(self) -> str:
        return f"{self.publisher}.{self.extension_name} v{self.version}"


class ExtensionParser:
    """Parser for VS Code marketplace extension pages."""

    def __init__(self, timeout: int = 30) -> None:
        """Initialize the parser.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self._client = None

    @property
    def client(self):
        """Lazy import and return httpx client."""
        if self._client is None:
            import httpx

            self._client = httpx.Client(
                timeout=self.timeout,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ExtensionParser":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def fetch_page_content(self, url: str) -> str:
        """Fetch the HTML content of a page.

        Args:
            url: The URL to fetch.

        Returns:
            The HTML content as a string.

        Raises:
            NetworkError: If the request fails.
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.text
        except TimeoutException as e:
            raise NetworkError(f"Request timed out after {self.timeout} seconds: {e}") from e
        except HTTPStatusError as e:
            raise NetworkError(f"HTTP error {e.response.status_code}: {e}") from e
        except RequestError as e:
            raise NetworkError(f"Network request failed: {e}") from e

    def extract_version_from_html(self, html: str) -> str:
        """Extract the latest version from the extension page HTML.

        Args:
            html: The HTML content of the extension page.

        Returns:
            The latest version string.

        Raises:
            VersionNotFoundError: If the version cannot be found.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Try multiple strategies to find the version

        # Strategy 1: Look for version in the Version History section
        # The version is often in a format like "3.43.3" in a specific element
        version_selectors = [
            # Version history section
            'div[class*="version"] span[class*="version"]',
            'div[class*="VersionHistory"] .version',
            'div[class*="version-history"] .version',
            # Alternative selectors
            'span[class*="version"]',
            'div[class*="version"]',
        ]

        for selector in version_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                # Check if it looks like a version number (e.g., 3.43.3)
                if re.match(r"^\d+\.\d+\.\d+", text):
                    return text

        # Strategy 2: Look for version in meta tags
        meta_version = soup.find("meta", attrs={"name": re.compile("version", re.I)})
        if meta_version and meta_version.get("content"):
            content = meta_version["content"]
            if re.match(r"^\d+\.\d+\.\d+", content):
                return content

        # Strategy 3: Look for version in script tags (JSON data)
        script_tags = soup.find_all("script", type="application/ld+json")
        for script in script_tags:
            if script.string:
                import json

                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        version = data.get("version")
                        if version and re.match(r"^\d+\.\d+\.\d+", str(version)):
                            return str(version)
                except (json.JSONDecodeError, TypeError):
                    continue

        # Strategy 4: Search for version pattern in the entire HTML
        version_pattern = r'["\'](\d+\.\d+\.\d+)["\']'
        matches = re.findall(version_pattern, html)
        if matches:
            # Return the first match (likely the latest version)
            return matches[0]

        raise VersionNotFoundError(
            "Could not find version information on the extension page. "
            "Please check the URL or try again later."
        )

    def parse_extension_info(
        self,
        item_name: str,
        publisher: str,
        extension_name: str,
    ) -> ExtensionInfo:
        """Parse extension information from the marketplace.

        Args:
            item_name: The full item name (e.g., denoland.vscode-deno).
            publisher: The publisher name.
            extension_name: The extension name.

        Returns:
            ExtensionInfo object containing all parsed information.

        Raises:
            NetworkError: If fetching the page fails.
            VersionNotFoundError: If the version cannot be found.
        """
        # Build the extension page URL
        extension_url = f"{MARKETPLACE_URL}/items?itemName={item_name}"

        # Fetch the page content
        html = self.fetch_page_content(extension_url)

        # Extract the latest version
        version = self.extract_version_from_html(html)

        # Build the download URL
        download_url = build_download_url(publisher, extension_name, version)

        return ExtensionInfo(
            item_name=item_name,
            publisher=publisher,
            extension_name=extension_name,
            version=version,
            download_url=download_url,
        )
