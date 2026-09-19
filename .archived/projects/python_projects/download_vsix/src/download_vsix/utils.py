"""Utility functions for the VSIX downloader."""

import hashlib
import re
from pathlib import Path
from typing import Final

from download_vsix.exceptions import InvalidURLError

# Constants
MARKETPLACE_BASE_URL: Final = "https://marketplace.visualstudio.com"
DOWNLOAD_API_TEMPLATE: Final = (
    "{base}/_apis/public/gallery/publishers/{publisher}/vsextensions/{extension}/{version}/vspackage"
)


def validate_marketplace_url(url: str) -> bool:
    """Validate if the URL is a valid VS Code marketplace extension URL.

    Args:
        url: The URL to validate.

    Returns:
        True if valid, False otherwise.
    """
    pattern = r"^https?://marketplace\.visualstudio\.com/items\?itemName=[a-zA-Z0-9.-]+$"
    return bool(re.match(pattern, url))


def parse_item_name(url: str) -> tuple[str, str, str]:
    """Parse the item name from a VS Code marketplace URL.

    Args:
        url: The marketplace extension URL.

    Returns:
        A tuple of (item_name, publisher, extension_name).

    Raises:
        InvalidURLError: If the URL is invalid.
    """
    if not validate_marketplace_url(url):
        raise InvalidURLError(
            f"Invalid VS Code marketplace URL: {url}\n"
            "Expected format: https://marketplace.visualstudio.com/items?itemName=publisher.extension"
        )

    # Extract itemName from URL query parameter
    match = re.search(r"itemName=([a-zA-Z0-9.-]+)", url)
    if not match:
        raise InvalidURLError(f"Could not extract itemName from URL: {url}")

    item_name = match.group(1)

    # Split item_name into publisher and extension_name
    parts = item_name.split(".", 1)
    if len(parts) != 2:
        raise InvalidURLError(
            f"Invalid itemName format: {item_name}\n"
            "Expected format: publisher.extension"
        )

    publisher, extension_name = parts
    return item_name, publisher, extension_name


def build_download_url(publisher: str, extension_name: str, version: str) -> str:
    """Build the download URL for a VSIX file.

    Args:
        publisher: The publisher name (fieldA).
        extension_name: The extension name (fieldB).
        version: The version number.

    Returns:
        The complete download URL.
    """
    return DOWNLOAD_API_TEMPLATE.format(
        base=MARKETPLACE_BASE_URL,
        publisher=publisher,
        extension=extension_name,
        version=version,
    )


def sanitize_filename(name: str) -> str:
    """Sanitize a filename by removing/replacing invalid characters.

    Args:
        name: The filename to sanitize.

    Returns:
        The sanitized filename.
    """
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, "_", name)


def format_file_size(size: int) -> str:
    """Format a file size in bytes to a human-readable string.

    Args:
        size: The file size in bytes.

    Returns:
        The formatted file size string.
    """
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.2f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.2f} TB"


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: The directory path.

    Returns:
        The directory path.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def calculate_checksum(file_path: Path, algorithm: str = "sha256") -> str:
    """Calculate the checksum of a file.

    Args:
        file_path: The path to the file.
        algorithm: The hash algorithm to use (default: sha256).

    Returns:
        The hexadecimal checksum string.
    """
    hash_func = hashlib.new(algorithm)
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def get_vsix_filename(publisher: str, extension_name: str, version: str) -> str:
    """Generate a standardized VSIX filename.

    Args:
        publisher: The publisher name.
        extension_name: The extension name.
        version: The version number.

    Returns:
        The generated filename.
    """
    base_name = f"{publisher}.{extension_name}-{version}"
    return sanitize_filename(base_name) + ".vsix"
