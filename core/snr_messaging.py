"""
SNR Messaging Protocol System

Implements real-world SNR query/response communication between:
- RIS Controller (requests SNR from UE/AP)
- UE/AP nodes (respond with measured SNR)

Mimics real wireless control channel behavior:
- Message serialization/deserialization
- Request/response matching
- Latency simulation
- Timeout handling
- Error cases
"""

from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, asdict
import time
import uuid


# Message Types
MSG_TYPE_SNR_REQUEST = 'SNR_REQUEST'
MSG_TYPE_SNR_RESPONSE = 'SNR_RESPONSE'
MSG_TYPE_SNR_ERROR = 'SNR_ERROR'


@dataclass
class SNRQueryMessage:
    """SNR Query Request from Controller to UE/AP"""
    msg_type: str = MSG_TYPE_SNR_REQUEST
    request_id: str = None  # Unique identifier
    timestamp: float = None  # When request was sent
    controller_name: str = None  # Which RIS controller
    target_ue_name: str = None  # Which UE to query
    target_ris_name: str = None  # Which RIS context

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())[:8]
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict:
        """Serialize for transmission"""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'SNRQueryMessage':
        """Deserialize from received data"""
        return SNRQueryMessage(**data)


@dataclass
class SNRResponseMessage:
    """SNR Measurement Response from UE/AP to Controller"""
    msg_type: str = MSG_TYPE_SNR_RESPONSE
    request_id: str = None  # Matches request
    timestamp_sent: float = None  # Request timestamp
    timestamp_received: float = None  # When UE received request
    timestamp_response: float = None  # When UE sent response
    ue_name: str = None  # Source UE
    ris_name: str = None  # Context RIS
    snr_dB: float = None  # Measured SNR in dB
    snr_linear: float = None  # Measured SNR linear
    rssi_dBm: float = None  # Received signal strength
    status: str = 'success'  # 'success', 'error', 'timeout'
    error_message: str = None  # If status != 'success'

    def __post_init__(self):
        if self.timestamp_response is None:
            self.timestamp_response = time.time()

    def to_dict(self) -> Dict:
        """Serialize for transmission"""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'SNRResponseMessage':
        """Deserialize from received data"""
        return SNRResponseMessage(**data)

    def round_trip_time(self) -> Optional[float]:
        """Calculate round-trip latency in milliseconds"""
        if self.timestamp_sent and self.timestamp_response:
            return (self.timestamp_response - self.timestamp_sent) * 1000
        return None


