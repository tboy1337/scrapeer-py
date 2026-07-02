"""Tests for scrapeer.udp module."""

import socket
import struct
from unittest.mock import MagicMock, patch

import pytest

from scrapeer.udp import (
    UdpResponseSlice,
    UdpTrackerEndpoint,
    prepare_udp,
    scrape_udp,
    udp_announce,
    udp_connection_request,
    udp_connection_response,
    udp_create_connection,
    udp_scrape,
    udp_scrape_data,
    udp_scrape_request,
    udp_verify_announce,
)


class TestScrapeUdp:
    """Tests for scrape_udp function."""

    @patch("scrapeer.udp.prepare_udp")
    @patch("scrapeer.udp.udp_connection_request")
    @patch("scrapeer.udp.udp_connection_response")
    @patch("scrapeer.udp.udp_scrape")
    def test_udp_scrape_flow(
        self,
        mock_scrape: MagicMock,
        mock_conn_resp: MagicMock,
        mock_conn_req: MagicMock,
        mock_prepare: MagicMock,
    ) -> None:
        """Test UDP scraping flow."""
        mock_socket = MagicMock()
        mock_prepare.return_value = (mock_socket, "127.0.0.1")
        mock_conn_req.return_value = (12345, 0x41727101980)
        mock_conn_resp.return_value = 0x41727101980
        mock_scrape.return_value = {
            "hash1": {"seeders": 1, "completed": 2, "leechers": 3}
        }

        result = scrape_udp(["hash1"], "example.com", 80, False, 5)

        mock_prepare.assert_called_once_with("example.com", 80)
        mock_socket.settimeout.assert_called_once_with(5)
        mock_conn_req.assert_called_once_with(mock_socket)
        mock_conn_resp.assert_called_once_with(mock_socket, 12345, "example.com", 80)
        mock_scrape.assert_called_once_with(
            mock_socket,
            ["hash1"],
            0x41727101980,
            12345,
            UdpTrackerEndpoint(host="example.com", port=80),
        )
        mock_socket.close.assert_called_once()
        assert result == {"hash1": {"seeders": 1, "completed": 2, "leechers": 3}}

    @patch("scrapeer.udp.prepare_udp")
    @patch("scrapeer.udp.udp_connection_request")
    @patch("scrapeer.udp.udp_connection_response")
    @patch("scrapeer.udp.udp_announce")
    def test_udp_announce_flow(
        self,
        mock_announce: MagicMock,
        mock_conn_resp: MagicMock,
        mock_conn_req: MagicMock,
        mock_prepare: MagicMock,
    ) -> None:
        """Test UDP announcing flow."""
        mock_socket = MagicMock()
        mock_prepare.return_value = (mock_socket, "127.0.0.1")
        mock_conn_req.return_value = (12345, 0x41727101980)
        mock_conn_resp.return_value = 0x41727101980
        mock_announce.return_value = {
            "hash1": {"seeders": 1, "completed": 2, "leechers": 3}
        }

        result = scrape_udp(["hash1"], "example.com", 80, True, 5)

        mock_announce.assert_called_once_with(mock_socket, ["hash1"], 0x41727101980)
        mock_socket.close.assert_called_once()
        assert result == {"hash1": {"seeders": 1, "completed": 2, "leechers": 3}}

    @patch("scrapeer.udp.prepare_udp")
    def test_udp_error_cleanup(self, mock_prepare: MagicMock) -> None:
        """Test that socket is closed even when error occurs after prepare_udp."""
        mock_socket = MagicMock()
        mock_prepare.return_value = (mock_socket, "127.0.0.1")

        with patch("scrapeer.udp.udp_connection_request") as mock_req:
            mock_req.side_effect = Exception("Connection request failed")

            with pytest.raises(Exception, match="Connection request failed"):
                scrape_udp(
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    "example.com",
                    80,
                    False,
                    5,
                )

            mock_socket.close.assert_called_once()


