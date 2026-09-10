"""Custom exceptions for the VSIX downloader."""


class VSIXDownloaderError(Exception):
    """Base exception for VSIX downloader errors."""

    pass


class InvalidURLError(VSIXDownloaderError):
    """Raised when the provided URL is invalid or not a VS Code marketplace URL."""

    pass


class VersionNotFoundError(VSIXDownloaderError):
    """Raised when the version cannot be found or parsed from the extension page."""

    pass


class DownloadFailedError(VSIXDownloaderError):
    """Raised when the download fails after all retries."""

    pass


class NetworkError(VSIXDownloaderError):
    """Raised when a network-related error occurs."""

    pass


class FileExistsError(VSIXDownloaderError):
    """Raised when the target file already exists and force flag is not set."""

    pass
