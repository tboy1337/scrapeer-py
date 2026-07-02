"""
HTTP scraping functionality for Scrapeer.
"""

import logging
import re
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass
from re import Match
from typing import Dict, List, Optional

from .config import get_user_agent

# Configure logging
logger = logging.getLogger(__name__)

_PATTERN_ALL = r"d8:completei(\d+)e10:downloadedi(\d+)e10:incompletei(\d+)e"
_PATTERN_SINGLE = r"d8:completei(\d+)e10:incompletei(\d+)e"


@dataclass(frozen=True)
class HttpTrackerEndpoint:
    """HTTP(S) tracker connection parameters."""

    protocol: str
    host: str
    port: int
    passkey: str = ""


def validate_network_params(host: str, port: int, timeout: int) -> None:
    """
    Validate common network parameters.

    Args:
        host: Host address to validate
        port: Port number to validate
        timeout: Timeout value to validate

    Raises:
        ValueError: If any parameter is invalid
    """
    if not host or not host.strip():
        raise ValueError("Host cannot be empty.")

    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError(f"Invalid port {port}, must be 1-65535.")

    if not isinstance(timeout, int) or timeout < 1:
        raise ValueError(f"Invalid timeout {timeout}, must be positive integer.")


def scrape_http(
    infohashes: List[str],
    endpoint: HttpTrackerEndpoint,
    *,
    announce: bool = False,
    timeout: int = 2,
) -> Dict[str, Dict[str, int]]:
    """
    Initiates the HTTP(S) scraping

    Args:
        infohashes: List of valid 40-character hex infohashes.
        endpoint: Tracker protocol, host, port, and passkey.
        announce: Use announce instead of scrape.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        dict: Dictionary of results with infohash as key.

    Raises:
        Exception: For network errors, invalid responses, or protocol issues.
    """
    if not infohashes:
        raise ValueError("Infohashes list cannot be empty.")

    if endpoint.protocol not in ("http", "https"):
        raise ValueError(
            f"Invalid protocol '{endpoint.protocol}', must be 'http' or 'https'."
        )

    validate_network_params(endpoint.host, endpoint.port, timeout)
    logger.debug(
        "Starting HTTP%s scrape for %s",
        "S" if endpoint.protocol == "https" else "",
        endpoint.host,
    )

    try:
        if announce:
            logger.debug("Using announce method for %d hash(es)", len(infohashes))
            response = http_announce(infohashes, endpoint, timeout=timeout)
        else:
            logger.debug("Using scrape method for %d hash(es)", len(infohashes))
            query = http_query(infohashes, endpoint)
            response = http_request(query, endpoint.host, endpoint.port, timeout)

        results = http_data(response, infohashes, endpoint.host)
        logger.info(
            "HTTP scrape successful: %d results from %s", len(results), endpoint.host
        )
        return results
    except Exception as e:
        logger.error("HTTP scrape failed for %s: %s", endpoint.host, str(e))
        raise


def http_query(infohashes: List[str], endpoint: HttpTrackerEndpoint) -> str:
    """
    Builds the HTTP(S) query

    Args:
        infohashes: List (>1) or string of infohash(es).
        endpoint: Tracker protocol, host, port, and passkey.

    Returns:
        str: Fully qualified URL.
    """
    info = urllib.parse.urlparse(
        f"{endpoint.protocol}://{endpoint.host}:{endpoint.port}"
        f"/scrape{endpoint.passkey}"
    )
    query = f"{info.scheme}://{info.netloc}{info.path}"

    if len(infohashes) > 1:
        query += "?"

        for index, infohash in enumerate(infohashes):
            query += f"info_hash={urllib.parse.quote(bytes.fromhex(infohash))}"

            if index < len(infohashes) - 1:
                query += "&"
    elif len(infohashes) == 1:
        query += f"?info_hash={urllib.parse.quote(bytes.fromhex(infohashes[0]))}"

    return query


def http_request(query: str, host: str, port: int, timeout: int) -> bytes:
    """
    Sends HTTP(S) request to the tracker

    Args:
        query: URL to the tracker.
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        str: Response from the tracker.
    """
    socket.setdefaulttimeout(timeout)

    try:
        request = urllib.request.Request(
            query, headers={"User-Agent": get_user_agent()}
        )
        with urllib.request.urlopen(request) as urlfile:  # type: ignore[misc]  # nosec B310
            response: bytes = urlfile.read()  # type: ignore[misc]
        return response
    except Exception as e:
        raise ConnectionError(f"Connection error: {host}:{port} - {str(e)}") from e


