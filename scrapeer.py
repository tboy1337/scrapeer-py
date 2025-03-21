"""
Scrapeer-py, a tiny Python library that lets you scrape
HTTP(S) and UDP trackers for torrent information.

Port of the original PHP Scrapeer library by TorrentPier.
"""

import socket
import struct
import random
import urllib.request
import urllib.parse
import re
import binascii


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
            self.infohashes = self.normalize_infohashes(hashes)
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
                passkey = self.get_passkey(path)
                
                result = self.try_scrape(protocol, host, port, passkey, announce)
                final_result.update(result)
                continue
            break

        return final_result

    def normalize_infohashes(self, infohashes):
        """
        Normalizes the given hashes

        Args:
            infohashes: List of infohash(es).

        Returns:
            list: Normalized infohash(es).
        """
        if not isinstance(infohashes, list):
            infohashes = [infohashes]

        normalized = []
        for infohash in infohashes:
            # Convert to lowercase for consistency
            infohash = infohash.lower()
            if not re.match(r'^[a-f0-9]{40}$', infohash):
                self.errors.append(f'Invalid info hash skipped ({infohash}).')
            else:
                normalized.append(infohash)

        total_infohashes = len(normalized)
        if total_infohashes > 64 or total_infohashes < 1:
            raise ValueError(f'Invalid amount of valid infohashes ({total_infohashes}).')

        return normalized

    def get_passkey(self, path):
        """
        Returns the passkey found in the scrape request.

        Args:
            path: Path from the scrape request.

        Returns:
            str: Passkey or empty string.
        """
        if path and re.search(r'[a-z0-9]{32}', path, re.IGNORECASE):
            matches = re.search(r'[a-z0-9]{32}', path, re.IGNORECASE)
            return f'/{matches.group(0)}'
        return ''

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
                results = self.scrape_udp(infohashes, host, port, announce)
            elif protocol == 'http':
                port = port if port else 80
                results = self.scrape_http(infohashes, protocol, host, port, passkey, announce)
            elif protocol == 'https':
                port = port if port else 443
                results = self.scrape_http(infohashes, protocol, host, port, passkey, announce)
            else:
                raise Exception(f'Unsupported protocol ({protocol}://{host}).')
        except Exception as e:
            self.infohashes = infohashes
            self.errors.append(str(e))
        
        return results

    def scrape_http(self, infohashes, protocol, host, port, passkey, announce):
        """
        Initiates the HTTP(S) scraping

        Args:
            infohashes: List (>1) or string of infohash(es).
            protocol: Protocol to use for the scraping.
            host: Domain or IP address of the tracker.
            port: Optional. Port number of the tracker.
            passkey: Optional. Passkey provided in the scrape request.
            announce: Optional. Use announce instead of scrape.

        Returns:
            dict: Dictionary of results.
        """
        if announce:
            response = self.http_announce(infohashes, protocol, host, port, passkey)
        else:
            query = self.http_query(infohashes, protocol, host, port, passkey)
            response = self.http_request(query, host, port)
        
        results = self.http_data(response, infohashes, host)
        return results

    def http_query(self, infohashes, protocol, host, port, passkey):
        """
        Builds the HTTP(S) query

        Args:
            infohashes: List (>1) or string of infohash(es).
            protocol: Protocol to use for the scraping.
            host: Domain or IP address of the tracker.
            port: Port number of the tracker.
            passkey: Optional. Passkey provided in the scrape request.

        Returns:
            str: Request query.
        """
        tracker_url = f"{protocol}://{host}:{port}{passkey}"
        scrape_query = ''

        for index, infohash in enumerate(infohashes):
            if index > 0:
                scrape_query += '&info_hash=' + urllib.parse.quote(binascii.unhexlify(infohash))
            else:
                scrape_query += '/scrape?info_hash=' + urllib.parse.quote(binascii.unhexlify(infohash))
        
        request_query = tracker_url + scrape_query
        return request_query

    def http_request(self, query, host, port):
        """
        Executes the query and returns the result

        Args:
            query: The query that will be executed.
            host: Domain or IP address of the tracker.
            port: Port number of the tracker.

        Returns:
            str: Request response.
        """
        try:
            # Create a request with timeout
            req = urllib.request.Request(query)
            response = urllib.request.urlopen(req, timeout=self.timeout).read()
        except Exception:
            raise Exception(f'Invalid scrape connection ({host}:{port}).')

        if not response.startswith(b'd5:filesd20:'):
            raise Exception(f'Invalid scrape response ({host}:{port}).')

        return response

    def http_announce(self, infohashes, protocol, host, port, passkey):
        """
        Builds the query, sends the announce request and returns the data

        Args:
            infohashes: List (>1) or string of infohash(es).
            protocol: Protocol to use for the scraping.
            host: Domain or IP address of the tracker.
            port: Port number of the tracker.
            passkey: Optional. Passkey provided in the scrape request.

        Returns:
            bytes: Request response.
        """
        tracker_url = f"{protocol}://{host}:{port}{passkey}"
        response_data = b''

        for infohash in infohashes:
            query = tracker_url + '/announce?info_hash=' + urllib.parse.quote(binascii.unhexlify(infohash))
            try:
                req = urllib.request.Request(query)
                response = urllib.request.urlopen(req, timeout=self.timeout).read()
            except Exception:
                raise Exception(f'Invalid announce connection ({host}:{port}).')

            if not response.startswith(b'd8:completei') or response.startswith(b'd8:completei0e10:downloadedi0e10:incompletei1e'):
                continue

            ben_hash = b'20:' + binascii.unhexlify(infohash) + b'd'
            response_data += ben_hash + response

        return response_data

    def http_data(self, response, infohashes, host):
        """
        Parses the response and returns the data

        Args:
            response: The response that will be parsed.
            infohashes: List of infohash(es).
            host: Domain or IP address of the tracker.

        Returns:
            dict: Parsed data.
        """
        torrents_data = {}

        for infohash in infohashes:
            ben_hash = b'20:' + binascii.unhexlify(infohash) + b'd'
            start_pos = response.find(ben_hash)
            
            if start_pos != -1:
                start = start_pos + 24
                head = response[start:]
                end = head.find(b'ee') + 1
                data = response[start:start+end]

                seeders = b'8:completei'
                seeders_val = self.get_information(data, seeders, b'e')

                completed = b'10:downloadedi'
                completed_val = self.get_information(data, completed, b'e')

                leechers = b'10:incompletei'
                leechers_val = self.get_information(data, leechers, b'e')

                torrents_data[infohash] = {
                    'seeders': seeders_val, 
                    'completed': completed_val, 
                    'leechers': leechers_val
                }
            else:
                self.collect_info_hash(infohash)
                self.errors.append(f'Invalid infohash ({infohash}) for tracker: {host}.')

        return torrents_data

    def get_information(self, data, start, end):
        """
        Parses a string and returns the data between start and end.

        Args:
            data: The data that will be parsed.
            start: Beginning part of the data.
            end: Ending part of the data.
            
        Returns:
            int: Parsed information or 0.
        """
        start_pos = data.find(start)
        if start_pos != -1:
            start_idx = start_pos + len(start)
            head = data[start_idx:]
            end_idx = head.find(end)
            information = data[start_idx:start_idx+end_idx]

            return int(information)
        return 0

    def scrape_udp(self, infohashes, host, port, announce):
        """
        Initiates the UDP scraping

        Args:
            infohashes: List (>1) or string of infohash(es).
            host: Domain or IP address of the tracker.
            port: Optional. Port number of the tracker.
            announce: Optional. Use announce instead of scrape.
            
        Returns:
            dict: Dictionary of results.
        """
        socket_obj, transaction_id, connection_id = self.prepare_udp(host, port)

        if announce:
            response = self.udp_announce(socket_obj, infohashes, connection_id)
            keys = 'leechers/seeders'
            start = 12
            end = 16
            offset = 20
        else:
            response = self.udp_scrape(socket_obj, infohashes, connection_id, transaction_id, host, port)
            keys = 'seeders/completed/leechers'
            start = 8
            end = offset = 12

        return self.udp_scrape_data(response, infohashes, host, keys, start, end, offset)

    def prepare_udp(self, host, port):
        """
        Prepares the UDP connection

        Args:
            host: Domain or IP address of the tracker.
            port: Optional. Port number of the tracker.
            
        Returns:
            tuple: Created socket, transaction ID and connection ID.
        """
        socket_obj = self.udp_create_connection(host, port)
        transaction_id = self.udp_connection_request(socket_obj)
        connection_id = self.udp_connection_response(socket_obj, transaction_id, host, port)

        return (socket_obj, transaction_id, connection_id)

    def udp_create_connection(self, host, port):
        """
        Creates the UDP socket and establishes the connection

        Args:
            host: Domain or IP address of the tracker.
            port: Port number of the tracker.
            
        Returns:
            socket: Created and connected socket.
        """
        try:
            socket_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_obj.settimeout(self.timeout)
            socket_obj.connect((host, port))
            return socket_obj
        except socket.error:
            raise Exception("Couldn't create socket.")

    def udp_connection_request(self, socket_obj):
        """
        Writes to the connected socket and returns the transaction ID

        Args:
            socket_obj: The socket object.
            
        Returns:
            int: The transaction ID.
        """
        connection_id = b'\x00\x00\x04\x17\x27\x10\x19\x80'
        action = struct.pack('>I', 0)
        transaction_id = random.randint(0, 2147483647)
        buffer = connection_id + action + struct.pack('>I', transaction_id)
        
        try:
            socket_obj.send(buffer)
            return transaction_id
        except socket.error:
            socket_obj.close()
            raise Exception("Couldn't write to socket.")

    def udp_connection_response(self, socket_obj, transaction_id, host, port):
        """
        Reads the connection response and returns the connection ID

        Args:
            socket_obj: The socket object.
            transaction_id: The transaction ID.
            host: Domain or IP address of the tracker.
            port: Port number of the tracker.
            
        Returns:
            bytes: The connection ID.
        """
        try:
            response = socket_obj.recv(16)
        except socket.error:
            socket_obj.close()
            raise Exception(f'Invalid scrape connection! ({host}:{port}).')

        if len(response) < 16:
            socket_obj.close()
            raise Exception(f'Invalid scrape response ({host}:{port}).')

        action, resp_transaction_id = struct.unpack('>II', response[0:8])
        if action != 0 or resp_transaction_id != transaction_id:
            socket_obj.close()
            raise Exception(f'Invalid scrape result ({host}:{port}).')

        connection_id = response[8:16]
        return connection_id

    def udp_scrape(self, socket_obj, hashes, connection_id, transaction_id, host, port):
        """
        Reads the socket response and returns the torrent data

        Args:
            socket_obj: The socket object.
            hashes: List (>1) or string of infohash(es).
            connection_id: The connection ID.
            transaction_id: The transaction ID.
            host: Domain or IP address of the tracker.
            port: Port number of the tracker.
            
        Returns:
            bytes: Response data.
        """
        self.udp_scrape_request(socket_obj, hashes, connection_id, transaction_id)

        read_length = 8 + (12 * len(hashes))
        try:
            response = socket_obj.recv(read_length)
        except socket.error:
            socket_obj.close()
            raise Exception(f'Invalid scrape connection ({host}:{port}).')
        
        socket_obj.close()

        if len(response) < read_length:
            raise Exception(f'Invalid scrape response ({host}:{port}).')

        action, resp_transaction_id = struct.unpack('>II', response[0:8])
        if action != 2 or resp_transaction_id != transaction_id:
            raise Exception(f'Invalid scrape result ({host}:{port}).')

        return response

    def udp_scrape_request(self, socket_obj, hashes, connection_id, transaction_id):
        """
        Writes to the connected socket

        Args:
            socket_obj: The socket object.
            hashes: List (>1) or string of infohash(es).
            connection_id: The connection ID.
            transaction_id: The transaction ID.
        """
        action = struct.pack('>I', 2)
        
        infohashes = b''
        for infohash in hashes:
            infohashes += binascii.unhexlify(infohash)

        buffer = connection_id + action + struct.pack('>I', transaction_id) + infohashes
        
        try:
            socket_obj.send(buffer)
        except socket.error:
            socket_obj.close()
            raise Exception("Couldn't write to socket.")

    def udp_announce(self, socket_obj, hashes, connection_id):
        """
        Writes the announce to the connected socket

        Args:
            socket_obj: The socket object.
            hashes: List (>1) or string of infohash(es).
            connection_id: The connection ID.
            
        Returns:
            bytes: Torrent(s) data.
        """
        action = struct.pack('>I', 1)
        downloaded = left = uploaded = b'\x30\x30\x30\x30\x30\x30\x30\x30'
        peer_id = self.random_peer_id()
        event = struct.pack('>I', 3)
        ip_addr = struct.pack('>I', 0)
        key = struct.pack('>I', random.randint(0, 2147483647))
        num_want = -1
        ann_port = struct.pack('>I', random.randint(0, 255))

        response_data = b''
        for infohash in hashes:
            transaction_id = random.randint(0, 2147483647)
            buffer = (connection_id + action + struct.pack('>I', transaction_id) + binascii.unhexlify(infohash) +
                     peer_id + downloaded + left + uploaded + event + ip_addr + key + struct.pack('>i', num_want) + ann_port)

            try:
                socket_obj.send(buffer)
            except socket.error:
                socket_obj.close()
                raise Exception("Couldn't write announce to socket.")

            response = self.udp_verify_announce(socket_obj, transaction_id)
            if response is False:
                continue

            response_data += response

        socket_obj.close()
        return response_data

    def random_peer_id(self):
        """
        Generates a random peer ID

        Returns:
            bytes: Generated peer ID.
        """
        identifier = b'-SP0054-'
        chars = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        
        # Generate 12 random bytes from chars
        random_chars = b''.join([bytes([chars[random.randint(0, len(chars)-1)]]) for _ in range(12)])
        
        return identifier + random_chars

    def udp_verify_announce(self, socket_obj, transaction_id):
        """
        Verifies the correctness of the announce response

        Args:
            socket_obj: The socket object.
            transaction_id: The transaction ID.
            
        Returns:
            bytes: Response data or False.
        """
        try:
            response = socket_obj.recv(20)
        except socket.error:
            return False

        if len(response) < 20:
            return False

        action, resp_transaction_id = struct.unpack('>II', response[0:8])
        if action != 1 or resp_transaction_id != transaction_id:
            return False

        return response

    def udp_scrape_data(self, response, hashes, host, keys, start, end, offset):
        """
        Reads the socket response and returns the torrent data

        Args:
            response: Data from the request response.
            hashes: List (>1) or string of infohash(es).
            host: Domain or IP address of the tracker.
            keys: Keys for the unpacked information.
            start: Start of the content we want to unpack.
            end: End of the content we want to unpack.
            offset: Offset to the next content part.
            
        Returns:
            dict: Scraped torrent data.
        """
        torrents_data = {}

        for infohash in hashes:
            byte_string = response[start:start+end]
            
            # Verify we have content
            if len(byte_string) == end:
                if keys == 'seeders/completed/leechers':
                    seeders, completed, leechers = struct.unpack('>III', byte_string)
                    torrents_data[infohash] = {'seeders': seeders, 'completed': completed, 'leechers': leechers}
                else:  # keys == 'leechers/seeders'
                    leechers, seeders = struct.unpack('>II', byte_string)
                    torrents_data[infohash] = {'seeders': seeders, 'leechers': leechers, 'completed': 0}
            else:
                self.collect_info_hash(infohash)
                self.errors.append(f'Invalid info-hash ({infohash}) for tracker: {host}.')
            
            start += offset

        return torrents_data

    def collect_info_hash(self, infohash):
        """
        Collects info-hashes that couldn't be scraped.

        Args:
            infohash: Info hash that wasn't scraped.
        """
        self.infohashes.append(infohash)

    def has_errors(self):
        """
        Checks if there are any errors

        Returns:
            bool: True or false, depending on if errors are present or not.
        """
        return len(self.errors) > 0

    def get_errors(self):
        """
        Returns all the errors that were logged

        Returns:
            list: All the logged errors.
        """
        return self.errors
