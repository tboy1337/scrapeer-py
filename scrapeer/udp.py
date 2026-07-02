"""
UDP scraping functionality for Scrapeer.
"""

import logging
import random
import socket
import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .http import validate_network_params
from .utils import collect_info_hash, random_peer_id

# Configure logging
logger = logging.getLogger(__name__)


def scrape_udp(
    infohashes: List[str], host: str, port: int, announce: bool, timeout: int
) -> Dict[str, Dict[str, int]]:
    """
    Initiates the UDP scraping

    Args:
        infohashes: List of valid 40-character hex infohashes.
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.
        announce: Use announce instead of scrape.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        dict: Dictionary of results with infohash as key.

    Raises:
        Exception: For network errors, invalid responses, or connection issues.
    """
    if not infohashes:
        raise ValueError("Infohashes list cannot be empty.")

    validate_network_params(host, port, timeout)
    logger.debug(
        "Starting UDP %s for %s:%d", "announce" if announce else "scrape", host, port
    )

    socket_obj, ip = prepare_udp(host, port)
    socket_obj.settimeout(timeout)

    try:
        logger.debug("Establishing UDP connection to %s (%s)", host, ip)
        transaction_id, _ = udp_connection_request(socket_obj)
        connection_id = udp_connection_response(socket_obj, transaction_id, host, port)

        if announce:
            logger.debug("Sending UDP announce for %d hash(es)", len(infohashes))
            result: Dict[str, Dict[str, int]] = udp_announce(
                socket_obj, infohashes, connection_id
            )
        else:
            logger.debug("Sending UDP scrape for %d hash(es)", len(infohashes))
            result = udp_scrape(
                socket_obj,
                infohashes,
                connection_id,
                transaction_id,
                host=host,
                port=port,
            )

        logger.info(
            "UDP %s successful: %d results from %s",
            "announce" if announce else "scrape",
            len(result),
            host,
        )
        return result
    except Exception as e:
        logger.error(
            "UDP %s failed for %s:%d: %s",
            "announce" if announce else "scrape",
            host,
            port,
            str(e),
        )
        raise
    finally:
        socket_obj.close()


def prepare_udp(host: str, port: int) -> Tuple[socket.socket, str]:
    """
    Prepares the UDP socket

    Args:
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.

    Returns:
        tuple: Tuple containing socket object and IP address.
    """
    socket_obj = udp_create_connection(host, port)

    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror as exc:
        raise ConnectionError(f"Failed to resolve host '{host}'.") from exc

    return socket_obj, ip


def udp_create_connection(host: str, port: int) -> socket.socket:
    """
    Creates a UDP connection

    Args:
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.

    Returns:
        socket: Socket object.
    """
    try:
        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_obj.connect((host, port))
        return socket_obj
    except socket.error as e:
        raise ConnectionError(
            f"Failed to create socket for '{host}:{port}' - {str(e)}."
        ) from e


def udp_connection_request(socket_obj: socket.socket) -> Tuple[int, int]:
    """
    Sends a connection request

    Args:
        socket_obj: Socket object.

    Returns:
        tuple: Tuple containing transaction_id and connection_id.
    """
    connection_id = 0x41727101980  # Default connection ID
    action = 0  # Action (0 = connection, 1 = announce, 2 = scrape)
    transaction_id = random.randint(0, 2147483647)  # Random transaction ID

    buffer = struct.pack(">QII", connection_id, action, transaction_id)

    try:
        socket_obj.send(buffer)
    except socket.error as e:
        raise ConnectionError(f"Failed to send connection request - {str(e)}.") from e

    return transaction_id, connection_id


def udp_connection_response(
    socket_obj: socket.socket, transaction_id: int, host: str, port: int
) -> int:
    """
    Receives a connection response

    Args:
        socket_obj: Socket object.
        transaction_id: Transaction ID.
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.

    Returns:
        int: Connection ID.
    """
    try:
        response = socket_obj.recv(16)
    except socket.error as e:
        raise ConnectionError(
            f"Failed to receive connection response from '{host}:{port}' - {str(e)}."
        ) from e

    if len(response) != 16:
        raise ValueError(f"Invalid response length from '{host}:{port}'.")

    return_action: int
    return_transaction_id: int
    connection_id: int
    return_action, return_transaction_id, connection_id = struct.unpack(  # type: ignore[misc]
        ">IIQ", response
    )

    if return_transaction_id != transaction_id:
        raise ValueError(f"Invalid transaction ID from '{host}:{port}'.")

    if return_action != 0:
        raise ValueError(f"Invalid action from '{host}:{port}'.")

    return connection_id


