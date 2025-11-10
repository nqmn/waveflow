"""
ARQ (Automatic Repeat Request) handler for reliable transmission
Implements selective repeat ARQ with CRC-based error detection
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ARQConfig:
    """ARQ configuration"""
    max_retransmissions: int = 3
    use_crc: bool = True
    crc_polynomial: int = 0xEDB88320  # CRC-32
    ack_timeout_symbols: int = 100


class CRCHandler:
    """CRC error detection for packet integrity"""

    @staticmethod
    def compute_crc32(data: np.ndarray) -> np.uint32:
        """Compute CRC-32 checksum"""
        crc = 0xFFFFFFFF
        poly = 0xEDB88320

        for byte_val in data:
            crc ^= int(byte_val)
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ poly
                else:
                    crc >>= 1

        return np.uint32(crc ^ 0xFFFFFFFF)

    @staticmethod
    def add_crc(data: np.ndarray) -> np.ndarray:
        """Add CRC to data"""
        crc = CRCHandler.compute_crc32(data)
        crc_bytes = np.array([
            (crc >> 0) & 0xFF,
            (crc >> 8) & 0xFF,
            (crc >> 16) & 0xFF,
            (crc >> 24) & 0xFF
        ], dtype=np.uint8)
        return np.concatenate([data, crc_bytes])

    @staticmethod
    def verify_crc(data: np.ndarray) -> Tuple[bool, np.ndarray]:
        """Verify CRC and extract original data"""
        if len(data) < 4:
            return False, data

        payload = data[:-4]
        crc_received = (
            (int(data[-4]) << 0) |
            (int(data[-3]) << 8) |
            (int(data[-2]) << 16) |
            (int(data[-1]) << 24)
        )
        crc_computed = CRCHandler.compute_crc32(payload)
        is_valid = (crc_received == crc_computed)

        return is_valid, payload


class ARQTransmitter:
    """Transmitter-side ARQ logic"""

    def __init__(self, config: ARQConfig = None):
        """
        Args:
            config: ARQ configuration
        """
        self.config = config or ARQConfig()
        self.packet_buffer = {}  # sequence_num -> packet_data
        self.next_seq_num = 0
        self.transmission_log = []
        self.max_log_size = 100

    def prepare_packet(self, data: np.ndarray, sequence_num: Optional[int] = None) -> Tuple[np.ndarray, int]:
        """
        Prepare packet with sequence number and optional CRC

        Args:
            data: Payload data
            sequence_num: Sequence number (auto-increment if None)

        Returns:
            (packet_with_header, sequence_num)
        """
        if sequence_num is None:
            sequence_num = self.next_seq_num
            self.next_seq_num += 1

        # Build packet: [SEQ_NUM(1 byte)] [LENGTH(2 bytes)] [PAYLOAD] [CRC(4 bytes)]
        seq_bytes = np.array([sequence_num & 0xFF], dtype=np.uint8)
        len_bytes = np.array([
            (len(data) >> 0) & 0xFF,
            (len(data) >> 8) & 0xFF
        ], dtype=np.uint8)

        packet = np.concatenate([seq_bytes, len_bytes, data])

        if self.config.use_crc:
            packet = CRCHandler.add_crc(packet)

        # Buffer packet for potential retransmission
        self.packet_buffer[sequence_num] = packet.copy()

        return packet, sequence_num

    def mark_transmitted(self, seq_num: int, attempt: int = 1) -> Dict:
        """Record transmission attempt"""
        entry = {
            'seq_num': seq_num,
            'attempt': attempt,
            'transmitted': True
        }
        self.transmission_log.append(entry)

        if len(self.transmission_log) > self.max_log_size:
            self.transmission_log.pop(0)

        return entry

    def get_retransmission_packet(self, seq_num: int) -> Optional[np.ndarray]:
        """Retrieve buffered packet for retransmission"""
        return self.packet_buffer.get(seq_num, None)

    def discard_packet(self, seq_num: int):
        """Discard packet from buffer (after successful ACK)"""
        if seq_num in self.packet_buffer:
            del self.packet_buffer[seq_num]


class ARQReceiver:
    """Receiver-side ARQ logic"""

    def __init__(self, config: ARQConfig = None):
        """
        Args:
            config: ARQ configuration
        """
        self.config = config or ARQConfig()
        self.received_packets = {}  # seq_num -> packet_data
        self.last_ack_num = -1
        self.receive_log = []
        self.max_log_size = 100

    def receive_packet(self, rx_packet: np.ndarray) -> Tuple[bool, Optional[np.ndarray], int]:
        """
        Process received packet

        Args:
            rx_packet: Received packet with header

        Returns:
            (is_valid, payload, sequence_num)
        """
        # Extract header
        if len(rx_packet) < 3:
            return False, None, -1

        seq_num = int(rx_packet[0])
        payload_len = (int(rx_packet[1]) & 0xFF) | ((int(rx_packet[2]) & 0xFF) << 8)

        # Verify CRC if enabled
        is_valid = True
        if self.config.use_crc:
            is_valid, extracted = CRCHandler.verify_crc(rx_packet)
            payload = extracted[3:3+payload_len] if is_valid else None
        else:
            payload = rx_packet[3:3+payload_len]

        # Record reception
        entry = {
            'seq_num': seq_num,
            'valid': is_valid,
            'payload_len': payload_len,
            'received': True
        }
        self.receive_log.append(entry)

        if len(self.receive_log) > self.max_log_size:
            self.receive_log.pop(0)

        if is_valid:
            self.received_packets[seq_num] = payload
            self.last_ack_num = seq_num

        return is_valid, payload, seq_num

    def send_ack(self, seq_num: int) -> np.ndarray:
        """
        Generate ACK packet

        Args:
            seq_num: Sequence number to acknowledge

        Returns:
            ACK packet as bits
        """
        # Simple ACK: [ACK_FLAG(1 bit)] [SEQ_NUM(8 bits)]
        ack_byte = np.uint8(0x80 | (seq_num & 0x7F))  # Set MSB for ACK flag
        return np.array([ack_byte], dtype=np.uint8)

    def is_duplicate(self, seq_num: int) -> bool:
        """Check if packet is duplicate"""
        return seq_num in self.received_packets


class ARQSystem:
    """Complete ARQ system for link"""

    def __init__(self, config: ARQConfig = None):
        """
        Args:
            config: ARQ configuration
        """
        self.config = config or ARQConfig()
        self.transmitter = ARQTransmitter(config)
        self.receiver = ARQReceiver(config)
        self.statistics = {
            'packets_transmitted': 0,
            'packets_retransmitted': 0,
            'packets_received': 0,
            'packets_corrupted': 0,
            'total_retransmissions': 0
        }

    def transmit(self, data: np.ndarray) -> Dict:
        """
        Transmit data with ARQ

        Args:
            data: Payload data

        Returns:
            Transmission info dict
        """
        packet, seq_num = self.transmitter.prepare_packet(data)
        self.transmitter.mark_transmitted(seq_num, attempt=1)
        self.statistics['packets_transmitted'] += 1

        return {
            'seq_num': seq_num,
            'packet': packet,
            'attempt': 1,
            'payload_bits': len(data),
            'total_bits': len(packet) * 8
        }

    def retransmit(self, seq_num: int) -> Optional[Dict]:
        """
        Retransmit packet

        Args:
            seq_num: Sequence number to retransmit

        Returns:
            Retransmission info or None if max retries exceeded
        """
        # Check attempt count from log
        attempts = sum(1 for log in self.transmitter.transmission_log if log['seq_num'] == seq_num)

        if attempts >= self.config.max_retransmissions:
            return None  # Max retries exceeded

        packet = self.transmitter.get_retransmission_packet(seq_num)
        if packet is None:
            return None

        self.transmitter.mark_transmitted(seq_num, attempt=attempts + 1)
        self.statistics['packets_retransmitted'] += 1
        self.statistics['total_retransmissions'] += 1

        return {
            'seq_num': seq_num,
            'packet': packet,
            'attempt': attempts + 1,
            'retry_number': attempts
        }

    def receive_and_decode(self, rx_packet: np.ndarray) -> Tuple[bool, Optional[np.ndarray], int]:
        """
        Receive and decode packet

        Args:
            rx_packet: Received packet

        Returns:
            (is_valid, payload, seq_num)
        """
        is_valid, payload, seq_num = self.receiver.receive_packet(rx_packet)

        if is_valid:
            self.statistics['packets_received'] += 1
        else:
            self.statistics['packets_corrupted'] += 1

        return is_valid, payload, seq_num

    def get_statistics(self) -> Dict:
        """Get ARQ statistics"""
        stats = self.statistics.copy()
        if stats['packets_transmitted'] > 0:
            stats['retransmission_rate'] = (
                stats['total_retransmissions'] / stats['packets_transmitted']
            )
            stats['success_rate'] = (
                stats['packets_received'] / stats['packets_transmitted']
            )
        return stats
