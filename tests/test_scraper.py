"""Tests for scrapeer.scraper module."""

from unittest.mock import patch

import pytest

from scrapeer._version import get_version
from scrapeer.scraper import Scraper


class TestScraper:  # pylint: disable=too-many-public-methods
    """Tests for Scraper class."""

    def test_init(self) -> None:
        """Test scraper initialization."""
        scraper = Scraper()

        assert not scraper.errors
        assert scraper.infohashes == []
        assert scraper.timeout == 2
        assert scraper.VERSION == get_version()

    def test_has_errors_empty(self) -> None:
        """Test has_errors when no errors."""
        scraper = Scraper()
        assert not scraper.has_errors()

    def test_has_errors_with_errors(self) -> None:
        """Test has_errors when errors exist."""
        scraper = Scraper()
        scraper.errors.append("Test error")
        assert scraper.has_errors()

    def test_get_errors(self) -> None:
        """Test get_errors method."""
        scraper = Scraper()
        scraper.errors.extend(["Error 1", "Error 2"])

        errors = scraper.get_errors()
        assert errors == ["Error 1", "Error 2"]

    def test_scrape_no_trackers(self) -> None:
        """Test scrape with no trackers."""
        scraper = Scraper()
        result = scraper.scrape(["hash1"], [])

        assert not result
        assert "No tracker specified, aborting." in scraper.errors

    def test_scrape_empty_trackers(self) -> None:
        """Test scrape with empty tracker."""
        scraper = Scraper()
        result = scraper.scrape(["hash1"], "")

        assert not result
        assert "No tracker specified, aborting." in scraper.errors

    def test_scrape_single_tracker_string(self) -> None:
        """Test scrape with single tracker as string."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["normalized_hash"]
            with patch.object(scraper, "try_scrape") as mock_try_scrape:
                mock_try_scrape.return_value = {"normalized_hash": {"seeders": 1}}

                result = scraper.scrape([valid_hash], "http://example.com/announce")

                mock_normalize.assert_called_once_with([valid_hash], scraper.errors)
                mock_try_scrape.assert_called_once_with(
                    "http", "example.com", None, "", announce=False
                )
                assert result == {"normalized_hash": {"seeders": 1}}

    def test_scrape_invalid_timeout(self) -> None:
        """Test scrape with invalid timeout."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with pytest.raises(TypeError, match="Timeout must be integer, got str"):
            scraper.scrape([valid_hash], ["http://example.com"], timeout="invalid")  # type: ignore

    def test_scrape_valid_timeout(self) -> None:
        """Test scrape with valid timeout."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["normalized_hash"]
            with patch.object(scraper, "try_scrape") as mock_try_scrape:
                mock_try_scrape.return_value = {}

                _ = scraper.scrape([valid_hash], ["http://example.com"], timeout=10)

                assert scraper.timeout == 10

    def test_scrape_normalize_error(self) -> None:
        """Test scrape when normalize_infohashes raises ValueError."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.side_effect = ValueError("Invalid hashes")

            result = scraper.scrape([valid_hash], ["http://example.com"])

            assert not result
            assert "Invalid hashes" in scraper.errors

    def test_scrape_max_trackers(self) -> None:
        """Test scrape with max_trackers limit."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"
        trackers = ["http://tracker1.com", "http://tracker2.com", "http://tracker3.com"]

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["normalized_hash"]
            with patch.object(scraper, "try_scrape") as mock_try_scrape:
                mock_try_scrape.return_value = {"normalized_hash": {"seeders": 1}}

                _ = scraper.scrape([valid_hash], trackers, max_trackers=2)

                # Should only call try_scrape twice
                assert mock_try_scrape.call_count == 2

    def test_scrape_invalid_tracker_url(self) -> None:
        """Test scrape with invalid tracker URL."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["normalized_hash"]

            _ = scraper.scrape([valid_hash], ["invalid_url"])

            assert "Skipping invalid tracker (invalid_url)." in scraper.errors

    def test_scrape_tracker_with_port(self) -> None:
        """Test scrape with tracker that has port."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["normalized_hash"]
            with patch.object(scraper, "try_scrape") as mock_try_scrape:
                mock_try_scrape.return_value = {}

                _ = scraper.scrape([valid_hash], ["http://example.com:8080/announce"])

                mock_try_scrape.assert_called_once_with(
                    "http", "example.com", 8080, "", announce=False
                )

    def test_scrape_tracker_with_passkey(self) -> None:
        """Test scrape with tracker that has passkey in path."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["normalized_hash"]
            with patch("scrapeer.scraper.get_passkey") as mock_passkey:
                mock_passkey.return_value = "/abc123def456789012345678901234567890"
                with patch.object(scraper, "try_scrape") as mock_try_scrape:
                    mock_try_scrape.return_value = {}

                    _ = scraper.scrape(
                        [valid_hash],
                        [
                            "http://example.com/announce/abc123def456789012345678901234567890"
                        ],
                    )

                    mock_passkey.assert_called_once_with(
                        "/announce/abc123def456789012345678901234567890"
                    )
                    mock_try_scrape.assert_called_once_with(
                        "http",
                        "example.com",
                        None,
                        "/abc123def456789012345678901234567890",
                        announce=False,
                    )

    def test_try_scrape_udp(self) -> None:
        """Test try_scrape with UDP protocol."""
        scraper = Scraper()
        scraper.infohashes = ["hash1"]

        with patch("scrapeer.scraper.scrape_udp") as mock_scrape_udp:
            mock_scrape_udp.return_value = {"hash1": {"seeders": 1}}

            result = scraper.try_scrape("udp", "example.com", None, "", announce=False)

            mock_scrape_udp.assert_called_once_with(
                ["hash1"], "example.com", 80, False, 2
            )
            assert result == {"hash1": {"seeders": 1}}

    def test_try_scrape_udp_with_port(self) -> None:
        """Test try_scrape with UDP protocol and custom port."""
        scraper = Scraper()
        scraper.infohashes = ["hash1"]

        with patch("scrapeer.scraper.scrape_udp") as mock_scrape_udp:
            mock_scrape_udp.return_value = {"hash1": {"seeders": 1}}

            _ = scraper.try_scrape("udp", "example.com", 1337, "", announce=False)

            mock_scrape_udp.assert_called_once_with(
                ["hash1"], "example.com", 1337, False, 2
            )

    def test_try_scrape_http(self) -> None:
        """Test try_scrape with HTTP protocol."""
        scraper = Scraper()
        scraper.infohashes = ["hash1"]

        with patch("scrapeer.scraper.scrape_http") as mock_scrape_http:
            mock_scrape_http.return_value = {"hash1": {"seeders": 1}}

            result = scraper.try_scrape(
                "http", "example.com", None, "/passkey", announce=False
            )

            mock_scrape_http.assert_called_once_with(
                ["hash1"],
                "http",
                "example.com",
                80,
                "/passkey",
                announce=False,
                timeout=2,
            )
            assert result == {"hash1": {"seeders": 1}}

    def test_try_scrape_https(self) -> None:
        """Test try_scrape with HTTPS protocol."""
        scraper = Scraper()
        scraper.infohashes = ["hash1"]

        with patch("scrapeer.scraper.scrape_http") as mock_scrape_http:
            mock_scrape_http.return_value = {"hash1": {"seeders": 1}}

            result = scraper.try_scrape(
                "https", "example.com", None, "/passkey", announce=True
            )

            mock_scrape_http.assert_called_once_with(
                ["hash1"],
                "https",
                "example.com",
                443,
                "/passkey",
                announce=True,
                timeout=2,
            )
            assert result == {"hash1": {"seeders": 1}}

    def test_try_scrape_unsupported_protocol(self) -> None:
        """Test try_scrape with unsupported protocol."""
        scraper = Scraper()
        scraper.infohashes = ["hash1"]

        result = scraper.try_scrape("ftp", "example.com", 21, "", announce=False)

        assert not result
        assert scraper.infohashes == ["hash1"]  # Should be restored on error
        assert "Unsupported protocol (ftp://example.com)." in scraper.errors

    def test_try_scrape_exception_handling(self) -> None:
        """Test try_scrape exception handling."""
        scraper = Scraper()
        scraper.infohashes = ["hash1"]

        with patch("scrapeer.scraper.scrape_udp") as mock_scrape_udp:
            mock_scrape_udp.side_effect = Exception("Connection failed")

            result = scraper.try_scrape("udp", "example.com", 80, "", announce=False)

            assert not result
            assert scraper.infohashes == ["hash1"]  # Should be restored on error
            assert "Connection failed" in scraper.errors

    def test_infohashes_backup_and_restore(self) -> None:
        """Test that infohashes are properly backed up and restored on error."""
        scraper = Scraper()
        scraper.infohashes = ["hash1", "hash2"]
        original_hashes = scraper.infohashes.copy()

        with patch("scrapeer.scraper.scrape_udp") as mock_scrape_udp:
            mock_scrape_udp.side_effect = Exception("Test error")

            _ = scraper.try_scrape("udp", "example.com", 80, "", announce=False)

            # Should restore original hashes on error
            assert scraper.infohashes == original_hashes

    def test_scrape_integration_flow(self) -> None:
        """Test complete scrape integration flow."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = [valid_hash]
            with patch("scrapeer.scraper.get_passkey") as mock_passkey:
                mock_passkey.return_value = ""
                with patch("scrapeer.scraper.scrape_udp") as mock_scrape_udp:
                    mock_scrape_udp.return_value = {
                        valid_hash: {
                            "seeders": 10,
                            "completed": 5,
                            "leechers": 3,
                        }
                    }

                    result = scraper.scrape(
                        hashes=[valid_hash],
                        trackers=["udp://tracker.example.com:8080/announce"],
                        timeout=5,
                        announce=True,
                    )

                    assert result == {
                        valid_hash: {
                            "seeders": 10,
                            "completed": 5,
                            "leechers": 3,
                        }
                    }
                    assert scraper.timeout == 5
                    mock_scrape_udp.assert_called_once_with(
                        [valid_hash], "tracker.example.com", 8080, True, 5
                    )

    def test_scrape_multiple_trackers_aggregation(self) -> None:
        """Test that results from multiple trackers are aggregated."""
        scraper = Scraper()
        valid_hash1 = "a1b2c3d4e5f6789012345678901234567890abcd"
        valid_hash2 = "b1c2d3e4f5a6789012345678901234567890efab"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = [valid_hash1, valid_hash2]
            with patch("scrapeer.scraper.get_passkey") as mock_passkey:
                mock_passkey.return_value = ""
                with patch("scrapeer.scraper.scrape_udp") as mock_scrape_udp:
                    # First tracker returns results for both hashes
                    mock_scrape_udp.return_value = {
                        valid_hash1: {"seeders": 10, "completed": 5, "leechers": 3},
                        valid_hash2: {"seeders": 20, "completed": 15, "leechers": 8},
                    }

                    result = scraper.scrape(
                        hashes=[valid_hash1, valid_hash2],
                        trackers=["udp://tracker1.com:8080", "udp://tracker2.com:8080"],
                    )

                    expected = {
                        valid_hash1: {"seeders": 10, "completed": 5, "leechers": 3},
                        valid_hash2: {"seeders": 20, "completed": 15, "leechers": 8},
                    }
                    assert result == expected
                    # Only first tracker should be called since all hashes are found
                    assert mock_scrape_udp.call_count == 1

    def test_scrape_no_infohashes_after_normalization(self) -> None:
        """Test scrape behavior when no valid infohashes remain after normalization."""
        scraper = Scraper()

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = []
            scraper.infohashes = []

            result = scraper.scrape(["invalid_hash"], ["udp://tracker.com"])

            # Should not attempt to scrape if no valid hashes
            assert not result

    def test_scrape_empty_infohashes_stops_iteration(self) -> None:
        """Test that empty infohashes stops the tracker iteration."""
        scraper = Scraper()
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcd"

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = [valid_hash]
            with patch.object(scraper, "try_scrape") as mock_try_scrape:
                # First call empties infohashes, second call shouldn't happen
                def side_effect(*args, **kwargs):
                    scraper.infohashes = []
                    return {valid_hash: {"seeders": 1}}

                mock_try_scrape.side_effect = side_effect

                _ = scraper.scrape(
                    [valid_hash], ["udp://tracker1.com", "udp://tracker2.com"]
                )

                # Should only call try_scrape once
                assert mock_try_scrape.call_count == 1

    def test_scraper_break_on_empty_infohashes(self) -> None:
        """Test scraper break statement when infohashes becomes empty after first tracker."""
        scraper = Scraper()

        # Set up a scenario where infohashes becomes empty after first tracker
        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["a1b2c3d4e5f6789012345678901234567890abcd"]

            with patch.object(scraper, "try_scrape") as mock_try_scrape:

                def side_effect(*args, **kwargs):
                    # First call empties the infohashes list
                    scraper.infohashes = []
                    return {"a1b2c3d4e5f6789012345678901234567890abcd": {"seeders": 1}}

                mock_try_scrape.side_effect = side_effect

                _ = scraper.scrape(
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    ["http://tracker1.com", "http://tracker2.com"],  # Two trackers
                )

                # Should only call try_scrape once before breaking
                assert mock_try_scrape.call_count == 1

    def test_validation_none_hashes(self) -> None:
        """Test validation error for None hashes."""
        scraper = Scraper()

        with pytest.raises(ValueError, match="Hashes cannot be None"):
            scraper.scrape(None, ["http://example.com"])  # type: ignore

    def test_validation_none_trackers(self) -> None:
        """Test validation error for None trackers."""
        scraper = Scraper()

        with pytest.raises(ValueError, match="Trackers cannot be None"):
            scraper.scrape(["a1b2c3d4e5f6789012345678901234567890abcd"], None)  # type: ignore

    def test_validation_invalid_announce_type(self) -> None:
        """Test validation error for invalid announce type."""
        scraper = Scraper()

        with pytest.raises(TypeError, match="Announce must be boolean"):
            scraper.scrape(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                ["http://example.com"],
                announce="true",  # type: ignore
            )

    def test_validation_invalid_max_trackers_type(self) -> None:
        """Test validation error for invalid max_trackers type."""
        scraper = Scraper()

        with pytest.raises(TypeError, match="Max_trackers must be integer or None"):
            scraper.scrape(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                ["http://example.com"],
                max_trackers="5",  # type: ignore
            )

    def test_validation_invalid_max_trackers_value(self) -> None:
        """Test validation error for invalid max_trackers value."""
        scraper = Scraper()

        with pytest.raises(ValueError, match="Max_trackers must be positive, got 0"):
            scraper.scrape(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                ["http://example.com"],
                max_trackers=0,
            )

    def test_validation_invalid_timeout_type(self) -> None:
        """Test validation error for invalid timeout type."""
        scraper = Scraper()

        with pytest.raises(TypeError, match="Timeout must be integer"):
            scraper.scrape(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                ["http://example.com"],
                timeout="5",  # type: ignore
            )

    def test_validation_invalid_timeout_value_low(self) -> None:
        """Test validation error for timeout too low."""
        scraper = Scraper()

        with pytest.raises(ValueError, match="Timeout must be positive, got 0"):
            scraper.scrape(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                ["http://example.com"],
                timeout=0,
            )

    def test_validation_invalid_timeout_value_high(self) -> None:
        """Test validation error for timeout too high."""
        scraper = Scraper()

        with pytest.raises(
            ValueError, match="Timeout too large, max 300 seconds, got 301"
        ):
            scraper.scrape(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                ["http://example.com"],
                timeout=301,
            )

    def test_scraper_break_on_max_trackers_reached(self) -> None:
        """Test scraper break statement when index >= max_iterations."""
        scraper = Scraper()

        with patch("scrapeer.scraper.normalize_infohashes") as mock_normalize:
            mock_normalize.return_value = ["a1b2c3d4e5f6789012345678901234567890abcd"]

            with patch.object(scraper, "try_scrape") as mock_try_scrape:
                mock_try_scrape.return_value = {}

                _ = scraper.scrape(
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    [
                        "http://tracker1.com",
                        "http://tracker2.com",
                        "http://tracker3.com",
                    ],
                    max_trackers=1,  # Limit to 1 tracker
                )

                # Should only call try_scrape once due to max_trackers limit
                assert mock_try_scrape.call_count == 1
