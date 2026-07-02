#!/usr/bin/env python3
"""
Command-line interface for Scrapeer-py.
"""

import argparse
import json
import sys
from typing import List, Optional

from scrapeer import Scraper
from scrapeer._version import get_version
from scrapeer.config import get_default_timeout


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Scrape BitTorrent trackers for torrent information",
        epilog="Example: %(prog)s abc123...def456 -t udp://tracker.example.com:80",
    )
    parser.add_argument(
        "infohashes", nargs="+", help="One or more 40-character infohashes to scrape"
    )
    parser.add_argument(
        "-t",
        "--trackers",
        nargs="+",
        required=True,
        help="One or more tracker URLs (UDP/HTTP/HTTPS)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="Timeout in seconds for each tracker (default: from config)",
    )
    parser.add_argument(
        "--announce", action="store_true", help="Use announce instead of scrape"
    )
    parser.add_argument(
        "--max-trackers", type=int, help="Maximum number of trackers to scrape"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress error messages"
    )
    parser.add_argument(
        "--version", action="version", version=f"Scrapeer-py {get_version()}"
    )
    return parser


def _validate_infohashes(infohashes: List[str], quiet: bool) -> None:
    """Validate infohash format; exit on failure."""
    for infohash in infohashes:
        if len(infohash) != 40 or not all(
            c in "0123456789abcdefABCDEF" for c in infohash
        ):
            if not quiet:
                print(
                    f"Error: Invalid infohash '{infohash}'. Must be 40 hex characters.",
                    file=sys.stderr,
                )
            sys.exit(1)


def _validate_timeout_value(timeout: int, quiet: bool) -> None:
    """Validate timeout range; exit on failure."""
    if timeout < 1 or timeout > 300:
        if not quiet:
            print("Error: Timeout must be between 1 and 300 seconds.", file=sys.stderr)
        sys.exit(1)


def _emit_json(
    results: dict[str, dict[str, int]],
    scraper: Scraper,
    infohashes: List[str],
) -> None:
    """Print scrape results as JSON."""
    output = {
        "results": results,
        "errors": scraper.get_errors() if scraper.has_errors() else [],
        "total_hashes": len(infohashes),
        "successful_hashes": len(results),
    }
    print(json.dumps(output, indent=2))


def _emit_human(
    results: dict[str, dict[str, int]],
    scraper: Scraper,
    infohashes: List[str],
    quiet: bool,
) -> None:
    """Print scrape results in human-readable form."""
    if results:
        print("Results:")
        print("=" * 50)
        for infohash, data in results.items():
            print(f"\n{infohash}:")
            print(f"  Seeders: {data['seeders']:,}")
            print(f"  Leechers: {data['leechers']:,}")
            print(f"  Completed: {data['completed']:,}")
        print(f"\nSummary: {len(results)}/{len(infohashes)} infohashes found")
    else:
        print("No results found.")

    if scraper.has_errors() and not quiet:
        error_count = len(scraper.get_errors())
        print(f"\nErrors ({error_count}):")
        print("-" * 30)
        for i, error in enumerate(scraper.get_errors(), 1):
            print(f"  {i}. {error}")


def _exit_code(results: dict[str, dict[str, int]], scraper: Scraper) -> int:
    """Return the process exit code for the scrape outcome."""
    if not results and scraper.has_errors():
        return 1
    return 0


def main() -> None:
    """Main CLI entry point."""
    args = _build_argument_parser().parse_args()

    infohashes: List[str] = args.infohashes
    trackers: List[str] = args.trackers
    timeout: int = args.timeout
    announce: bool = args.announce
    max_trackers: Optional[int] = args.max_trackers
    json_output: bool = args.json
    quiet: bool = args.quiet

    _validate_infohashes(infohashes, quiet)
    _validate_timeout_value(timeout, quiet)

    scraper = Scraper()
    try:
        results = scraper.scrape(
            hashes=infohashes,
            trackers=trackers,
            timeout=timeout,
            announce=announce,
            max_trackers=max_trackers,
        )

        if json_output:
            _emit_json(results, scraper, infohashes)
        else:
            _emit_human(results, scraper, infohashes, quiet)

        exit_code = _exit_code(results, scraper)
        if exit_code != 0:
            sys.exit(exit_code)

    except KeyboardInterrupt:
        if not quiet:
            print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-exception-caught
        if not quiet:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