def http_announce(
    infohashes: List[str],
    endpoint: HttpTrackerEndpoint,
    *,
    timeout: int = 2,
) -> bytes:
    """
    Announces to the tracker instead of scraping

    Args:
        infohashes: List (>1) or string of infohash(es).
        endpoint: Tracker protocol, host, port, and passkey.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        str: Response from the tracker.
    """
    info = urllib.parse.urlparse(
        f"{endpoint.protocol}://{endpoint.host}:{endpoint.port}"
        f"/announce{endpoint.passkey}"
    )
    query = f"{info.scheme}://{info.netloc}{info.path}"

    if len(infohashes) > 1:
        raise ValueError(f"Too many hashes for HTTP announce ({len(infohashes)}).")

    query += f"?info_hash={urllib.parse.quote(bytes.fromhex(infohashes[0]))}"
    query += "&peer_id=test1234567891234567"
    query += "&port=6889"
    query += "&uploaded=0"
    query += "&downloaded=0"
    query += "&left=0"
    query += "&compact=1"

    socket.setdefaulttimeout(timeout)

    try:
        request = urllib.request.Request(
            query, headers={"User-Agent": get_user_agent()}
        )
        with urllib.request.urlopen(request) as urlfile:  # type: ignore[misc]  # nosec B310
            response: bytes = urlfile.read()  # type: ignore[misc]
        return response
    except Exception as e:
        raise ConnectionError(
            f"Connection error: {endpoint.host}:{endpoint.port} - {str(e)}"
        ) from e


def _decode_tracker_response(response: bytes) -> str:
    """Decode tracker response bytes to a string."""
    try:
        return response.decode("utf-8")
    except UnicodeDecodeError:
        return response.decode("latin-1", errors="replace")


def _stats_from_all_pattern(matches: Match[str]) -> Dict[str, int]:
    """Build stats dict from the full scrape regex match."""
    return {
        "seeders": int(matches.group(1)),
        "completed": int(matches.group(2)),
        "leechers": int(matches.group(3)),
    }


def _stats_from_single_pattern(matches: Match[str]) -> Dict[str, int]:
    """Build stats dict from the single-hash scrape regex match."""
    return {
        "seeders": int(matches.group(1)),
        "completed": 0,
        "leechers": int(matches.group(2)),
    }


def _parse_hash_direct(data: str, infohash: str) -> Optional[Dict[str, int]]:
    """Parse per-hash stats using direct regex patterns."""
    pattern = f"{infohash}:{_PATTERN_ALL}"
    matches = re.search(pattern, data, re.IGNORECASE)
    if matches:
        return _stats_from_all_pattern(matches)

    pattern = f"{infohash}:{_PATTERN_SINGLE}"
    matches = re.search(pattern, data, re.IGNORECASE)
    if matches:
        return _stats_from_single_pattern(matches)

    return None


def _parse_hash_from_files_section(
    data: str, infohash: str, host: str
) -> Dict[str, int]:
    """Parse per-hash stats from the d5:filesd section fallback."""
    info = get_information(data, "d5:filesd", "ee")
    if not info:
        raise ValueError(f"Invalid scrape response from '{host}'.")

    try:
        infohash_bytes = bytes.fromhex(infohash).decode("latin-1", errors="ignore")
    except ValueError:
        infohash_bytes = infohash

    pattern = f"20:{infohash_bytes}d"
    start = info.find(pattern)
    if start == -1:
        raise ValueError(f"Failed to parse torrent data from '{host}'.")

    section = info[start:]
    end = section.find("e")
    section = section[: end + 1]

    seeders_match = re.search(r"completei(\d+)e", section, re.IGNORECASE)
    leechers_match = re.search(r"incompletei(\d+)e", section, re.IGNORECASE)
    completed_match = re.search(r"downloadedi(\d+)e", section, re.IGNORECASE)

    return {
        "seeders": int(seeders_match.group(1)) if seeders_match else 0,
        "leechers": int(leechers_match.group(1)) if leechers_match else 0,
        "completed": int(completed_match.group(1)) if completed_match else 0,
    }


def http_data(
    response: bytes, infohashes: List[str], host: str
) -> Dict[str, Dict[str, int]]:
    """
    Gets the data from HTTP(S) response

    Args:
        response: Response from the tracker.
        infohashes: List (>1) or string of infohash(es).
        host: Domain or IP address of the tracker.

    Returns:
        dict: Dictionary of results.
    """
    data = _decode_tracker_response(response)
    results: Dict[str, Dict[str, int]] = {}

    for infohash in infohashes:
        direct = _parse_hash_direct(data, infohash)
        if direct is not None:
            results[infohash] = direct
            continue
        results[infohash] = _parse_hash_from_files_section(data, infohash, host)

    return results


def get_information(data: str, start: str, end: str) -> Optional[str]:
    """
    Gets information from HTTP(S) response

    Args:
        data: Response from the tracker.
        start: Starting string.
        end: Ending string.

    Returns:
        str: Information or None.
    """
    start_pos = data.find(start)

    if start_pos != -1:
        start_pos += len(start)
        end_pos = data.find(end, start_pos)

        if end_pos != -1:
            return data[start_pos:end_pos]

    return None
