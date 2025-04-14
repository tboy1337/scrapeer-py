"""
UDP scraping functionality for Scrapeer.
"""

import socket
import struct
import random
from .utils import random_peer_id, collect_info_hash


def scrape_udp(infohashes, host, port, announce, timeout):
    """
    Initiates the UDP scraping

    Args:
        infohashes: List (>1) or string of infohash(es).
        host: Domain or IP address of the tracker.
        port: Port number of the tracker.
        announce: Optional. Use announce instead of scrape.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        dict: Dictionary of results.
    """
    socket_obj, ip = prepare_udp(host, port)
    socket_obj.settimeout(timeout)
    
    try:
        transaction_id, connection_id = udp_connection_request(socket_obj)
        connection_id = udp_connection_response(socket_obj, transaction_id, host, port)
        
        if announce:
            return udp_announce(socket_obj, infohashes, connection_id)
        else:
            return udp_scrape(socket_obj, infohashes, connection_id, transaction_id, host, port)
    finally:
        socket_obj.close()


def prepare_udp(host, port):
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
    except socket.gaierror:
        raise Exception(f"Failed to resolve host '{host}'.")
    
    return socket_obj, ip


def udp_create_connection(host, port):
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
        raise Exception(f"Failed to create socket for '{host}:{port}' - {str(e)}.")


def udp_connection_request(socket_obj):
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
        raise Exception(f"Failed to send connection request - {str(e)}.")
    
    return transaction_id, connection_id


def udp_connection_response(socket_obj, transaction_id, host, port):
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
        raise Exception(f"Failed to receive connection response from '{host}:{port}' - {str(e)}.")
    
    if len(response) != 16:
        raise Exception(f"Invalid response length from '{host}:{port}'.")
    
    return_action, return_transaction_id, connection_id = struct.unpack(">IIQ", response)

    if return_transaction_id != transaction_id:
        raise Exception(f"Invalid transaction ID from '{host}:{port}'.")

    if return_action != 0:
        raise Exception(f"Invalid action from '{host}:{port}'.")
    
    return connection_id


def udp_scrape(socket_obj, hashes, connection_id, transaction_id, host, port):
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
            raise Exception(f"Invalid scrape response from '{host}:{port}'.")
        
        return_action, return_transaction_id = struct.unpack(">II", response[:8])
        
        # Verify transaction ID
        if transaction_id != return_transaction_id:
            raise Exception(f"Invalid transaction ID from '{host}:{port}'.")
        
        # Verify action
        if return_action != action:
            err_msg = struct.unpack(">I", response[4:8])[0]
            raise Exception(f"Tracker error, code: {err_msg} from '{host}:{port}'.")
        
        # Create keys array
        keys = []
        for infohash in hashes:
            keys.append(infohash)
        
        # Parse results
        return udp_scrape_data(response, hashes, host, keys, 8, len(response), 12)
    except socket.error as e:
        raise Exception(f"Socket error from '{host}:{port}' - {str(e)}.")


def udp_scrape_request(socket_obj, hashes, connection_id, transaction_id):
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


def udp_announce(socket_obj, hashes, connection_id):
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
        raise Exception(f"Too many hashes for UDP announce ({len(hashes)}).")
    
    action = 1  # Action (1 = announce)
    transaction_id = random.randint(0, 2147483647)  # Random transaction ID
    
    infohash = collect_info_hash(hashes[0])
    peer_id = random_peer_id()
    downloaded = 0
    left = 0
    uploaded = 0
    event = 0
    ip = 0
    key = 0
    num_want = -1
    port = 6889
    
    buffer = struct.pack(">QII20s20sQQQIIIiH",
                      connection_id, action, transaction_id, infohash, peer_id,
                      downloaded, left, uploaded, event, ip, key, num_want, port)
    
    try:
        socket_obj.send(buffer)
        result = udp_verify_announce(socket_obj, transaction_id)
        
        return {
            hashes[0]: {
                'seeders': result[0],
                'leechers': result[1],
                'completed': result[2],
            }
        }
    except socket.error as e:
        raise Exception(f"Failed to send announce request - {str(e)}.")


def udp_verify_announce(socket_obj, transaction_id):
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
        raise Exception(f"Failed to receive announce response - {str(e)}.")
    
    if len(response) < 20:
        raise Exception(f"Invalid announce response length ({len(response)}).")
    
    return_action, return_transaction_id, interval, leechers, seeders = struct.unpack(">IIIII", response)
    
    if return_transaction_id != transaction_id:
        raise Exception(f"Invalid transaction ID ({return_transaction_id} != {transaction_id}).")
    
    if return_action != 1:
        raise Exception(f"Invalid action code ({return_action}).")
    
    return (seeders, leechers, 0)


def udp_scrape_data(response, hashes, host, keys, start, end, offset):
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
    results = {}
    
    # Check if there is enough data for all hashes
    if (end - start) < (len(hashes) * offset):
        raise Exception(f"Invalid scrape response from '{host}'.")
    
    # Parse each hash
    for i, infohash in enumerate(hashes):
        pos = start + (i * offset)
        
        if pos + 12 <= end:
            seeders, completed, leechers = struct.unpack(">III", response[pos:pos+12])
            
            results[keys[i]] = {
                'seeders': seeders,
                'completed': completed,
                'leechers': leechers,
            }
        else:
            raise Exception(f"Invalid scrape response from '{host}'.")
    
    return results 