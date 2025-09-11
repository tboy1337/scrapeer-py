"""Tests for scrapeer.utils module."""

import binascii
from typing import List
from unittest.mock import patch, MagicMock

import pytest

from scrapeer.utils import (
    normalize_infohashes,
    get_passkey,
    random_peer_id,
    collect_info_hash,
)


class TestNormalizeInfohashes:
    """Tests for normalize_infohashes function."""

    def test_valid_single_hash(self) -> None:
        """Test with a valid single infohash."""
        errors: List[str] = []
        hash_str = "a1b2c3d4e5f6789012345678901234567890abcd"
        result = normalize_infohashes(hash_str, errors)

        assert result == ["a1b2c3d4e5f6789012345678901234567890abcd"]
        assert not errors

    def test_valid_multiple_hashes(self) -> None:
        """Test with multiple valid infohashes."""
        errors: List[str] = []
        hashes = [
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "B1C2D3E4F5678901234567890123456789ABCDEF",
        ]
        result = normalize_infohashes(hashes, errors)

        assert result == [
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "b1c2d3e4f5678901234567890123456789abcdef",
        ]
        assert not errors

    def test_mixed_case_normalization(self) -> None:
        """Test that uppercase hashes are converted to lowercase."""
        errors: List[str] = []
        hash_str = "A1B2C3D4E5F6789012345678901234567890ABCD"
        result = normalize_infohashes(hash_str, errors)

        assert result == ["a1b2c3d4e5f6789012345678901234567890abcd"]
        assert not errors

    def test_invalid_hash_too_short(self) -> None:
        """Test with infohash that's too short."""
        errors: List[str] = []
        hash_str = "a1b2c3d4e5f6789012345678901234567890abc"  # 39 chars

        with pytest.raises(
            ValueError, match="No valid infohashes found \\(0 valid\\)"
        ):
            normalize_infohashes(hash_str, errors)

        assert len(errors) == 1
        assert "Invalid info hash format skipped" in errors[0]

    def test_invalid_hash_too_long(self) -> None:
        """Test with infohash that's too long."""
        errors: List[str] = []
        hash_str = "a1b2c3d4e5f6789012345678901234567890abcde"  # 41 chars

        with pytest.raises(
            ValueError, match="No valid infohashes found \\(0 valid\\)"
        ):
            normalize_infohashes(hash_str, errors)

        assert len(errors) == 1
        assert "Invalid info hash format skipped" in errors[0]

    def test_invalid_hash_non_hex(self) -> None:
        """Test with infohash containing non-hex characters."""
        errors: List[str] = []
        hash_str = "g1b2c3d4e5f6789012345678901234567890abcd"  # contains 'g'

        with pytest.raises(
            ValueError, match="No valid infohashes found \\(0 valid\\)"
        ):
            normalize_infohashes(hash_str, errors)

        assert len(errors) == 1
        assert "Invalid info hash format skipped" in errors[0]

    def test_mixed_valid_invalid_hashes(self) -> None:
        """Test with mix of valid and invalid hashes."""
        errors: List[str] = []
        hashes = [
            "a1b2c3d4e5f6789012345678901234567890abcd",  # valid
            "invalid_hash",  # invalid
            "b1c2d3e4f5678901234567890123456789abcdef",  # valid
        ]
        result = normalize_infohashes(hashes, errors)

        assert result == [
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "b1c2d3e4f5678901234567890123456789abcdef",
        ]
        assert len(errors) == 1
        assert "Invalid info hash format skipped" in errors[0]

    def test_empty_list(self) -> None:
        """Test with empty list."""
        errors: List[str] = []

        with pytest.raises(
            ValueError, match="No valid infohashes found \\(0 valid\\)"
        ):
            normalize_infohashes([], errors)

    def test_too_many_hashes(self) -> None:
        """Test with more than 64 hashes."""
        errors: List[str] = []
        hashes = ["a1b2c3d4e5f6789012345678901234567890abcd"] * 65

        with pytest.raises(
            ValueError, match="Too many infohashes provided \\(65, max 64\\)"
        ):
            normalize_infohashes(hashes, errors)

    def test_exactly_64_hashes(self) -> None:
        """Test with exactly 64 hashes (boundary condition)."""
        errors: List[str] = []
        hash_base = "a1b2c3d4e5f6789012345678901234567890abc"
        hashes = (
            [hash_base + f"{i:01x}" for i in range(16)]
            + [hash_base + f"{i:01x}" for i in range(16)]
            + [hash_base + f"{i:01x}" for i in range(16)]
            + [hash_base + f"{i:01x}" for i in range(16)]
        )

        result = normalize_infohashes(hashes, errors)
        assert len(result) == 64
        assert not errors

    def test_none_infohashes(self) -> None:
        """Test with None infohashes."""
        errors: List[str] = []
        with pytest.raises(ValueError, match="Infohashes cannot be None"):
            normalize_infohashes(None, errors)  # type: ignore

    def test_invalid_type_infohashes(self) -> None:
        """Test with invalid type for infohashes."""
        errors: List[str] = []
        with pytest.raises(TypeError, match="Infohashes must be a string or list, got int"):
            normalize_infohashes(123, errors)  # type: ignore

    def test_empty_infohash_in_list(self) -> None:
        """Test with empty string in infohashes list."""
        errors: List[str] = []
        result = normalize_infohashes(
            [
                "a1b2c3d4e5f6789012345678901234567890abcd",
                "",
                "b2c3d4e5f6789012345678901234567890abcdef"
            ],
            errors
        )

        assert result == [
            "a1b2c3d4e5f6789012345678901234567890abcd", "b2c3d4e5f6789012345678901234567890abcdef"
        ]
        assert "Empty info hash skipped." in errors


