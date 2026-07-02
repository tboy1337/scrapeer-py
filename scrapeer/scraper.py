"""
Main Scraper class for Scrapeer.
"""

import logging
import urllib.parse
from typing import Dict, List, Optional, Union

from ._version import get_version
from .config import get_default_timeout
from .http import scrape_http
from .udp import scrape_udp
from .utils import get_passkey, normalize_infohashes

logger = logging.getLogger(__name__)


class Scraper:
    """
    The one and only class you'll ever need.
    """

    VERSION = get_version()

    def __init__(self) -> None:
        """
        Initialize the scraper.
        """
        self.errors: List[str] = []
        self.infohashes: List[str] = []
        self.timeout: int = get_default_timeout()
        logger.debug(
            "Scraper initialized with default timeout of %d seconds", self.timeout
        )

    def scrape(  # pylint: disable=too-many-locals
        self,
        hashes: Union[str, List[str]],
        trackers: Union[str, List[str]],
        *,
        max_trackers: Optional[int] = None,
        timeout: Optional[int] = None,
        announce: bool = False,
    ) -> Dict[str, Dict[str, int]]:
        """
        Initiates the scraper

        Args:
            hashes: List (>1) or string of infohash(es).
            trackers: List (>1) or string of tracker(s).
            max_trackers: Optional. Maximum number of trackers to be scraped, Default all.
            timeout: Optional. Maximum time for each tracker scrape in seconds.
            announce: Optional. Use announce instead of scrape, Default false.

        Returns:
            dict: Dictionary of results with infohash as key and stats as value.

        Raises:
            ValueError: If input validation fails.
            TypeError: If arguments are of incorrect type.
        """
        if timeout is None:
            timeout = get_default_timeout()

        if hashes is None:
            raise ValueError("Hashes cannot be None.")

        if trackers is None:
            raise ValueError("Trackers cannot be None.")

        if not isinstance(announce, bool):
            raise TypeError(f"Announce must be boolean, got {type(announce).__name__}.")

        if max_trackers is not None and not isinstance(max_trackers, int):
            raise TypeError(
                f"Max_trackers must be integer or None, got {type(max_trackers).__name__}."
            )

        if max_trackers is not None and max_trackers < 1:
            raise ValueError(f"Max_trackers must be positive, got {max_trackers}.")

        if not isinstance(timeout, int):
            raise TypeError(f"Timeout must be integer, got {type(timeout).__name__}.")

        if timeout < 1:
            raise ValueError(f"Timeout must be positive, got {timeout}.")

        if timeout > 300:
            raise ValueError(f"Timeout too large, max 300 seconds, got {timeout}.")

        final_result: Dict[str, Dict[str, int]] = {}

        if not trackers:
            error_msg = "No tracker specified, aborting."
            logger.error(error_msg)
            self.errors.append(error_msg)
            return final_result
        if not isinstance(trackers, list):
            trackers = [trackers]

        logger.info(
            "Starting scrape of %d tracker(s) with %d hash(es)",
            len(trackers),
            len(hashes) if isinstance(hashes, list) else 1,
        )

        self.timeout = timeout
        logger.debug("Timeout set to %d seconds", timeout)

        try:
            self.infohashes = normalize_infohashes(hashes, self.errors)
            logger.debug("Normalized %d valid infohashes", len(self.infohashes))
        except ValueError as e:
            error_msg = str(e)
            logger.error("Hash normalization failed: %s", error_msg)
            self.errors.append(error_msg)
            return final_result

        max_iterations = (
            max_trackers if isinstance(max_trackers, int) else len(trackers)
        )
        for index, tracker in enumerate(trackers):
            if self.infohashes and index < max_iterations:
                info = urllib.parse.urlparse(tracker)
                protocol = info.scheme
                host = info.netloc.split(":")[0] if ":" in info.netloc else info.netloc

                if not protocol or not host:
                    error_msg = f"Skipping invalid tracker ({tracker})."
                    logger.warning(error_msg)
                    self.errors.append(error_msg)
                    continue

                port = info.port if info.port else None
                path = info.path if info.path else None
                passkey = get_passkey(path)

                logger.info("Scraping %s://%s:%s", protocol, host, port or "default")
                result = self.try_scrape(
                    protocol, host, port, passkey, announce=announce
                )
                final_result.update(result)
                logger.debug("Got %d results from %s", len(result), host)
                continue
            break

        return final_result

    def try_scrape(
        self,
        protocol: str,
        host: str,
        port: Optional[int],
        passkey: str,
        *,
        announce: bool = False,
    ) -> Dict[str, Dict[str, int]]:
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
        results: Dict[str, Dict[str, int]] = {}

        try:
            if protocol == "udp":
                port = port if port else 80
                results = scrape_udp(infohashes, host, port, announce, self.timeout)
            elif protocol == "http":
                port = port if port else 80
                results = scrape_http(
                    infohashes,
                    protocol,
                    host,
                    port,
                    passkey,
                    announce=announce,
                    timeout=self.timeout,
                )
            elif protocol == "https":
                port = port if port else 443
                results = scrape_http(
                    infohashes,
                    protocol,
                    host,
                    port,
                    passkey,
                    announce=announce,
                    timeout=self.timeout,
                )
            else:
                raise ValueError(f"Unsupported protocol ({protocol}://{host}).")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.infohashes = infohashes
            error_msg = str(e)
            logger.error("Scraping failed for %s://%s: %s", protocol, host, error_msg)
            self.errors.append(error_msg)

        return results

    def has_errors(self) -> bool:
        """
        Checks if there are any errors.

        Returns:
            bool: True if errors are present, False otherwise.
        """
        return len(self.errors) > 0

    def get_errors(self) -> List[str]:
        """
        Returns all the errors that were logged.

        Returns:
            list: All the logged errors.
        """
        return self.errors
