"""
HTTP scraping functionality for Scrapeer.
"""

import urllib.request
import urllib.parse
import re
import socket


def scrape_http(infohashes, protocol, host, port, passkey, announce, timeout):
    """
    Initiates the HTTP(S) scraping

    Args:
        infohashes: List (>1) or string of infohash(es).
        protocol: Protocol to use for the scraping.
        host: Domain or IP address of the tracker.
        port: Optional. Port number of the tracker.
        passkey: Optional. Passkey provided in the scrape request.
        announce: Optional. Use announce instead of scrape.
        timeout: Maximum time for each tracker scrape in seconds.

    Returns:
        dict: Dictionary of results.
    """
    if announce:
        response = http_announce(infohashes, protocol, host, port, passkey, timeout)
    else:
        query = http_query(infohashes, protocol, host, port, passkey)
        response = http_request(query, host, port, timeout)
    
    results = http_data(response, infohashes, host)
    return results


def http_query(infohashes, protocol, host, port, passkey):
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
        query += '?'
        
        for index, infohash in enumerate(infohashes):
            query += f"info_hash={urllib.parse.quote(bytes.fromhex(infohash))}"
            
            if index < len(infohashes) - 1:
                query += '&'
    elif len(infohashes) == 1:
        query += f"?info_hash={urllib.parse.quote(bytes.fromhex(infohashes[0]))}"
        
    return query


def http_request(query, host, port, timeout):
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
            query,
            headers={'User-Agent': 'Scrapeer-py/1.0.0'}
        )
        response = urllib.request.urlopen(request).read()
        return response
    except Exception as e:
        raise Exception(f"Connection error: {host}:{port} - {str(e)}")


def http_announce(infohashes, protocol, host, port, passkey, timeout):
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
        raise Exception(f"Too many hashes for HTTP announce ({len(infohashes)}).")

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
            query,
            headers={'User-Agent': 'Scrapeer-py/1.0.0'}
        )
        response = urllib.request.urlopen(request).read()
        return response
    except Exception as e:
        raise Exception(f"Connection error: {host}:{port} - {str(e)}")


def http_data(response, infohashes, host):
    """
    Gets the data from HTTP(S) response

    Args:
        response: Response from the tracker.
        infohashes: List (>1) or string of infohash(es).
        host: Domain or IP address of the tracker.

    Returns:
        dict: Dictionary of results.
    """
    data = str(response)
    results = {}
    pattern_all = r"d8:completei(\d+)e10:downloadedi(\d+)e10:incompletei(\d+)e"
    pattern_single = r"d8:completei(\d+)e10:incompletei(\d+)e"
    
    for infohash in infohashes:
        pattern = f"{infohash}:{pattern_all}"
        matches = re.search(pattern, data, re.IGNORECASE)
        
        if matches:
            results[infohash] = {
                'seeders': int(matches.group(1)),
                'completed': int(matches.group(2)),
                'leechers': int(matches.group(3)),
            }
        else:
            pattern = f"{infohash}:{pattern_single}"
            matches = re.search(pattern, data, re.IGNORECASE)
            
            if matches:
                results[infohash] = {
                    'seeders': int(matches.group(1)),
                    'completed': 0,
                    'leechers': int(matches.group(2)),
                }
            else:
                info = get_information(data, 'd5:filesd', 'ee')
                
                if info:
                    pattern = f"20:{bytes.fromhex(infohash).decode('latin-1', errors='ignore')}d"
                    start = info.find(pattern)
                    
                    if start != -1:
                        info = info[start:]
                        end = info.find('e')
                        info = info[:end + 1]
                        
                        seeders = re.search(r"completei(\d+)e", info, re.IGNORECASE)
                        leechers = re.search(r"incompletei(\d+)e", info, re.IGNORECASE)
                        completed = re.search(r"downloadedi(\d+)e", info, re.IGNORECASE)
                        
                        seeders = int(seeders.group(1)) if seeders else 0
                        leechers = int(leechers.group(1)) if leechers else 0
                        completed = int(completed.group(1)) if completed else 0
                        
                        results[infohash] = {
                            'seeders': seeders,
                            'completed': completed,
                            'leechers': leechers,
                        }
                    else:
                        raise Exception(f"Failed to parse torrent data from '{host}'.")
                else:
                    raise Exception(f"Invalid scrape response from '{host}'.")
    
    return results


def get_information(data, start, end):
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