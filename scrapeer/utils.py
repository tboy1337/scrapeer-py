"""
Utility functions for Scrapeer.
"""

import binascii
import random
import re
from typing import List, Optional, Union


def normalize_infohashes(
    infohashes: Union[str, List[str]], errors: List[str]
) -> List[str]:
    """
    Normalizes the given hashes

    Args:
        infohashes: List of infohash(es) or single infohash string.
        errors: List to append any errors to.

    Returns:
        list: Normalized infohash(es).

    Raises:
        ValueError: If no valid infohashes remain or too many provided.
        TypeError: If infohashes is not a string or list.
    """
    if infohashes is None:
        raise ValueError("Infohashes cannot be None.")

    if not isinstance(infohashes, (list, str)):
        raise TypeError(
            f"Infohashes must be a string or list, got {type(infohashes).__name__}."
        )

    if isinstance(infohashes, str):
        infohashes = [infohashes]

    normalized = []
    for infohash in infohashes:
        # Convert to lowercase for consistency
        infohash = infohash.lower().strip()

        if not infohash:
            errors.append("Empty info hash skipped.")
            continue

        if not re.match(r"^[a-f0-9]{40}$", infohash):
            errors.append(f"Invalid info hash format skipped ({infohash}).")
        else:
            normalized.append(infohash)

    total_infohashes = len(normalized)
    if total_infohashes < 1:
        raise ValueError(f"No valid infohashes found ({total_infohashes} valid).")
    if total_infohashes > 64:
        raise ValueError(f"Too many infohashes provided ({total_infohashes}, max 64).")

    return normalized


def get_passkey(path: Optional[str]) -> str:
    """
    Returns the passkey found in the scrape request.

    Args:
        path: Path from the scrape request.

    Returns:
        str: Passkey or empty string.
    """
    if not path:
        return ""
    match = re.search(r"[a-z0-9]{32}", path, re.IGNORECASE)
    if match:
        return f"/{match.group(0)}"
    return ""


def random_peer_id() -> bytes:
    """
    Generate a random peer_id.

    Returns:
        bytes: A random peer_id.
    """
    prefix = b"-PY0001-"
    suffix = "".join([str(random.randint(0, 9)) for _ in range(12)])
    return prefix + suffix.encode()


def collect_info_hash(infohash: str) -> bytes:
    """
    Converts infohash to binary.

    Args:
        infohash: Infohash to convert.

    Returns:
        bytes: Binary representation of the infohash.
    """
    return binascii.unhexlify(infohash)