class TestPrepareUdp:
    """Tests for prepare_udp function."""

    @patch("scrapeer.udp.udp_create_connection")
    @patch("socket.gethostbyname")
    def test_successful_prepare(
        self, mock_gethostbyname: MagicMock, mock_create: MagicMock
    ) -> None:
        """Test successful UDP preparation."""
        mock_socket = MagicMock()
        mock_create.return_value = mock_socket
        mock_gethostbyname.return_value = "192.168.1.1"

        result = prepare_udp("example.com", 80)

        mock_create.assert_called_once_with("example.com", 80)
        mock_gethostbyname.assert_called_once_with("example.com")
        assert result == (mock_socket, "192.168.1.1")

    @patch("scrapeer.udp.udp_create_connection")
    @patch("socket.gethostbyname")
    def test_dns_resolution_failure(
        self, mock_gethostbyname: MagicMock, mock_create: MagicMock
    ) -> None:
        """Test DNS resolution failure."""
        mock_socket = MagicMock()
        mock_create.return_value = mock_socket
        mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")

        with pytest.raises(Exception, match="Failed to resolve host 'example.com'"):
            prepare_udp("example.com", 80)


class TestUdpCreateConnection:
    """Tests for udp_create_connection function."""

    @patch("socket.socket")
    def test_successful_connection(self, mock_socket_class: MagicMock) -> None:
        """Test successful UDP socket creation."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        result = udp_create_connection("example.com", 80)

        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_socket.connect.assert_called_once_with(("example.com", 80))
        assert result == mock_socket

    @patch("socket.socket")
    def test_connection_failure(self, mock_socket_class: MagicMock) -> None:
        """Test UDP socket creation failure."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.error("Connection failed")

        with pytest.raises(
            Exception,
            match="Failed to create socket for 'example.com:80' - Connection failed",
        ):
            udp_create_connection("example.com", 80)


class TestUdpConnectionRequest:
    """Tests for udp_connection_request function."""

    @patch("random.randint")
    def test_successful_request(self, mock_randint: MagicMock) -> None:
        """Test successful connection request."""
        mock_socket = MagicMock()
        mock_randint.return_value = 12345

        result = udp_connection_request(mock_socket)

        expected_buffer = struct.pack(">QII", 0x41727101980, 0, 12345)
        mock_socket.send.assert_called_once_with(expected_buffer)
        assert result == (12345, 0x41727101980)

    def test_send_failure(self) -> None:
        """Test send failure."""
        mock_socket = MagicMock()
        mock_socket.send.side_effect = socket.error("Send failed")

        with pytest.raises(
            Exception, match="Failed to send connection request - Send failed"
        ):
            udp_connection_request(mock_socket)


