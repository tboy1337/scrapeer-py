# Scrapeer-py

A tiny Python library that lets you scrape HTTP(S) and UDP trackers for torrent information.

Scrapeer-py is a Python port of the original PHP [Scrapeer](https://github.com/torrentpier/scrapeer) library by [TorrentPier](https://github.com/torrentpier).

## Overview

Scrapeer-py allows you to retrieve peer information from BitTorrent trackers using both HTTP(S) and UDP protocols. It can fetch seeders, leechers, and completed download counts for multiple torrents from multiple trackers simultaneously.

## Features

- Support for both HTTP(S) and UDP tracker protocols
- Batch scraping of multiple infohashes at once (up to 64)
- Support for trackers with passkeys
- Optional announce mode for trackers that don't support scrape
- Configurable timeout settings
- Detailed error reporting
- Well-organized modular codebase

## Installation

```bash
pip install scrapeer
```

## Usage

```python
from scrapeer import Scraper

# Initialize the scraper
scraper = Scraper()

# Define your infohashes and trackers
infohashes = [
    "0123456789abcdef0123456789abcdef01234567",
    "fedcba9876543210fedcba9876543210fedcba98"
]

trackers = [
    "udp://tracker.example.com:80",
    "http://tracker.example.org:6969/announce",
    "https://private-tracker.example.net:443/YOUR_PASSKEY/announce"
]

# Get the results (timeout of 3 seconds per tracker)
results = scraper.scrape(
    hashes=infohashes,
    trackers=trackers,
    timeout=3
)

# Print the results
for infohash, data in results.items():
    print(f"Results for {infohash}:")
    print(f"  Seeders: {data['seeders']}")
    print(f"  Leechers: {data['leechers']}")
    print(f"  Completed: {data['completed']}")

# Check if there were any errors
if scraper.has_errors():
    print("\nErrors:")
    for error in scraper.get_errors():
        print(f"  {error}")
```

## Package Structure

Scrapeer-py is organized into the following modules:

- `scrapeer/` - Main package directory
  - `__init__.py` - Package initialization that exports the Scraper class
  - `scraper.py` - Main Scraper class implementation
  - `http.py` - HTTP(S) protocol scraping functionality
  - `udp.py` - UDP protocol scraping functionality
  - `utils.py` - Utility functions used across the package

## API Reference

### `Scraper` class

#### `scrape(hashes, trackers, max_trackers=None, timeout=2, announce=False)`

Scrape trackers for torrent information.

- **Parameters**:
  - `hashes`: List (>1) or string of infohash(es)
  - `trackers`: List (>1) or string of tracker(s)
  - `max_trackers`: (Optional) Maximum number of trackers to be scraped, Default all
  - `timeout`: (Optional) Maximum time for each tracker scrape in seconds, Default 2
  - `announce`: (Optional) Use announce instead of scrape, Default False

- **Returns**:
  - Dictionary of results with infohashes as keys and stats as values

#### `has_errors()`

Checks if there are any errors.

- **Returns**:
  - `bool`: True if errors are present, False otherwise

#### `get_errors()`

Returns all the errors that were logged.

- **Returns**:
  - `list`: All the logged errors

## Limitations

- Maximum of 64 infohashes per request
- Minimum of 1 infohash per request
- Only supports BitTorrent trackers (HTTP(S) and UDP)

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.