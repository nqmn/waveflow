"""
Input validation and error handling for API endpoints
"""

from typing import Tuple, Any, Optional
import numpy as np


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class InputValidator:
    """Validate API input parameters"""

    @staticmethod
    def validate_node_type(typ: str) -> str:
        """Validate node type

        Args:
            typ: Node type ('ap', 'ris', 'ue')

        Returns:
            Normalized type string

        Raises:
            ValidationError: If type is invalid
        """
        valid_types = {'ap', 'ris', 'ue'}
        if typ.lower() not in valid_types:
            raise ValidationError(f"Invalid node type '{typ}'. Must be one of: {valid_types}")
        return typ.lower()

    @staticmethod
    def validate_coordinates(x: Any, y: Any, z: Any = 0.0) -> Tuple[float, float, float]:
        """Validate and convert coordinates

        Args:
            x, y, z: Coordinates

        Returns:
            Tuple of (x, y, z) as floats

        Raises:
            ValidationError: If coordinates are invalid
        """
        try:
            x_f = float(x) if x is not None else 0.0
            y_f = float(y) if y is not None else 0.0
            z_f = float(z) if z is not None else 0.0

            # Check for NaN or inf
            for val in [x_f, y_f, z_f]:
                if np.isnan(val) or np.isinf(val):
                    raise ValidationError(f"Coordinate value is NaN or infinite: {val}")

            return x_f, y_f, z_f

        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid coordinate value: {e}")

    @staticmethod
    def validate_node_name(name: str) -> str:
        """Validate node name

        Args:
            name: Node name

        Returns:
            Normalized name

        Raises:
            ValidationError: If name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValidationError("Node name must be a non-empty string")

        if len(name) > 256:
            raise ValidationError("Node name is too long (max 256 characters)")

        return name.strip()

    @staticmethod
    def validate_positive_int(value: Any, field_name: str, min_val: int = 1) -> int:
        """Validate positive integer

        Args:
            value: Value to validate
            field_name: Field name for error message
            min_val: Minimum allowed value (default 1)

        Returns:
            Integer value

        Raises:
            ValidationError: If validation fails
        """
        try:
            val = int(value)
            if val < min_val:
                raise ValidationError(
                    f"{field_name} must be >= {min_val}, got {val}"
                )
            return val
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name} must be an integer, got {value}")

    @staticmethod
    def validate_positive_float(
        value: Any, field_name: str, min_val: float = 0.0
    ) -> float:
        """Validate positive float

        Args:
            value: Value to validate
            field_name: Field name for error message
            min_val: Minimum allowed value (default 0.0)

        Returns:
            Float value

        Raises:
            ValidationError: If validation fails
        """
        try:
            val = float(value)
            if np.isnan(val) or np.isinf(val):
                raise ValidationError(f"{field_name} is NaN or infinite")
            if val < min_val:
                raise ValidationError(
                    f"{field_name} must be >= {min_val}, got {val}"
                )
            return val
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name} must be a number, got {value}")

    @staticmethod
    def validate_ris_params(N: Any, bits: Any) -> Tuple[int, int]:
        """Validate RIS parameters

        Args:
            N: Grid size (N x N)
            bits: Quantization bits

        Returns:
            Tuple of (N, bits)

        Raises:
            ValidationError: If validation fails
        """
        N = InputValidator.validate_positive_int(N, "N (RIS grid size)", min_val=4)
        bits = InputValidator.validate_positive_int(bits, "bits (quantization)", min_val=1)

        if N > 256:
            raise ValidationError(f"RIS grid size too large: {N} (max 256)")
        if bits > 8:
            raise ValidationError(f"Quantization bits too large: {bits} (max 8)")

        return N, bits

    @staticmethod
    def validate_node_exists(net, name: str) -> None:
        """Validate that a node exists

        Args:
            net: RISNetwork instance
            name: Node name

        Raises:
            ValidationError: If node doesn't exist
        """
        if not net.get(name):
            available = ", ".join(net.list_nodes()) if hasattr(net, 'list_nodes') else "unknown"
            raise ValidationError(
                f"Node '{name}' not found. Available nodes: {available}"
            )

    @staticmethod
    def validate_nodes_exist(net, *names: str) -> None:
        """Validate that multiple nodes exist

        Args:
            net: RISNetwork instance
            names: Node names to validate

        Raises:
            ValidationError: If any node doesn't exist
        """
        missing = []
        for name in names:
            if not net.get(name):
                missing.append(f"'{name}'")

        if missing:
            available = ", ".join(net.list_nodes()) if hasattr(net, 'list_nodes') else "unknown"
            raise ValidationError(
                f"Node(s) not found: {', '.join(missing)}. Available: {available}"
            )

    @staticmethod
    def validate_angle(angle: Any, field_name: str = "angle") -> float:
        """Validate angle in degrees

        Args:
            angle: Angle value
            field_name: Field name for error message

        Returns:
            Angle as float

        Raises:
            ValidationError: If validation fails
        """
        angle_f = InputValidator.validate_positive_float(
            angle, field_name, min_val=-360.0
        )
        if angle_f > 360.0:
            raise ValidationError(f"{field_name} should be in range [-360, 360], got {angle_f}")
        return angle_f

    @staticmethod
    def validate_algorithm(algorithm: str) -> str:
        """Validate pathfinding algorithm name

        Args:
            algorithm: Algorithm name

        Returns:
            Normalized algorithm name

        Raises:
            ValidationError: If algorithm is invalid
        """
        valid_algorithms = {'dijkstra', 'astar', 'a*', 'greedy', 'exhaustive'}
        if algorithm.lower() not in valid_algorithms:
            raise ValidationError(
                f"Invalid algorithm '{algorithm}'. "
                f"Must be one of: {valid_algorithms}"
            )
        return algorithm.lower()
