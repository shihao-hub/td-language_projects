"""Tests for utility functions."""

import pytest

from download_vsix.exceptions import InvalidURLError
from download_vsix.utils import (
    build_download_url,
    format_file_size,
    get_vsix_filename,
    parse_item_name,
    sanitize_filename,
    validate_marketplace_url,
)


class TestValidateMarketplaceURL:
    """Tests for validate_marketplace_url function."""

    def test_valid_url(self):
        """Test validation of valid URLs."""
        valid_urls = [
            "https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno",
            "http://marketplace.visualstudio.com/items?itemName=ms-python.python",
            "https://marketplace.visualstudio.com/items?itemName=Publisher.Extension-123",
        ]
        for url in valid_urls:
            assert validate_marketplace_url(url), f"URL should be valid: {url}"

    def test_invalid_url(self):
        """Test validation of invalid URLs."""
        invalid_urls = [
            "https://example.com/items?itemName=test",
            "https://marketplace.visualstudio.com/items",
            "https://marketplace.visualstudio.com/items?itemName=",
            "marketplace.visualstudio.com/items?itemName=test",
            "https://marketplace.visualstudio.com/other?itemName=test",
        ]
        for url in invalid_urls:
            assert not validate_marketplace_url(url), f"URL should be invalid: {url}"


class TestParseItemName:
    """Tests for parse_item_name function."""

    def test_parse_valid_url(self):
        """Test parsing a valid URL."""
        url = "https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno"
        item_name, publisher, extension_name = parse_item_name(url)
        assert item_name == "denoland.vscode-deno"
        assert publisher == "denoland"
        assert extension_name == "vscode-deno"

    def test_parse_with_numbers(self):
        """Test parsing URL with numbers."""
        url = "https://marketplace.visualstudio.com/items?itemName=ms-python.python"
        item_name, publisher, extension_name = parse_item_name(url)
        assert item_name == "ms-python.python"
        assert publisher == "ms-python"
        assert extension_name == "python"

    def test_parse_invalid_url(self):
        """Test parsing an invalid URL raises error."""
        with pytest.raises(InvalidURLError):
            parse_item_name("https://example.com/items?itemName=test")

    def test_parse_missing_item_name(self):
        """Test parsing URL without itemName raises error."""
        with pytest.raises(InvalidURLError):
            parse_item_name("https://marketplace.visualstudio.com/items")


class TestBuildDownloadURL:
    """Tests for build_download_url function."""

    def test_build_url(self):
        """Test building download URL."""
        url = build_download_url("denoland", "vscode-deno", "3.43.3")
        expected = (
            "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/"
            "denoland/vsextensions/vscode-deno/3.43.3/vspackage"
        )
        assert url == expected


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_sanitize_invalid_chars(self):
        """Test sanitizing filename with invalid characters."""
        # The pattern matches: < > : " / \ \ | ? * (9 characters)
        assert sanitize_filename('test<>:"/\\|?*file') == "test_________file"

    def test_sanitize_valid_filename(self):
        """Test that valid filenames are unchanged."""
        assert sanitize_filename("valid-file_name.vsix") == "valid-file_name.vsix"

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string."""
        assert sanitize_filename("") == ""


class TestFormatFileSize:
    """Tests for format_file_size function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(512) == "512.00 B"
        assert format_file_size(1024) == "1.00 KB"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(2048) == "2.00 KB"
        assert format_file_size(1024 * 1024) == "1.00 MB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(2 * 1024 * 1024) == "2.00 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(2 * 1024 * 1024 * 1024) == "2.00 GB"

    def test_format_zero(self):
        """Test formatting zero bytes."""
        assert format_file_size(0) == "0.00 B"


class TestGetVSIXFilename:
    """Tests for get_vsix_filename function."""

    def test_generate_filename(self):
        """Test generating VSIX filename."""
        filename = get_vsix_filename("denoland", "vscode-deno", "3.43.3")
        assert filename == "denoland.vscode-deno-3.43.3.vsix"

    def test_generate_filename_with_special_chars(self):
        """Test generating filename with special characters."""
        filename = get_vsix_filename("ms-python", "python", "2024.1.0")
        assert filename == "ms-python.python-2024.1.0.vsix"
