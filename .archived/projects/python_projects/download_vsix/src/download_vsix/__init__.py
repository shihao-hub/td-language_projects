"""VSIX Downloader - Download VSIX files from VS Code marketplace."""

__version__ = "0.1.0"

from download_vsix.exceptions import (
    DownloadFailedError,
    InvalidURLError,
    NetworkError,
    VersionNotFoundError,
)

__all__ = [
    "__version__",
    "InvalidURLError",
    "VersionNotFoundError",
    "DownloadFailedError",
    "NetworkError",
]
