"""
Scrapeer-py, a tiny Python library that lets you scrape
HTTP(S) and UDP trackers for torrent information.

Port of the original PHP Scrapeer library by TorrentPier.
"""

from .scraper import Scraper

__version__ = '1.0.0'
__all__ = ['Scraper'] 