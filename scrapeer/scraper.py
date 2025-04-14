"""
Main Scraper class for Scrapeer.
"""

import urllib.parse
from .http import scrape_http
from .udp import scrape_udp
from .utils import normalize_infohashes, get_passkey


class Scraper:
    """
    The one and only class you'll ever need.
    """

    VERSION = '1.0.0'  # Python port version

    def __init__(self):
        """
        Initialize the scraper.
        """
        self.errors = []
        self.infohashes = []
        self.timeout = 2

    def scrape(self, hashes, trackers, max_trackers=None, timeout=2, announce=False):
        """
        Initiates the scraper

        Args:
            hashes: List (>1) or string of infohash(es).
            trackers: List (>1) or string of tracker(s).
            max_trackers: Optional. Maximum number of trackers to be scraped, Default all.
            timeout: Optional. Maximum time for each tracker scrape in seconds, Default 2.
            announce: Optional. Use announce instead of scrape, Default false.

        Returns:
            dict: Dictionary of results.
        """
        final_result = {}

        if not trackers:
            self.errors.append('No tracker specified, aborting.')
            return final_result
        elif not isinstance(trackers, list):
            trackers = [trackers]

        if isinstance(timeout, int):
            self.timeout = timeout
        else:
            self.timeout = 2
            self.errors.append('Timeout must be an integer. Using default value.')

        try:
            self.infohashes = normalize_infohashes(hashes, self.errors)
        except ValueError as e:
            self.errors.append(str(e))
            return final_result

        max_iterations = max_trackers if isinstance(max_trackers, int) else len(trackers)
        for index, tracker in enumerate(trackers):
            if self.infohashes and index < max_iterations:
                info = urllib.parse.urlparse(tracker)
                protocol = info.scheme
                host = info.netloc.split(':')[0] if ':' in info.netloc else info.netloc
                
                if not protocol or not host:
                    self.errors.append(f'Skipping invalid tracker ({tracker}).')
                    continue

                port = info.port if info.port else None
                path = info.path if info.path else None
                passkey = get_passkey(path)
                
                result = self.try_scrape(protocol, host, port, passkey, announce)
                final_result.update(result)
                continue
            break

        return final_result

    def try_scrape(self, protocol, host, port, passkey, announce):
        """
        Tries to scrape with a single tracker.

        Args:
            protocol: Protocol of the tracker.
            host: Domain or address of the tracker.
            port: Optional. Port number of the tracker.
            passkey: Optional. Passkey provided in the scrape request.
            announce: Optional. Use announce instead of scrape, Default false.

        Returns:
            dict: Dictionary of results.
        """
        infohashes = self.infohashes.copy()
        self.infohashes = []
        results = {}
        
        try:
            if protocol == 'udp':
                port = port if port else 80
                results = scrape_udp(infohashes, host, port, announce, self.timeout)
            elif protocol == 'http':
                port = port if port else 80
                results = scrape_http(infohashes, protocol, host, port, passkey, announce, self.timeout)
            elif protocol == 'https':
                port = port if port else 443
                results = scrape_http(infohashes, protocol, host, port, passkey, announce, self.timeout)
            else:
                raise Exception(f'Unsupported protocol ({protocol}://{host}).')
        except Exception as e:
            self.infohashes = infohashes
            self.errors.append(str(e))
        
        return results

    def has_errors(self):
        """
        Checks if there are any errors.

        Returns:
            bool: True if errors are present, False otherwise.
        """
        return len(self.errors) > 0

    def get_errors(self):
        """
        Returns all the errors that were logged.

        Returns:
            list: All the logged errors.
        """
        return self.errors 