class TestGetPasskey:
    """Tests for get_passkey function."""

    def test_valid_passkey(self) -> None:
        """Test extracting valid 32-char passkey."""
        path = "/announce/abcdef1234567890abcdef1234567890"
        result = get_passkey(path)
        assert result == "/abcdef1234567890abcdef1234567890"

    def test_passkey_in_middle_of_path(self) -> None:
        """Test passkey in the middle of path."""
        path = "/some/path/abcdef1234567890abcdef1234567890/announce"
        result = get_passkey(path)
        assert result == "/abcdef1234567890abcdef1234567890"

    def test_uppercase_passkey(self) -> None:
        """Test with uppercase passkey."""
        path = "/ABCDEF1234567890ABCDEF1234567890"
        result = get_passkey(path)
        assert result == "/ABCDEF1234567890ABCDEF1234567890"

    def test_mixed_case_passkey(self) -> None:
        """Test with mixed case passkey."""
        path = "/AbCdEf1234567890aBcDeF1234567890"
        result = get_passkey(path)
        assert result == "/AbCdEf1234567890aBcDeF1234567890"

    def test_no_passkey(self) -> None:
        """Test path without passkey."""
        path = "/announce"
        result = get_passkey(path)
        assert result == ""

    def test_empty_path(self) -> None:
        """Test with empty path."""
        result = get_passkey("")
        assert result == ""

    def test_none_path(self) -> None:
        """Test with None path."""
        result = get_passkey(None)
        assert result == ""

    def test_passkey_too_short(self) -> None:
        """Test with passkey that's too short."""
        path = "/announce/abcdef1234567890abcdef123456789"  # 31 chars
        result = get_passkey(path)
        assert result == ""

    def test_passkey_too_long(self) -> None:
        """Test with passkey that's too long (should still match first 32)."""
        path = "/announce/abcdef1234567890abcdef1234567890a"  # 33 chars
        result = get_passkey(path)
        assert result == "/abcdef1234567890abcdef1234567890"

    def test_multiple_potential_passkeys(self) -> None:
        """Test with multiple potential passkey matches (should return first)."""
        path = "/abcdef1234567890abcdef1234567890/fedcba0987654321fedcba0987654321"
        result = get_passkey(path)
        assert result == "/abcdef1234567890abcdef1234567890"


class TestRandomPeerId:
    """Tests for random_peer_id function."""

    def test_peer_id_format(self) -> None:
        """Test that peer ID has correct format and length."""
        peer_id = random_peer_id()

        assert isinstance(peer_id, bytes)
        assert len(peer_id) == 20
        assert peer_id.startswith(b"-PY0001-")

    def test_peer_id_uniqueness(self) -> None:
        """Test that multiple calls generate different peer IDs."""
        peer_id1 = random_peer_id()
        peer_id2 = random_peer_id()

        # They should be different (very high probability)
        assert peer_id1 != peer_id2

    def test_peer_id_suffix_digits(self) -> None:
        """Test that suffix contains only digits."""
        peer_id = random_peer_id()
        suffix = peer_id[8:]  # Skip '-PY0001-' prefix

        # Should be 12 digits
        assert len(suffix) == 12
        for byte in suffix:
            char = chr(byte)
            assert char.isdigit(), f"Non-digit character found: {char}"

    @patch("random.randint")
    def test_peer_id_deterministic(self, mock_randint: MagicMock) -> None:
        """Test peer ID generation with mocked randomness."""
        # Mock randint to return predictable values
        mock_randint.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1]

        peer_id = random_peer_id()
        expected = b"-PY0001-012345678901"

        assert peer_id == expected


class TestCollectInfoHash:
    """Tests for collect_info_hash function."""

    def test_valid_infohash(self) -> None:
        """Test converting valid hex string to bytes."""
        infohash = "a1b2c3d4e5f6789012345678901234567890abcd"
        result = collect_info_hash(infohash)

        expected = binascii.unhexlify(infohash)
        assert result == expected
        assert len(result) == 20  # 40 hex chars = 20 bytes

    def test_uppercase_infohash(self) -> None:
        """Test with uppercase hex string."""
        infohash = "A1B2C3D4E5F6789012345678901234567890ABCD"
        result = collect_info_hash(infohash)

        expected = binascii.unhexlify(infohash)
        assert result == expected

    def test_mixed_case_infohash(self) -> None:
        """Test with mixed case hex string."""
        infohash = "a1B2c3D4e5F6789012345678901234567890AbCd"
        result = collect_info_hash(infohash)

        expected = binascii.unhexlify(infohash)
        assert result == expected

    def test_all_zeros(self) -> None:
        """Test with all zeros."""
        infohash = "0" * 40
        result = collect_info_hash(infohash)

        expected = b"\x00" * 20
        assert result == expected

    def test_all_fs(self) -> None:
        """Test with all F's."""
        infohash = "f" * 40
        result = collect_info_hash(infohash)

        expected = b"\xff" * 20
        assert result == expected

    def test_invalid_hex_raises_error(self) -> None:
        """Test that invalid hex raises binascii.Error."""
        infohash = "g1b2c3d4e5f6789012345678901234567890abcd"  # contains 'g'

        with pytest.raises(binascii.Error):
            collect_info_hash(infohash)

    def test_wrong_length_raises_error(self) -> None:
        """Test that wrong length hex string raises binascii.Error."""
        infohash = "a1b2c3d4e5f6789012345678901234567890abc"  # 39 chars

        with pytest.raises(binascii.Error):
            collect_info_hash(infohash)
