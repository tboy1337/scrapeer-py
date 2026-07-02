"""
Scrapeer-py, a tiny Python library that lets you scrape
HTTP(S) and UDP trackers for torrent information.

Port of the original PHP Scrapeer library by TorrentPier.
"""

from . import config as _config  # noqa: F401  # triggers configure_logging on import
from ._version import get_version
from .config import configure_logging, get_config
from .scraper import Scraper

__version__ = get_version()
__all__ = ["Scraper", "__version__", "configure_logging", "get_config", "get_version"]