def udp_scrape(
    socket_obj: socket.socket,
    hashes: List[str],
    connection_id: int,
    transaction_id: int,
    *,
    host: str,
    port: int,
) -> Dict[str, Dict[str, int]]:
    """
    Sends a scrape request

    Args:
        socket_obj: Socket object.
        hashes: List (>1) or string of infohash(es).
        connection_id: Connection ID.
        transaction_id: Transaction ID.
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.

    Returns:
        dict: Dictionary of results.
    """
    action = 2  # Action (2 = scrape)

    # Create scrape request
    buffer = udp_scrape_request(socket_obj, hashes, connection_id, transaction_id)

    try:
        # Send scrape request
        socket_obj.send(buffer)

        # Receive scrape response
        response = socket_obj.recv(8 + (12 * len(hashes)))

        # Parse scrape response
        if len(response) < 8:
            raise ValueError(f"Invalid scrape response from '{host}:{port}'.")

        return_action: int
        return_transaction_id: int
        return_action, return_transaction_id = struct.unpack(
            ">II", response[:8]
        )  # type: ignore[misc]

        # Verify transaction ID
        if transaction_id != return_transaction_id:
            raise ValueError(f"Invalid transaction ID from '{host}:{port}'.")

        # Verify action
        if return_action != action:
            err_msg: int = struct.unpack(">I", response[4:8])[0]  # type: ignore[misc]
            raise RuntimeError(f"Tracker error, code: {err_msg} from '{host}:{port}'.")

        # Create keys array
        keys: List[str] = []
        for infohash in hashes:
            keys.append(infohash)

        # Parse results
        return udp_scrape_data(
            response, hashes, host, keys, start=8, end=len(response), offset=12
        )
    except socket.error as e:
        raise ConnectionError(f"Socket error from '{host}:{port}' - {str(e)}.") from e


def udp_scrape_request(
    socket_obj: socket.socket,
    hashes: List[str],
    connection_id: int,
    transaction_id: int,
) -> bytes:
    """
    Creates a scrape request

    Args:
        socket_obj: Socket object.
        hashes: List (>1) or string of infohash(es).
        connection_id: Connection ID.
        transaction_id: Transaction ID.

    Returns:
        bytes: Scrape request.
    """
    action = 2  # Action (2 = scrape)

    buffer = struct.pack(">QII", connection_id, action, transaction_id)

    for infohash in hashes:
        buffer += collect_info_hash(infohash)

    return buffer


@dataclass
class UdpAnnounceParams:
    """Parameters for UDP announce request."""

    action: int = 1  # Action (1 = announce)
    downloaded: int = 0
    left: int = 0
    uploaded: int = 0
    event: int = 0
    ip: int = 0
    key: int = 0
    num_want: int = -1
    port: int = 6889


def udp_announce(
    socket_obj: socket.socket, hashes: List[str], connection_id: int
) -> Dict[str, Dict[str, int]]:
    """
    Sends an announce request

    Args:
        socket_obj: Socket object.
        hashes: List (>1) or string of infohash(es).
        connection_id: Connection ID.

    Returns:
        dict: Dictionary of results.
    """
    if len(hashes) > 1:
        raise ValueError(f"Too many hashes for UDP announce ({len(hashes)}).")

    transaction_id = random.randint(0, 2147483647)
    infohash = collect_info_hash(hashes[0])
    peer_id = random_peer_id()
    params = UdpAnnounceParams()

    buffer = struct.pack(
        ">QII20s20sQQQIIIiH",
        connection_id,
        params.action,
        transaction_id,
        infohash,
        peer_id,
        params.downloaded,
        params.left,
        params.uploaded,
        params.event,
        params.ip,
        params.key,
        params.num_want,
        params.port,
    )

    try:
        socket_obj.send(buffer)
        result: Tuple[int, int, int] = udp_verify_announce(socket_obj, transaction_id)

        return {
            hashes[0]: {
                "seeders": result[0],
                "leechers": result[1],
                "completed": result[2],
            }
        }
    except socket.error as e:
        raise ConnectionError(f"Failed to send announce request - {str(e)}.") from e


def udp_verify_announce(
    socket_obj: socket.socket, transaction_id: int
) -> Tuple[int, int, int]:
    """
    Verifies an announce response

    Args:
        socket_obj: Socket object.
        transaction_id: Transaction ID.

    Returns:
        tuple: Tuple containing seeders, leechers, and completed.
    """
    try:
        response = socket_obj.recv(20)
    except socket.error as e:
        raise ConnectionError(f"Failed to receive announce response - {str(e)}.") from e

    if len(response) < 20:
        raise ValueError(f"Invalid announce response length ({len(response)}).")

    return_action: int
    return_transaction_id: int
    _: int  # interval
    leechers: int
    seeders: int
    return_action, return_transaction_id, _, leechers, seeders = struct.unpack(
        ">IIIII", response  # type: ignore[misc]
    )

    if return_transaction_id != transaction_id:
        raise ValueError(
            f"Invalid transaction ID ({return_transaction_id} != {transaction_id})."
        )

    if return_action != 1:
        raise ValueError(f"Invalid action code ({return_action}).")

    return (seeders, leechers, 0)


def udp_scrape_data(
    response: bytes,
    hashes: List[str],
    host: str,
    keys: List[str],
    *,
    start: int,
    end: int,
    offset: int,
) -> Dict[str, Dict[str, int]]:
    """
    Parses scrape response

    Args:
        response: Response from the tracker.
        hashes: List (>1) or string of infohash(es).
        host: Domain or IP address of the tracker.
        keys: List of infohash keys.
        start: Start position in the response.
        end: End position in the response.
        offset: Offset for each result.

    Returns:
        dict: Dictionary of results.
    """
    results: Dict[str, Dict[str, int]] = {}

    # Check if there is enough data for all hashes
    if (end - start) < (len(hashes) * offset):
        raise ValueError(f"Invalid scrape response from '{host}'.")

    # Parse each hash
    for i, _ in enumerate(hashes):
        pos: int = start + (i * offset)
        seeders: int
        completed: int
        leechers: int
        seeders, completed, leechers = struct.unpack(  # type: ignore[misc]
            ">III", response[pos : pos + 12]
        )

        results[keys[i]] = {
            "seeders": seeders,
            "completed": completed,
            "leechers": leechers,
        }

    return results