class TestUdpConnectionResponse:
    """Tests for udp_connection_response function."""

    def test_successful_response(self) -> None:
        """Test successful connection response."""
        mock_socket = MagicMock()
        # Mock a valid connection response
        response_data = struct.pack(">IIQ", 0, 12345, 0x41727101999)
        mock_socket.recv.return_value = response_data

        result = udp_connection_response(mock_socket, 12345, "example.com", 80)

        mock_socket.recv.assert_called_once_with(16)
        assert result == 0x41727101999

    def test_receive_failure(self) -> None:
        """Test receive failure."""
        mock_socket = MagicMock()
        mock_socket.recv.side_effect = socket.error("Receive failed")

        with pytest.raises(
            Exception,
            match="Failed to receive connection response from 'example.com:80' - Receive failed",
        ):
            udp_connection_response(mock_socket, 12345, "example.com", 80)

    def test_invalid_response_length(self) -> None:
        """Test invalid response length."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"short"  # Less than 16 bytes

        with pytest.raises(
            Exception, match="Invalid response length from 'example.com:80'"
        ):
            udp_connection_response(mock_socket, 12345, "example.com", 80)

    def test_invalid_transaction_id(self) -> None:
        """Test invalid transaction ID in response."""
        mock_socket = MagicMock()
        response_data = struct.pack(
            ">IIQ", 0, 54321, 0x41727101999
        )  # Wrong transaction ID
        mock_socket.recv.return_value = response_data

        with pytest.raises(
            Exception, match="Invalid transaction ID from 'example.com:80'"
        ):
            udp_connection_response(mock_socket, 12345, "example.com", 80)

    def test_invalid_action(self) -> None:
        """Test invalid action in response."""
        mock_socket = MagicMock()
        response_data = struct.pack(
            ">IIQ", 1, 12345, 0x41727101999
        )  # Wrong action (should be 0)
        mock_socket.recv.return_value = response_data

        with pytest.raises(Exception, match="Invalid action from 'example.com:80'"):
            udp_connection_response(mock_socket, 12345, "example.com", 80)


class TestUdpScrape:
    """Tests for udp_scrape function."""

    @patch("scrapeer.udp.udp_scrape_request")
    @patch("scrapeer.udp.udp_scrape_data")
    def test_successful_scrape(
        self, mock_scrape_data: MagicMock, mock_scrape_request: MagicMock
    ) -> None:
        """Test successful UDP scrape."""
        mock_socket = MagicMock()
        mock_scrape_request.return_value = b"request_data"

        # Mock valid scrape response
        response_data = (
            struct.pack(">II", 2, 12345) + b"\x00" * 12
        )  # action=2, transaction_id, + 12 bytes data
        mock_socket.recv.return_value = response_data

        mock_scrape_data.return_value = {
            "hash1": {"seeders": 1, "completed": 2, "leechers": 3}
        }

        result = udp_scrape(
            mock_socket,
            ["a1b2c3d4e5f6789012345678901234567890abcd"],
            0x41727101999,
            12345,
            UdpTrackerEndpoint(host="example.com", port=80),
        )

        mock_scrape_request.assert_called_once_with(
            mock_socket,
            ["a1b2c3d4e5f6789012345678901234567890abcd"],
            0x41727101999,
            12345,
        )
        mock_socket.send.assert_called_once_with(b"request_data")
        mock_socket.recv.assert_called_once_with(8 + (12 * 1))  # 8 header + 12 per hash
        assert result == {"hash1": {"seeders": 1, "completed": 2, "leechers": 3}}

    def test_invalid_response_length(self) -> None:
        """Test invalid response length."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"short"  # Less than 8 bytes

        with patch("scrapeer.udp.udp_scrape_request") as mock_req:
            mock_req.return_value = b"request_data"

            with pytest.raises(
                Exception, match="Invalid scrape response from 'example.com:80'"
            ):
                udp_scrape(
                    mock_socket,
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    0x41727101999,
                    12345,
                    UdpTrackerEndpoint(host="example.com", port=80),
                )

    def test_invalid_transaction_id(self) -> None:
        """Test invalid transaction ID."""
        mock_socket = MagicMock()
        response_data = (
            struct.pack(">II", 2, 54321) + b"\x00" * 12
        )  # Wrong transaction ID
        mock_socket.recv.return_value = response_data

        with patch("scrapeer.udp.udp_scrape_request") as mock_req:
            mock_req.return_value = b"request_data"

            with pytest.raises(
                Exception, match="Invalid transaction ID from 'example.com:80'"
            ):
                udp_scrape(
                    mock_socket,
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    0x41727101999,
                    12345,
                    UdpTrackerEndpoint(host="example.com", port=80),
                )

    def test_error_response(self) -> None:
        """Test error response from tracker."""
        mock_socket = MagicMock()
        response_data = struct.pack(">II", 3, 12345) + struct.pack(
            ">I", 500
        )  # action=3 (error), error code
        mock_socket.recv.return_value = response_data

        with patch("scrapeer.udp.udp_scrape_request") as mock_req:
            mock_req.return_value = b"request_data"

            with pytest.raises(
                Exception, match="Tracker error, code: 12345 from 'example.com:80'"
            ):
                udp_scrape(
                    mock_socket,
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    0x41727101999,
                    12345,
                    UdpTrackerEndpoint(host="example.com", port=80),
                )

    def test_socket_error(self) -> None:
        """Test socket error during scrape."""
        mock_socket = MagicMock()
        mock_socket.send.side_effect = socket.error("Send failed")

        with patch("scrapeer.udp.udp_scrape_request") as mock_req:
            mock_req.return_value = b"request_data"

            with pytest.raises(
                Exception, match="Socket error from 'example.com:80' - Send failed"
            ):
                udp_scrape(
                    mock_socket,
                    ["a1b2c3d4e5f6789012345678901234567890abcd"],
                    0x41727101999,
                    12345,
                    UdpTrackerEndpoint(host="example.com", port=80),
                )


class TestUdpScrapeRequest:
    """Tests for udp_scrape_request function."""

    @patch("scrapeer.udp.collect_info_hash")
    def test_request_creation(self, mock_collect: MagicMock) -> None:
        """Test scrape request creation."""
        mock_collect.side_effect = [b"\x12" * 20, b"\x34" * 20]  # Mock 20-byte hashes

        result = udp_scrape_request(
            MagicMock(),
            [
                "a1b2c3d4e5f6789012345678901234567890abcd",
                "b1c2d3e4f5678901234567890123456789abcdef",
            ],
            0x41727101999,
            12345,
        )

        expected_header = struct.pack(">QII", 0x41727101999, 2, 12345)
        expected_hashes = b"\x12" * 20 + b"\x34" * 20
        expected = expected_header + expected_hashes

        assert result == expected
        assert mock_collect.call_count == 2


