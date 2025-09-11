"""Tests for scrapeer.http module."""

import socket
import urllib.error
import urllib.request
from unittest.mock import patch, MagicMock

import pytest

from scrapeer.http import (
    scrape_http,
    http_query,
    http_request,
    http_announce,
    http_data,
    get_information,
    validate_network_params,
)


class TestScrapeHttp:
    """Tests for scrape_http function."""

    @patch("scrapeer.http.http_announce")
    def test_scrape_http_announce(self, mock_announce: MagicMock) -> None:
        """Test HTTP scraping with announce=True."""
        mock_announce.return_value = b"fake_response"

        with patch("scrapeer.http.http_data") as mock_http_data:
            mock_http_data.return_value = {
                "hash1": {"seeders": 1, "completed": 2, "leechers": 3}
            }

            result = scrape_http(
                ["hash1"], "http", "example.com", 80, "/passkey", announce=True, timeout=5
            )

            mock_announce.assert_called_once_with(
                ["hash1"], "http", "example.com", 80, "/passkey", timeout=5
            )
            mock_http_data.assert_called_once_with(
                b"fake_response", ["hash1"], "example.com"
            )
            assert result == {"hash1": {"seeders": 1, "completed": 2, "leechers": 3}}

    @patch("scrapeer.http.http_request")
    @patch("scrapeer.http.http_query")
    def test_scrape_http_scrape(
        self, mock_query: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test HTTP scraping with announce=False."""
        mock_query.return_value = "http://example.com/scrape?info_hash=test"
        mock_request.return_value = b"fake_response"

        with patch("scrapeer.http.http_data") as mock_http_data:
            mock_http_data.return_value = {
                "hash1": {"seeders": 1, "completed": 2, "leechers": 3}
            }

            result = scrape_http(
                ["hash1"], "http", "example.com", 80, "/passkey", announce=False, timeout=5
            )

            mock_query.assert_called_once_with(
                ["hash1"], "http", "example.com", 80, "/passkey"
            )
            mock_request.assert_called_once_with(
                "http://example.com/scrape?info_hash=test", "example.com", 80, 5
            )
            mock_http_data.assert_called_once_with(
                b"fake_response", ["hash1"], "example.com"
            )
            assert result == {"hash1": {"seeders": 1, "completed": 2, "leechers": 3}}

    @patch("scrapeer.http.http_request")
    @patch("scrapeer.http.http_query")
    def test_scrape_http_exception_handling(
        self, mock_query: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test HTTP scraping exception handling."""
        mock_query.return_value = "http://example.com/scrape?info_hash=test"
        mock_request.return_value = b"fake_response"

        with patch("scrapeer.http.http_data") as mock_http_data:
            mock_http_data.side_effect = Exception("Data parsing failed")

            with pytest.raises(Exception, match="Data parsing failed"):
                scrape_http(
                    ["hash1"], "http", "example.com", 80, "/passkey", announce=False, timeout=5
                )


class TestHttpQuery:
    """Tests for http_query function."""

    def test_single_hash(self) -> None:
        """Test query building with single hash."""
        result = http_query(
            ["a1b2c3d4e5f6789012345678901234567890abcd"],
            "http",
            "example.com",
            80,
            "/passkey",
        )
        expected = (
            "http://example.com:80/scrape/passkey?info_hash="
            "%A1%B2%C3%D4%E5%F6x%90%124Vx%90%124Vx%90%AB%CD"
        )
        assert result == expected

    def test_multiple_hashes(self) -> None:
        """Test query building with multiple hashes."""
        hashes = [
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "b1c2d3e4f5678901234567890123456789abcdef",
        ]
        result = http_query(hashes, "https", "tracker.com", 443, "/key123")

        assert result.startswith("https://tracker.com:443/scrape/key123?info_hash=")
        assert "&info_hash=" in result

    def test_no_passkey(self) -> None:
        """Test query building without passkey."""
        result = http_query(
            ["a1b2c3d4e5f6789012345678901234567890abcd"],
            "http",
            "example.com",
            80,
            ""
        )
        expected = (
            "http://example.com:80/scrape?info_hash="
            "%A1%B2%C3%D4%E5%F6x%90%124Vx%90%124Vx%90%AB%CD"
        )
        assert result == expected

    def test_empty_hash_list(self) -> None:
        """Test with empty hash list."""
        result = http_query([], "http", "example.com", 80, "")
        assert result == "http://example.com:80/scrape"


class TestHttpRequest:
    """Tests for http_request function."""

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_successful_request(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test successful HTTP request."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"response_data"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        result = http_request("http://example.com/scrape", "example.com", 80, 5)

        mock_timeout.assert_called_once_with(5)
        mock_urlopen.assert_called_once()
        assert result == b"response_data"

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_request_with_user_agent(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test that request includes User-Agent header."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"response_data"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        http_request("http://example.com/scrape", "example.com", 80, 5)

        # Check that urlopen was called with a Request object that has User-Agent
        args, _ = mock_urlopen.call_args
        request_obj = args[0]
        assert hasattr(request_obj, "headers")
        assert request_obj.headers.get("User-agent") == "Scrapeer-py/1.0.0"

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_connection_error(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test connection error handling."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")

        with pytest.raises(
            Exception, match="Connection error: example.com:80 - .*Connection failed.*"
        ):
            http_request("http://example.com/scrape", "example.com", 80, 5)

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_timeout_error(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test timeout error handling."""
        mock_urlopen.side_effect = socket.timeout("Timeout")

        with pytest.raises(
            Exception, match="Connection error: example.com:80 - Timeout"
        ):
            http_request("http://example.com/scrape", "example.com", 80, 5)


class TestHttpAnnounce:
    """Tests for http_announce function."""

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_successful_announce(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test successful HTTP announce."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"announce_response"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        result = http_announce(
            ["a1b2c3d4e5f6789012345678901234567890abcd"],
            "http",
            "example.com",
            80,
            "/passkey",
            timeout=5,
        )

        mock_timeout.assert_called_once_with(5)
        assert result == b"announce_response"

    def test_multiple_hashes_error(self) -> None:
        """Test that multiple hashes raises an error."""
        hashes = ["hash1", "hash2"]

        with pytest.raises(
            Exception, match="Too many hashes for HTTP announce \\(2\\)"
        ):
            http_announce(hashes, "http", "example.com", 80, "/passkey", timeout=5)

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_announce_with_params(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test announce request includes required parameters."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"announce_response"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        http_announce(
            ["a1b2c3d4e5f6789012345678901234567890abcd"],
            "https",
            "tracker.com",
            443,
            "/key",
            timeout=10,
        )

        # Verify the request was made with correct parameters
        args, _ = mock_urlopen.call_args
        request_obj = args[0]
        url = request_obj.full_url

        assert url.startswith("https://tracker.com:443/announce/key?")
        assert "info_hash=" in url
        assert "peer_id=test1234567891234567" in url
        assert "port=6889" in url
        assert "uploaded=0" in url
        assert "downloaded=0" in url
        assert "left=0" in url
        assert "compact=1" in url

    @patch("socket.setdefaulttimeout")
    @patch("urllib.request.urlopen")
    def test_announce_connection_error(
        self, mock_urlopen: MagicMock, mock_timeout: MagicMock
    ) -> None:
        """Test announce connection error handling."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")

        with pytest.raises(
            Exception, match="Connection error: example.com:80 - .*Connection failed.*"
        ):
            http_announce(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                "http",
                "example.com",
                80,
                "/passkey",
                timeout=5,
            )


class TestHttpData:
    """Tests for http_data function."""

    def test_parse_complete_response(self) -> None:
        """Test parsing response with complete data."""
        # Test with response that contains direct pattern match
        response_str = (
            "746573745f686173685f686572655f31365f6279:"
            "d8:completei5e10:downloadedi10e10:incompletei2ee"
        )
        response = response_str.encode()
        hashes = ["746573745f686173685f686572655f31365f6279"]

        result = http_data(response, hashes, "example.com")

        expected = {
            "746573745f686173685f686572655f31365f6279": {
                "seeders": 5,
                "completed": 10,
                "leechers": 2,
            }
        }
        assert result == expected

    def test_parse_simple_response(self) -> None:
        """Test parsing response with only seeders and leechers."""
        response_str = (
            "some data 746573745f686173685f686572655f31365f6279:"
            "d8:completei3e10:incompletei7ee more data"
        )
        response = response_str.encode()
        hashes = ["746573745f686173685f686572655f31365f6279"]

        result = http_data(response, hashes, "example.com")

        expected = {
            "746573745f686173685f686572655f31365f6279": {
                "seeders": 3,
                "completed": 0,
                "leechers": 7,
            }
        }
        assert result == expected

    @patch("scrapeer.http.get_information")
    def test_fallback_parsing_called(self, mock_get_info: MagicMock) -> None:
        """Test that fallback parsing calls get_information when other methods fail."""
        # Return None to trigger the final error path
        mock_get_info.return_value = None

        response = b"some response without proper patterns"
        hashes = ["746573745f686173685f686572655f31365f6279"]

        with pytest.raises(
            Exception, match="Invalid scrape response from 'example.com'"
        ):
            http_data(response, hashes, "example.com")

        # Verify get_information was called as part of the fallback
        mock_get_info.assert_called_once_with(
            "some response without proper patterns", "d5:filesd", "ee"
        )

    @patch("scrapeer.http.get_information")
    def test_hash_not_found_error(self, mock_get_info: MagicMock) -> None:
        """Test error when hash is not found in response."""
        mock_get_info.return_value = "20:different_hash_hered8:completei1ee"

        response = b"some bencode response d5:filesd..ee"
        hashes = ["746573745f686173685f686572655f31365f6279"]

        with pytest.raises(
            Exception, match="Failed to parse torrent data from 'example.com'"
        ):
            http_data(response, hashes, "example.com")

    @patch("scrapeer.http.get_information")
    def test_invalid_response_error(self, mock_get_info: MagicMock) -> None:
        """Test error when response is invalid."""
        mock_get_info.return_value = None

        response = b"invalid response"
        hashes = ["746573745f686173685f686572655f31365f6279"]

        with pytest.raises(
            Exception, match="Invalid scrape response from 'example.com'"
        ):
            http_data(response, hashes, "example.com")



class TestGetInformation:
    """Tests for get_information function."""

    def test_extract_information(self) -> None:
        """Test extracting information between start and end markers."""
        data = "some text d5:filesd important data ee more text"
        result = get_information(data, "d5:filesd", "ee")

        assert result == " important data "

    def test_start_not_found(self) -> None:
        """Test when start marker is not found."""
        data = "some text without markers"
        result = get_information(data, "missing_start", "end")

        assert result is None

    def test_end_not_found(self) -> None:
        """Test when end marker is not found."""
        data = "some text d5:filesd important data without end"
        result = get_information(data, "d5:filesd", "missing_end")

        assert result is None

    def test_empty_data(self) -> None:
        """Test with empty data."""
        result = get_information("", "start", "end")

        assert result is None

    def test_multiple_occurrences(self) -> None:
        """Test with multiple occurrences of markers (should return first)."""
        data = "start first_data end some text start second_data end"
        result = get_information(data, "start", "end")

        assert result == " first_data "

    def test_adjacent_markers(self) -> None:
        """Test with adjacent start/end markers."""
        data = "prefix startend suffix"
        result = get_information(data, "start", "end")

        assert result == ""


class TestValidateNetworkParams:
    """Tests for validate_network_params function."""

    def test_valid_params(self) -> None:
        """Test with valid parameters."""
        # Should not raise any exception
        validate_network_params("example.com", 80, 5)
        validate_network_params("192.168.1.1", 65535, 300)

    def test_empty_host(self) -> None:
        """Test with empty host."""
        with pytest.raises(ValueError, match="Host cannot be empty"):
            validate_network_params("", 80, 5)

    def test_whitespace_only_host(self) -> None:
        """Test with whitespace-only host."""
        with pytest.raises(ValueError, match="Host cannot be empty"):
            validate_network_params("   ", 80, 5)

    def test_invalid_port_type(self) -> None:
        """Test with invalid port type."""
        with pytest.raises(ValueError, match="Invalid port"):
            validate_network_params("example.com", "80", 5)  # type: ignore

    def test_port_too_low(self) -> None:
        """Test with port number too low."""
        with pytest.raises(ValueError, match="Invalid port 0, must be 1-65535"):
            validate_network_params("example.com", 0, 5)

    def test_port_too_high(self) -> None:
        """Test with port number too high."""
        with pytest.raises(ValueError, match="Invalid port 65536, must be 1-65535"):
            validate_network_params("example.com", 65536, 5)

    def test_invalid_timeout_type(self) -> None:
        """Test with invalid timeout type."""
        with pytest.raises(ValueError, match="Invalid timeout"):
            validate_network_params("example.com", 80, "5")  # type: ignore

    def test_timeout_too_low(self) -> None:
        """Test with timeout too low."""
        with pytest.raises(ValueError, match="Invalid timeout 0, must be positive integer"):
            validate_network_params("example.com", 80, 0)


class TestScrapeHttpValidation:
    """Tests for scrape_http validation."""

    def test_empty_infohashes(self) -> None:
        """Test with empty infohashes list."""
        with pytest.raises(ValueError, match="Infohashes list cannot be empty"):
            scrape_http([], "http", "example.com", 80, "", announce=False)

    def test_invalid_protocol(self) -> None:
        """Test with invalid protocol."""
        with pytest.raises(ValueError, match="Invalid protocol 'ftp', must be 'http' or 'https'"):
            scrape_http(
                ["a1b2c3d4e5f6789012345678901234567890abcd"],
                "ftp",
                "example.com",
                80,
                "",
                announce=False
            )


class TestHttpDataEdgeCases:
    """Tests for edge cases in http_data function."""

    def test_unicode_decode_error_fallback(self) -> None:
        """Test fallback to latin-1 when utf-8 decoding fails."""
        # Create bytes that will cause UnicodeDecodeError in utf-8
        response = b'\xff\xfe' + b"d8:completei1e10:incompletei2e"
        hashes = ["746573745f686173685f686572655f31365f6279"]
        # This should raise an exception since the malformed data won't match patterns
        with pytest.raises(ValueError, match="Invalid scrape response from 'example.com'"):
            http_data(response, hashes, "example.com")

    def test_hex_decode_fallback(self) -> None:
        """Test fallback when hex decoding fails in get_information path."""
        # Create a response that will trigger the get_information fallback
        response = b"d5:filesd20:invalid_hex_stringd8:completei5e10:incompletei3eee"
        hashes = ["invalid_hex_string"]  # This will cause ValueError in hex decoding

        result = http_data(response, hashes, "example.com")

        # Should handle the error gracefully
        assert isinstance(result, dict)
