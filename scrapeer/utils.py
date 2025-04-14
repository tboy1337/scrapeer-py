"""
Utility functions for Scrapeer.
"""

import re
import random
import binascii


def normalize_infohashes(infohashes, errors):
    """
    Normalizes the given hashes

    Args:
        infohashes: List of infohash(es).
        errors: List to append any errors to.

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
            errors.append(f'Invalid info hash skipped ({infohash}).')
        else:
            normalized.append(infohash)

    total_infohashes = len(normalized)
    if total_infohashes > 64 or total_infohashes < 1:
        raise ValueError(f'Invalid amount of valid infohashes ({total_infohashes}).')

    return normalized


def get_passkey(path):
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


def random_peer_id():
    """
    Generate a random peer_id.

    Returns:
        bytes: A random peer_id.
    """
    return '-PY0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)]).encode()


def collect_info_hash(infohash):
    """
    Converts infohash to binary.

    Args:
        infohash: Infohash to convert.

    Returns:
        bytes: Binary representation of the infohash.
    """
    return binascii.unhexlify(infohash) 