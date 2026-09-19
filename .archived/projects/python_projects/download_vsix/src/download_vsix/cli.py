"""Command-line interface for the VSIX downloader."""

import sys
from pathlib import Path
from typing import Final

import typer
from rich.console import Console

from download_vsix.downloader import VSIXDownloader
from download_vsix.exceptions import (
    DownloadFailedError,
    FileExistsError,
    InvalidURLError,
    NetworkError,
    VersionNotFoundError,
)
from download_vsix.parser import ExtensionParser
from download_vsix.utils import (
    ensure_directory,
    get_vsix_filename,
    parse_item_name,
    validate_marketplace_url,
)

# Constants
DEFAULT_OUTPUT_DIR: Final = Path("vsixs")
APP_NAME: Final = "download-vsix"
APP_VERSION: Final = "0.1.0"

# Create console instance
console = Console()

# Create typer app
app = typer.Typer(
    name=APP_NAME,
    help="Download VSIX files from VS Code marketplace",
    add_completion=False,
)


def print_banner() -> None:
    """Print the application banner."""
    banner = f"""
    ===============================================================
    
         VSIX Downloader for VS Code Marketplace
                     v{APP_VERSION}
    
    ===============================================================
    """
    console.print(banner, style="bold cyan")


def print_error(message: str) -> None:
    """Print an error message in red.

    Args:
        message: The error message to print.
    """
    console.print(f"[red][X] Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message in green.

    Args:
        message: The success message to print.
    """
    console.print(f"[green][√][/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow.

    Args:
        message: The warning message to print.
    """
    console.print(f"[yellow][!][/yellow] Warning: {message}")


def print_info(message: str) -> None:
    """Print an info message in blue.

    Args:
        message: The info message to print.
    """
    console.print(f"[blue][i][/blue] {message}")


@app.command()
def main(
    url: str = typer.Argument(
        ...,
        help="VS Code marketplace extension URL",
        metavar="URL",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_OUTPUT_DIR,
        "--output-dir",
        "-o",
        help="Directory to save the downloaded VSIX file",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file without prompting",
    ),
    no_resume: bool = typer.Option(
        False,
        "--no-resume",
        help="Disable resume support for interrupted downloads",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    no_banner: bool = typer.Option(
        False,
        "--no-banner",
        help="Don't display the application banner",
    ),
) -> None:
    """Download a VSIX file from VS Code marketplace.

    Example:
        download-vsix https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno
    """
    # Print banner
    if not no_banner:
        print_banner()

    # Set up logging for verbose mode
    if verbose:
        from loguru import logger

        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    try:
        # Validate URL
        print_info(f"Validating URL: {url}")
        if not validate_marketplace_url(url):
            raise InvalidURLError(
                f"Invalid VS Code marketplace URL.\n"
                f"Expected format: https://marketplace.visualstudio.com/items?itemName=publisher.extension\n"
                f"Example: https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno"
            )

        # Parse item name from URL
        print_info("Parsing extension information...")
        item_name, publisher, extension_name = parse_item_name(url)

        if verbose:
            print_info(f"  Publisher: {publisher}")
            print_info(f"  Extension: {extension_name}")
            print_info(f"  Item Name: {item_name}")

        # Fetch extension information (including latest version)
        print_info("Fetching extension details...")
        with ExtensionParser() as parser:
            ext_info = parser.parse_extension_info(item_name, publisher, extension_name)

        console.print(f"\n[bold cyan]Extension:[/bold cyan] {ext_info}")
        console.print(f"  [dim]Version:[/dim] {ext_info.version}")
        console.print(f"  [dim]Download URL:[/dim] {ext_info.download_url}")

        # Generate filename
        filename = get_vsix_filename(publisher, extension_name, ext_info.version)
        output_path = ensure_directory(output_dir) / filename

        if verbose:
            print_info(f"Output path: {output_path}")

        # Download VSIX file
        console.print(f"\n[bold cyan]Starting download...[/bold cyan]")
        with VSIXDownloader() as downloader:
            downloader.download(
                url=ext_info.download_url,
                output_dir=output_dir,
                filename=filename,
                force=force,
                resume=not no_resume,
            )

        # Success
        console.print(f"\n[green]{'='*60}[/green]")
        console.print(f"[bold green]Download completed successfully![/bold green]")
        console.print(f"[green]{'='*60}[/green]")
        console.print(f"  [dim]Extension:[/dim] {ext_info}")
        console.print(f"  [dim]Saved to:[/dim] {output_path}")
        console.print(f"  [dim]Filename:[/dim] {filename}")

        sys.exit(0)

    except InvalidURLError as e:
        print_error(str(e))
        console.print(
            "\n[dim]Example URLs:[/dim]",
        )
        console.print("  https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno")
        console.print("  https://marketplace.visualstudio.com/items?itemName=ms-python.python")
        sys.exit(1)

    except VersionNotFoundError as e:
        print_error(str(e))
        console.print(
            "\n[dim]This could be due to:[/dim]\n"
            "  - The extension page has changed its structure\n"
            "  - The extension is no longer available\n"
            "  - Network connectivity issues\n"
            "\n[dim]Please try again later or report this issue.[/dim]"
        )
        sys.exit(1)

    except FileExistsError as e:
        print_error(str(e))
        console.print(
            f"\n[dim]Use the --force flag to overwrite:[/dim]\n"
            f"  download-vsix {url} --force"
        )
        sys.exit(1)

    except NetworkError as e:
        print_error(f"Network error: {e}")
        console.print(
            "\n[dim]Please check your internet connection and try again.[/dim]"
        )
        sys.exit(1)

    except DownloadFailedError as e:
        print_error(f"Download failed: {e}")
        console.print(
            "\n[dim]The download could not be completed. Please try again later.[/dim]"
        )
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Download cancelled by user.[/yellow]")
        sys.exit(130)

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            console.print("\n[dim]Traceback:[/dim]")
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def version() -> None:
    """Show the application version."""
    console.print(f"{APP_NAME} v{APP_VERSION}")


if __name__ == "__main__":
    app()
