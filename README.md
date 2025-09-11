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

Scrapeer-py can be used both as a Python library and as a command-line tool.

### Python Library Usage

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

### Command-Line Usage

After installation, you can use the `scrapeer` command directly:

```bash
# Basic usage
scrapeer INFOHASH1 INFOHASH2 -t TRACKER1 TRACKER2

# Example with real values
scrapeer abc123def456...890 fedcba987654...321 \
  -t udp://tracker.example.com:80 \
  -t http://tracker.example.org:6969/announce

# With options
scrapeer INFOHASH -t TRACKER --timeout 5 --announce --json

# Get help
scrapeer --help
```

#### CLI Options

- `-t, --trackers`: One or more tracker URLs (required)
- `--timeout`: Timeout in seconds for each tracker (default: 2)
- `--announce`: Use announce instead of scrape
- `--max-trackers`: Maximum number of trackers to scrape
- `--json`: Output results in JSON format
- `--quiet, -q`: Suppress error messages
- `--version`: Show version information

#### CLI Examples

**Basic scraping:**
```bash
scrapeer d4344b390d7bc7b7d332c6d89ef1ff5d6f78ca48 \
  -t udp://tracker.opentrackr.org:1337/announce
```

**Multiple hashes and trackers:**
```bash
scrapeer hash1 hash2 hash3 \
  -t udp://tracker1.com:80 \
  -t http://tracker2.org:8080/announce \
  --timeout 10
```

**JSON output for scripting:**
```bash
scrapeer INFOHASH -t TRACKER --json > results.json
```

**Private tracker with passkey:**
```bash
scrapeer INFOHASH \
  -t https://private-tracker.net:443/YOUR_PASSKEY/announce \
  --announce
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