class TestUdpAnnounce:
    """Tests for udp_announce function."""

    def test_multiple_hashes_error(self) -> None:
        """Test that multiple hashes raises error."""
        mock_socket = MagicMock()

        with pytest.raises(Exception, match="Too many hashes for UDP announce \\(2\\)"):
            udp_announce(
                mock_socket,
                [
                    "a1b2c3d4e5f6789012345678901234567890abcd",
                    "b1c2d3e4f5678901234567890123456789abcdef",
                ],
                0x41727101999,
            )

    @patch("scrapeer.udp.collect_info_hash")
    @patch("scrapeer.udp.random_peer_id")
    @patch("scrapeer.udp.udp_verify_announce")
    @patch("random.randint")
    def test_successful_announce(
        self,
        mock_randint: MagicMock,
        mock_verify: MagicMock,
        mock_peer_id: MagicMock,
        mock_collect: MagicMock,
    ) -> None:
        """Test successful UDP announce."""
        mock_socket = MagicMock()
        mock_randint.return_value = 12345
        mock_collect.return_value = b"\x12" * 20
        mock_peer_id.return_value = b"-PY0001-123456789012"
        mock_verify.return_value = (10, 5, 15)  # seeders, leechers, completed

        result = udp_announce(
            mock_socket, ["a1b2c3d4e5f6789012345678901234567890abcd"], 0x41727101999
        )

        expected_result = {
            "a1b2c3d4e5f6789012345678901234567890abcd": {
                "seeders": 10,
                "leechers": 5,
                "completed": 15,
            }
        }

        assert result == expected_result
        mock_socket.send.assert_called_once()
        mock_verify.assert_called_once_with(mock_socket, 12345)

    def test_socket_error(self) -> None:
        """Test socket error during announce."""
        mock_socket = MagicMock()
        mock_socket.send.side_effect = socket.error("Send failed")

        with pytest.raises(
            Exception, match="Failed to send announce request - Send failed"
        ):
            udp_announce(
                mock_socket, ["a1b2c3d4e5f6789012345678901234567890abcd"], 0x41727101999
            )