class SNRMessagingChannel:
    """
    Simulates a control channel for SNR query/response communication.

    Models real-world characteristics:
    - Propagation latency
    - Message processing delays
    - Timeout handling
    - Error cases
    """

    def __init__(self,
                 name: str = 'control_channel',
                 latency_ms: float = 5.0,
                 jitter_ms: float = 1.0,
                 error_rate: float = 0.0):
        """
        Initialize messaging channel.

        Args:
            name: Channel name
            latency_ms: Base latency in milliseconds
            jitter_ms: Latency jitter (±)
            error_rate: Message error rate (0-1)
        """
        self.name = name
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.error_rate = error_rate

        # Message tracking
        self.pending_requests: Dict[str, SNRQueryMessage] = {}
        self.message_history: List[Dict] = []
        self.request_handlers: Dict[str, Callable] = {}  # ue_name -> handler

    def register_ue_handler(self, ue_name: str, handler: Callable) -> None:
        """
        Register SNR response handler for a UE.

        Args:
            ue_name: UE node name
            handler: Function that takes SNRQueryMessage and returns SNRResponseMessage
        """
        self.request_handlers[ue_name] = handler

    def get_actual_latency(self) -> float:
        """Get latency with jitter (milliseconds)"""
        import numpy as np
        jitter = np.random.uniform(-self.jitter_ms, self.jitter_ms)
        actual = self.latency_ms + jitter
        return max(actual, 0.1)  # Minimum 0.1ms

    def send_snr_query(self, controller_name: str, target_ue_name: str,
                      target_ris_name: str) -> Optional[str]:
        """
        Send SNR query request from controller to UE.

        Args:
            controller_name: RIS controller name
            target_ue_name: Target UE name
            target_ris_name: RIS context name

        Returns:
            Request ID (for tracking), or None if error
        """
        # Create query message
        query = SNRQueryMessage(
            controller_name=controller_name,
            target_ue_name=target_ue_name,
            target_ris_name=target_ris_name
        )

        # Check for transmission error
        import numpy as np
        if np.random.random() < self.error_rate:
            self.message_history.append({
                'type': 'query',
                'request_id': query.request_id,
                'status': 'transmission_error',
                'timestamp': time.time()
            })
            return None

        # Store pending request
        self.pending_requests[query.request_id] = query

        self.message_history.append({
            'type': 'query',
            'request_id': query.request_id,
            'status': 'sent',
            'timestamp': time.time(),
            'target_ue': target_ue_name,
            'latency_ms': self.get_actual_latency()
        })

        return query.request_id

    def receive_snr_response(self, request_id: str,
                            timeout_ms: float = 1000.0) -> Optional[SNRResponseMessage]:
        """
        Receive SNR response from UE.

        Simulates:
        - Request transmission latency
        - UE processing latency
        - Response transmission latency
        - Timeout if UE doesn't respond

        Args:
            request_id: Request ID to match
            timeout_ms: Maximum wait time in milliseconds

        Returns:
            SNRResponseMessage if successful, None if timeout/error
        """
        if request_id not in self.pending_requests:
            return None

        query = self.pending_requests[request_id]
        ue_name = query.target_ue_name

        # Check if handler registered for this UE
        if ue_name not in self.request_handlers:
            response = SNRResponseMessage(
                request_id=request_id,
                timestamp_sent=query.timestamp,
                ue_name=ue_name,
                status='error',
                error_message=f'No handler registered for UE: {ue_name}'
            )
            self.message_history.append({
                'type': 'response',
                'request_id': request_id,
                'status': 'no_handler',
                'timestamp': time.time()
            })
            del self.pending_requests[request_id]
            return response

        # Call handler to get SNR measurement
        try:
            handler = self.request_handlers[ue_name]
            response = handler(query)
            response.request_id = request_id
            response.timestamp_sent = query.timestamp

            # Record in history
            self.message_history.append({
                'type': 'response',
                'request_id': request_id,
                'status': 'received',
                'timestamp': time.time(),
                'snr_dB': response.snr_dB,
                'rtt_ms': response.round_trip_time()
            })

            del self.pending_requests[request_id]
            return response

        except Exception as e:
            response = SNRResponseMessage(
                request_id=request_id,
                timestamp_sent=query.timestamp,
                ue_name=ue_name,
                status='error',
                error_message=f'Handler error: {str(e)}'
            )
            self.message_history.append({
                'type': 'response',
                'request_id': request_id,
                'status': 'handler_error',
                'timestamp': time.time()
            })
            del self.pending_requests[request_id]
            return response

    def get_channel_statistics(self) -> Dict:
        """Get messaging channel statistics"""
        responses = [m for m in self.message_history if m['type'] == 'response']
        queries = [m for m in self.message_history if m['type'] == 'query']

        rtt_times = [m['rtt_ms'] for m in responses if m.get('rtt_ms')]

        return {
            'total_queries': len(queries),
            'total_responses': len(responses),
            'success_rate': len(responses) / len(queries) if queries else 0,
            'avg_rtt_ms': sum(rtt_times) / len(rtt_times) if rtt_times else None,
            'min_rtt_ms': min(rtt_times) if rtt_times else None,
            'max_rtt_ms': max(rtt_times) if rtt_times else None,
            'pending_requests': len(self.pending_requests),
            'base_latency_ms': self.latency_ms,
            'jitter_ms': self.jitter_ms,
            'error_rate': self.error_rate
        }

    def get_message_history(self, last_n: Optional[int] = None) -> List[Dict]:
        """Get message transmission history"""
        if last_n is None:
            return self.message_history
        return self.message_history[-last_n:]

    def clear_history(self) -> None:
        """Clear message history"""
        self.message_history.clear()

    def reset(self) -> None:
        """Reset channel to initial state"""
        self.pending_requests.clear()
        self.message_history.clear()


