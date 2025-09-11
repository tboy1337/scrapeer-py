"""
HTTP scraping functionality for Scrapeer.
"""

import logging
import re
import socket
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


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
    protocol: str,
    host: str,
    port: int,
    passkey: str,
    *,
    announce: bool = False,
    timeout: int = 2,
) -> Dict[str, Dict[str, int]]:
    """
    Initiates the HTTP(S) scraping

    Args:
        infohashes: List of valid 40-character hex infohashes.
        protocol: Protocol to use for the scraping ("http" or "https").
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.
        passkey: Passkey provided in the scrape request (can be empty).
        announce: Use announce instead of scrape.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        dict: Dictionary of results with infohash as key.

    Raises:
        Exception: For network errors, invalid responses, or protocol issues.
    """
    if not infohashes:
        raise ValueError("Infohashes list cannot be empty.")

    if protocol not in ("http", "https"):
        raise ValueError(f"Invalid protocol '{protocol}', must be 'http' or 'https'.")

    validate_network_params(host, port, timeout)
    logger.debug("Starting HTTP%s scrape for %s", 'S' if protocol == 'https' else '', host)

    try:
        if announce:
            logger.debug("Using announce method for %d hash(es)", len(infohashes))
            response = http_announce(infohashes, protocol, host, port, passkey, timeout=timeout)
        else:
            logger.debug("Using scrape method for %d hash(es)", len(infohashes))
            query = http_query(infohashes, protocol, host, port, passkey)
            response = http_request(query, host, port, timeout)

        results = http_data(response, infohashes, host)
        logger.info("HTTP scrape successful: %d results from %s", len(results), host)
        return results
    except Exception as e:
        logger.error("HTTP scrape failed for %s: %s", host, str(e))
        raise


def http_query(infohashes: List[str], protocol: str, host: str, port: int, passkey: str) -> str:
    """
    Builds the HTTP(S) query

    Args:
        infohashes: List (>1) or string of infohash(es).
        protocol: Protocol to use for the scraping.
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.
        passkey: Optional. Passkey provided in the scrape request.

    Returns:
        str: Fully qualified URL.
    """
    info = urllib.parse.urlparse(f"{protocol}://{host}:{port}/scrape{passkey}")
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
            query, headers={"User-Agent": "Scrapeer-py/1.0.0"}
        )
        with urllib.request.urlopen(request) as urlfile:  # type: ignore[misc]
            response: bytes = urlfile.read()  # type: ignore[misc]
        return response
    except Exception as e:
        raise ConnectionError(f"Connection error: {host}:{port} - {str(e)}") from e


def http_announce(
    infohashes: List[str], protocol: str, host: str, port: int, passkey: str, *, timeout: int = 2
) -> bytes:
    """
    Announces to the tracker instead of scraping

    Args:
        infohashes: List (>1) or string of infohash(es).
        protocol: Protocol to use for the scraping.
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.
        passkey: Optional. Passkey provided in the scrape request.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        str: Response from the tracker.
    """
    info = urllib.parse.urlparse(f"{protocol}://{host}:{port}/announce{passkey}")
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
            query, headers={"User-Agent": "Scrapeer-py/1.0.0"}
        )
        with urllib.request.urlopen(request) as urlfile:  # type: ignore[misc]
            response: bytes = urlfile.read()  # type: ignore[misc]
        return response
    except Exception as e:
        raise ConnectionError(f"Connection error: {host}:{port} - {str(e)}") from e


def http_data(response: bytes, infohashes: List[str], host: str) -> Dict[str, Dict[str, int]]:  # pylint: disable=too-many-locals
    """
    Gets the data from HTTP(S) response

    Args:
        response: Response from the tracker.
        infohashes: List (>1) or string of infohash(es).
        host: Domain or IP address of the tracker.

    Returns:
        dict: Dictionary of results.
    """
    # Convert bytes to string, handling encoding issues
    try:
        data = response.decode('utf-8', errors='replace')
    except UnicodeDecodeError:
        data = response.decode('latin-1', errors='replace')
    results: Dict[str, Dict[str, int]] = {}
    pattern_all = r"d8:completei(\d+)e10:downloadedi(\d+)e10:incompletei(\d+)e"
    pattern_single = r"d8:completei(\d+)e10:incompletei(\d+)e"

    for infohash in infohashes:
        pattern = f"{infohash}:{pattern_all}"
        matches = re.search(pattern, data, re.IGNORECASE)

        if matches:
            results[infohash] = {
                "seeders": int(matches.group(1)),
                "completed": int(matches.group(2)),
                "leechers": int(matches.group(3)),
            }
        else:
            pattern = f"{infohash}:{pattern_single}"
            matches = re.search(pattern, data, re.IGNORECASE)

            if matches:
                results[infohash] = {
                    "seeders": int(matches.group(1)),
                    "completed": 0,
                    "leechers": int(matches.group(2)),
                }
            else:
                info = get_information(data, "d5:filesd", "ee")

                if info:
                    try:
                        infohash_bytes = bytes.fromhex(infohash).decode('latin-1', errors='ignore')
                    except ValueError:
                        infohash_bytes = infohash
                    pattern = f"20:{infohash_bytes}d"
                    start = info.find(pattern)

                    if start != -1:
                        info = info[start:]
                        end = info.find("e")
                        info = info[: end + 1]

                        seeders_match = re.search(r"completei(\d+)e", info, re.IGNORECASE)
                        leechers_match = re.search(r"incompletei(\d+)e", info, re.IGNORECASE)
                        completed_match = re.search(r"downloadedi(\d+)e", info, re.IGNORECASE)

                        seeders = int(seeders_match.group(1)) if seeders_match else 0
                        leechers = int(leechers_match.group(1)) if leechers_match else 0
                        completed = int(completed_match.group(1)) if completed_match else 0

                        results[infohash] = {
                            "seeders": seeders,
                            "completed": completed,
                            "leechers": leechers,
                        }
                    else:
                        raise ValueError(f"Failed to parse torrent data from '{host}'.")
                else:
                    raise ValueError(f"Invalid scrape response from '{host}'.")

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