class TestUdpVerifyAnnounce:
    """Tests for udp_verify_announce function."""

    def test_successful_verification(self) -> None:
        """Test successful announce verification."""
        mock_socket = MagicMock()
        response_data = struct.pack(
            ">IIIII", 1, 12345, 1800, 5, 10
        )  # action, txn_id, interval, leechers, seeders
        mock_socket.recv.return_value = response_data

        result = udp_verify_announce(mock_socket, 12345)

        assert result == (10, 5, 0)  # seeders, leechers, completed

    def test_receive_error(self) -> None:
        """Test receive error."""
        mock_socket = MagicMock()
        mock_socket.recv.side_effect = socket.error("Receive failed")

        with pytest.raises(
            Exception, match="Failed to receive announce response - Receive failed"
        ):
            udp_verify_announce(mock_socket, 12345)

    def test_invalid_response_length(self) -> None:
        """Test invalid response length."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"short"  # Less than 20 bytes

        with pytest.raises(Exception, match="Invalid announce response length \\(5\\)"):
            udp_verify_announce(mock_socket, 12345)

    def test_invalid_transaction_id(self) -> None:
        """Test invalid transaction ID."""
        mock_socket = MagicMock()
        response_data = struct.pack(
            ">IIIII", 1, 54321, 1800, 5, 10
        )  # Wrong transaction ID
        mock_socket.recv.return_value = response_data

        with pytest.raises(
            Exception, match="Invalid transaction ID \\(54321 != 12345\\)"
        ):
            udp_verify_announce(mock_socket, 12345)

    def test_invalid_action(self) -> None:
        """Test invalid action."""
        mock_socket = MagicMock()
        response_data = struct.pack(
            ">IIIII", 2, 12345, 1800, 5, 10
        )  # Wrong action (should be 1)
        mock_socket.recv.return_value = response_data

        with pytest.raises(Exception, match="Invalid action code \\(2\\)"):
            udp_verify_announce(mock_socket, 12345)


class TestUdpScrapeData:
    """Tests for udp_scrape_data function."""

    def test_successful_parsing(self) -> None:
        """Test successful scrape data parsing."""
        # Create response data: header + 2 sets of scrape data (12 bytes each)
        header = struct.pack(">II", 2, 12345)
        scrape_data1 = struct.pack(">III", 10, 5, 2)  # seeders, completed, leechers
        scrape_data2 = struct.pack(">III", 20, 15, 8)
        response = header + scrape_data1 + scrape_data2

        hashes = ["hash1", "hash2"]
        keys = ["hash1", "hash2"]

        result = udp_scrape_data(
            response,
            hashes,
            "example.com",
            keys,
            UdpResponseSlice(start=8, end=len(response), offset=12),
        )

        expected = {
            "hash1": {"seeders": 10, "completed": 5, "leechers": 2},
            "hash2": {"seeders": 20, "completed": 15, "leechers": 8},
        }

        assert result == expected

    def test_insufficient_data(self) -> None:
        """Test insufficient data for all hashes."""
        response = (
            struct.pack(">II", 2, 12345) + b"\x00" * 6
        )  # Only 6 bytes instead of 12
        hashes = ["hash1"]
        keys = ["hash1"]

        with pytest.raises(
            Exception, match="Invalid scrape response from 'example.com'"
        ):
            udp_scrape_data(
                response,
                hashes,
                "example.com",
                keys,
                UdpResponseSlice(start=8, end=len(response), offset=12),
            )

    def test_partial_data(self) -> None:
        """Test partial data scenario."""
        header = struct.pack(">II", 2, 12345)
        scrape_data = struct.pack(">III", 10, 5, 2)  # Only one complete set
        response = header + scrape_data + b"\x00" * 6  # Incomplete second set

        hashes = ["hash1", "hash2"]
        keys = ["hash1", "hash2"]

        with pytest.raises(
            Exception, match="Invalid scrape response from 'example.com'"
        ):
            udp_scrape_data(
                response,
                hashes,
                "example.com",
                keys,
                UdpResponseSlice(start=8, end=len(response), offset=12),
            )

    def test_insufficient_data_for_single_hash(self) -> None:
        """Test insufficient data for a single hash at specific position."""
        header = struct.pack(">II", 2, 12345)
        scrape_data = struct.pack(">III", 10, 5, 2)  # Complete first hash
        response = header + scrape_data + b"\x00" * 8  # Incomplete data for second hash

        hashes = ["hash1", "hash2"]
        keys = ["hash1", "hash2"]

        with pytest.raises(
            Exception, match="Invalid scrape response from 'example.com'"
        ):
            udp_scrape_data(
                response,
                hashes,
                "example.com",
                keys,
                UdpResponseSlice(start=8, end=len(response), offset=12),
            )

    def test_udp_scrape_data_insufficient_response(self) -> None:
        """Test UDP scrape data error on insufficient response data."""
        # Create response header but insufficient data for the hash
        header = struct.pack(">II", 2, 12345)  # action=2, transaction_id
        insufficient_data = b"\x00" * 6  # Only 6 bytes instead of required 12
        response = header + insufficient_data

        hashes = ["a1b2c3d4e5f6789012345678901234567890abcd"]
        keys = ["a1b2c3d4e5f6789012345678901234567890abcd"]

        with pytest.raises(
            Exception, match="Invalid scrape response from 'example.com'"
        ):
            udp_scrape_data(
                response,
                hashes,
                "example.com",
                keys,
                UdpResponseSlice(start=8, end=len(response), offset=12),
            )


class TestScrapeUdpValidation:
    """Tests for scrape_udp validation."""

    def test_empty_infohashes(self) -> None:
        """Test with empty infohashes list."""
        with pytest.raises(ValueError, match="Infohashes list cannot be empty"):
            scrape_udp([], "example.com", 80, False, 5)

    def test_udp_scrape_data_invalid_response(self) -> None:
        """Test UDP scrape data with completely invalid response."""
        response = b"short"  # Too short response
        hashes = ["a1b2c3d4e5f6789012345678901234567890abcd"]
        keys = ["a1b2c3d4e5f6789012345678901234567890abcd"]

        with pytest.raises(
            ValueError, match="Invalid scrape response from 'example.com'"
        ):
            udp_scrape_data(
                response,
                hashes,
                "example.com",
                keys,
                UdpResponseSlice(start=0, end=len(response), offset=12),
            )
