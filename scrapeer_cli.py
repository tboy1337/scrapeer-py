#!/usr/bin/env python3
"""
Command-line interface for Scrapeer-py.
"""

import argparse
import json
import sys
from typing import List, Optional

from scrapeer import Scraper


def main() -> None:  # pylint: disable=too-many-locals
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape BitTorrent trackers for torrent information",
        epilog="Example: %(prog)s abc123...def456 -t udp://tracker.example.com:80"
    )
    parser.add_argument(
        "infohashes",
        nargs="+",
        help="One or more 40-character infohashes to scrape"
    )
    parser.add_argument(
        "-t", "--trackers",
        nargs="+",
        required=True,
        help="One or more tracker URLs (UDP/HTTP/HTTPS)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=2,
        help="Timeout in seconds for each tracker (default: 2)"
    )
    parser.add_argument(
        "--announce",
        action="store_true",
        help="Use announce instead of scrape"
    )
    parser.add_argument(
        "--max-trackers",
        type=int,
        help="Maximum number of trackers to scrape"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress error messages"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Scrapeer-py 1.0.3"
    )

    args = parser.parse_args()

    # Validate infohashes
    infohashes: List[str] = args.infohashes
    trackers: List[str] = args.trackers
    timeout: int = args.timeout
    announce: bool = args.announce
    max_trackers: Optional[int] = args.max_trackers
    json_output: bool = args.json
    quiet: bool = args.quiet
    for infohash in infohashes:
        if len(infohash) != 40 or not all(c in '0123456789abcdefABCDEF' for c in infohash):
            if not quiet:
                print(
                    f"Error: Invalid infohash '{infohash}'. Must be 40 hex characters.",
                    file=sys.stderr
                )
            sys.exit(1)

    # Validate timeout
    if timeout < 1 or timeout > 300:
        if not quiet:
            print("Error: Timeout must be between 1 and 300 seconds.", file=sys.stderr)
        sys.exit(1)

    # Initialize scraper and get results
    scraper = Scraper()
    try:
        results = scraper.scrape(
            hashes=infohashes,
            trackers=trackers,
            timeout=timeout,
            announce=announce,
            max_trackers=max_trackers
        )

        if json_output:
            # JSON output
            output = {
                "results": results,
                "errors": scraper.get_errors() if scraper.has_errors() else [],
                "total_hashes": len(infohashes),
                "successful_hashes": len(results)
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
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

        # Exit with appropriate code
        if not results and scraper.has_errors():
            sys.exit(1)

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