class SNRMessagingSystem:
    """
    Manages SNR messaging for entire network.

    Coordinates:
    - Multiple control channels
    - Request routing to correct UE
    - Response collection from controller
    - Network-wide statistics
    """

    def __init__(self, network, latency_ms: float = 5.0, jitter_ms: float = 1.0):
        """
        Initialize messaging system.

        Args:
            network: RISNetwork instance
            latency_ms: Base control channel latency
            jitter_ms: Latency jitter
        """
        self.network = network
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms

        # Create main control channel
        self.control_channel = SNRMessagingChannel(
            name='main_control',
            latency_ms=latency_ms,
            jitter_ms=jitter_ms
        )

        # Register UE handlers
        self._register_ue_handlers()

    def _register_ue_handlers(self) -> None:
        """Register SNR measurement handlers for all UEs"""
        for node_name, node in self.network.nodes.items():
            # Check if it's a UE (has snr_measurement_dB attribute)
            if hasattr(node, 'snr_measurement_dB'):
                self.control_channel.register_ue_handler(
                    node_name,
                    self._create_ue_handler(node_name)
                )

    def _create_ue_handler(self, ue_name: str) -> Callable:
        """Create SNR measurement handler for a UE"""
        def handler(query: SNRQueryMessage) -> SNRResponseMessage:
            ue = self.network.get(ue_name)
            if ue is None:
                return SNRResponseMessage(
                    status='error',
                    error_message=f'UE not found: {ue_name}'
                )

            metadata = ue.get_link_metadata(query.controller_name, query.target_ris_name)
            if metadata is not None:
                snr_db = ue.compute_snr_from_metadata(metadata)
            else:
                snr_db = ue.snr_measurement_dB

            if snr_db is None:
                # No measurement yet - return error, will trigger fallback to physics
                return SNRResponseMessage(
                    status='error',
                    error_message=f'No SNR measurement available for {ue_name}'
                )

            # Convert to linear if needed
            snr_linear = 10 ** (snr_db / 10) if snr_db > -100 else 1e-10

            return SNRResponseMessage(
                timestamp_received=time.time(),
                ue_name=ue_name,
                ris_name=query.target_ris_name,
                snr_dB=snr_db,
                snr_linear=snr_linear,
                status='success'
            )

        return handler

    def query_ue_snr(self, controller_name: str, ue_name: str,
                     ris_name: str) -> Optional[SNRResponseMessage]:
        """
        Query SNR from UE (mimics real control channel).

        Simulates:
        1. Controller sends SNR_REQUEST to UE
        2. Latency for message transmission
        3. UE receives and processes request
        4. UE sends SNR_RESPONSE back
        5. Latency for response transmission
        6. Controller receives response

        Args:
            controller_name: RIS controller name
            ue_name: Target UE name
            ris_name: RIS context

        Returns:
            SNRResponseMessage with measured SNR, or None if error/timeout
        """
        # Register handler for this UE if not already registered
        if ue_name not in self.control_channel.request_handlers:
            if ue_name in self.network.nodes:
                self.control_channel.register_ue_handler(
                    ue_name,
                    self._create_ue_handler(ue_name)
                )

        # Send query request
        request_id = self.control_channel.send_snr_query(
            controller_name, ue_name, ris_name
        )

        if request_id is None:
            return None  # Transmission error

        # Receive response (with simulated latency)
        response = self.control_channel.receive_snr_response(request_id)

        return response

    def get_snr(self, ue_name: str, ris_name: str = None) -> Optional[float]:
        """
        Get SNR for a UE via messaging system (instead of computing).

        This function queries the UE for its measured SNR value through the
        control channel, simulating real-world scenario where RIS controller
        doesn't compute SNR but receives it from the UE via feedback.

        Args:
            ue_name: Target UE node name
            ris_name: RIS context name (optional, defaults to first RIS in network)

        Returns:
            SNR in dB (float), or None if query fails
        """
        # Default ris_name to first available RIS if not specified
        if ris_name is None:
            for node_name, node in self.network.nodes.items():
                if hasattr(node, 'num_elements'):  # RIS nodes have num_elements
                    ris_name = node_name
                    break
            if ris_name is None:
                ris_name = 'RIS1'  # Fallback

        # Use first RIS as controller
        controller_name = ris_name

        # Query UE for SNR via messaging system
        response = self.query_ue_snr(controller_name, ue_name, ris_name)

        if response is None or response.status != 'success':
            return None

        return response.snr_dB

    def get_statistics(self) -> Dict:
        """Get network-wide messaging statistics"""
        return self.control_channel.get_channel_statistics()

    def get_message_history(self, last_n: Optional[int] = None) -> List[Dict]:
        """Get message transmission history"""
        return self.control_channel.get_message_history(last_n)

    def reset(self) -> None:
        """Reset messaging system"""
        self.control_channel.reset()
        self._register_ue_handlers()
