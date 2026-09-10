"""Downloader module for downloading VSIX files from VS Code marketplace."""

import time
from pathlib import Path
from typing import Final

from httpx import HTTPStatusError, RequestError, TimeoutException
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from download_vsix.exceptions import DownloadFailedError, FileExistsError, NetworkError
from download_vsix.utils import calculate_checksum, ensure_directory, format_file_size, get_vsix_filename

# Constants
DEFAULT_MAX_RETRIES: Final = 3
DEFAULT_RETRY_DELAY: Final = 1.0  # seconds
USER_AGENT: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class VSIXDownloader:
    """Downloader for VSIX files from VS Code marketplace."""

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        timeout: int = 300,  # 5 minutes for large files
    ) -> None:
        """Initialize the downloader.

        Args:
            max_retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries in seconds.
            timeout: Download timeout in seconds.
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._client = None
        self._async_client = None
        self.console = Console()

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
        """Close the HTTP clients."""
        if self._client is not None:
            self._client.close()
            self._client = None
        if self._async_client is not None:
            import asyncio

            asyncio.run(self._async_client.aclose())
            self._async_client = None

    def __enter__(self) -> "VSIXDownloader":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def _get_file_size(self, url: str) -> int:
        """Get the file size from the URL headers.

        Args:
            url: The URL to check.

        Returns:
            The file size in bytes, or 0 if unknown.

        Raises:
            NetworkError: If the request fails.
        """
        try:
            response = self.client.head(url)
            response.raise_for_status()
            return int(response.headers.get("content-length", 0))
        except TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except HTTPStatusError as e:
            raise NetworkError(f"HTTP error {e.response.status_code}: {e}") from e
        except RequestError as e:
            raise NetworkError(f"Network request failed: {e}") from e

    def _download_with_progress(
        self,
        url: str,
        output_path: Path,
        expected_size: int = 0,
    ) -> None:
        """Download a file with progress bar.

        Args:
            url: The URL to download from.
            output_path: The path to save the file.
            expected_size: Expected file size in bytes.

        Raises:
            DownloadFailedError: If the download fails.
            NetworkError: If a network error occurs.
        """
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        try:
            with progress:
                task_id = progress.add_task(
                    f"[cyan]Downloading {output_path.name}",
                    total=expected_size,
                )

                with self.client.stream("GET", url) as response:
                    response.raise_for_status()

                    with output_path.open("wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task_id, advance=len(chunk))

        except TimeoutException as e:
            raise NetworkError(f"Download timed out: {e}") from e
        except HTTPStatusError as e:
            raise DownloadFailedError(f"HTTP error {e.response.status_code}: {e}") from e
        except RequestError as e:
            raise NetworkError(f"Download failed: {e}") from e

    def _resume_download(
        self,
        url: str,
        output_path: Path,
        partial_size: int,
        expected_size: int = 0,
    ) -> None:
        """Resume a partially downloaded file.

        Args:
            url: The URL to download from.
            output_path: The path to save the file.
            partial_size: Size of the already downloaded portion.
            expected_size: Expected total file size in bytes.

        Raises:
            DownloadFailedError: If the download fails.
            NetworkError: If a network error occurs.
        """
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        try:
            with progress:
                task_id = progress.add_task(
                    f"[cyan]Resuming {output_path.name}",
                    total=expected_size,
                    completed=partial_size,
                )

                headers = {"Range": f"bytes={partial_size}-"}

                with self.client.stream("GET", url, headers=headers) as response:
                    response.raise_for_status()

                    with output_path.open("ab") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task_id, advance=len(chunk))

        except TimeoutException as e:
            raise NetworkError(f"Resume download timed out: {e}") from e
        except HTTPStatusError as e:
            raise DownloadFailedError(f"HTTP error {e.response.status_code}: {e}") from e
        except RequestError as e:
            raise NetworkError(f"Resume download failed: {e}") from e

    def download(
        self,
        url: str,
        output_dir: Path,
        filename: str | None = None,
        force: bool = False,
        resume: bool = True,
    ) -> Path:
        """Download a VSIX file with retry and progress support.

        Args:
            url: The URL to download from.
            output_dir: The directory to save the file.
            filename: Optional custom filename. If not provided, a default name is generated.
            force: Overwrite existing file without prompting.
            resume: Enable resume support for interrupted downloads.

        Returns:
            The path to the downloaded file.

        Raises:
            FileExistsError: If the file exists and force is False.
            DownloadFailedError: If the download fails after all retries.
            NetworkError: If a network error occurs.
        """
        # Ensure output directory exists
        output_dir = ensure_directory(output_dir)

        # Determine output path
        if filename is None:
            # Try to extract filename from URL or use a default
            filename = url.split("/")[-1] or "extension.vsix"
        output_path = output_dir / filename

        # Check if file exists
        if output_path.exists():
            if not force:
                raise FileExistsError(
                    f"File already exists: {output_path}\n"
                    f"Use --force to overwrite."
                )
            if resume:
                # Check if we can resume
                partial_size = output_path.stat().st_size
                if partial_size > 0:
                    self.console.print(
                        f"[yellow]Found partial download ({format_file_size(partial_size)}), "
                        f"attempting to resume...[/yellow]"
                    )
                    try:
                        expected_size = self._get_file_size(url)
                        self._resume_download(url, output_path, partial_size, expected_size)
                        self._print_success(output_path)
                        return output_path
                    except (NetworkError, DownloadFailedError) as e:
                        self.console.print(f"[red]Resume failed: {e}[/red]")
                        self.console.print("[yellow]Starting fresh download...[/yellow]")
                        output_path.unlink()
            else:
                output_path.unlink()

        # Get expected file size for progress bar
        expected_size = 0
        try:
            expected_size = self._get_file_size(url)
            if expected_size > 0:
                self.console.print(
                    f"[dim]File size: {format_file_size(expected_size)}[/dim]"
                )
        except NetworkError:
            # Continue without size information
            pass

        # Download with retry
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._download_with_progress(url, output_path, expected_size)
                self._print_success(output_path)
                return output_path
            except (NetworkError, DownloadFailedError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.console.print(
                        f"[yellow]Download failed (attempt {attempt + 1}/{self.max_retries}): {e}[/yellow]"
                    )
                    self.console.print(f"[dim]Retrying in {delay:.1f}s...[/dim]")
                    time.sleep(delay)
                else:
                    break

        raise DownloadFailedError(
            f"Download failed after {self.max_retries} attempts. Last error: {last_error}"
        ) from last_error

    def _print_success(self, output_path: Path) -> None:
        """Print success message with file info.

        Args:
            output_path: The path to the downloaded file.
        """
        file_size = output_path.stat().st_size
        checksum = calculate_checksum(output_path)

        self.console.print("\n[green][√] Download completed successfully![/green]")
        self.console.print(f"  [dim]File:[/dim] {output_path}")
        self.console.print(f"  [dim]Size:[/dim] {format_file_size(file_size)}")
        self.console.print(f"  [dim]SHA256:[/dim] {checksum}")
