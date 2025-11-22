"""
Data type converters between NumPy and MATLAB.

All MATLAB imports are lazy-loaded to avoid startup overhead.
"""

from typing import Any, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    import matlab

_matlab_module = None


def _get_matlab():
    """Lazy load matlab module."""
    global _matlab_module
    if _matlab_module is None:
        import matlab
        _matlab_module = matlab
    return _matlab_module


def numpy_to_matlab(arr: np.ndarray) -> 'matlab.double':
    """
    Convert numpy array to MATLAB double array.

    Args:
        arr: NumPy array (1D or 2D)

    Returns:
        matlab.double array
    """
    matlab = _get_matlab()

    if arr.ndim == 1:
        return matlab.double(arr.tolist())
    elif arr.ndim == 2:
        return matlab.double(arr.tolist())
    else:
        # Flatten higher dimensional arrays
        return matlab.double(arr.flatten().tolist())


def matlab_to_numpy(mat_arr: Any) -> np.ndarray:
    """
    Convert MATLAB array to NumPy array.

    Args:
        mat_arr: MATLAB array (matlab.double or similar)

    Returns:
        NumPy ndarray
    """
    return np.array(mat_arr)


def numpy_complex_to_matlab(arr: np.ndarray):
    """
    Convert complex numpy array to MATLAB.

    Args:
        arr: Complex NumPy array

    Returns:
        Tuple of (real_matlab, imag_matlab) arrays
    """
    matlab = _get_matlab()

    real_part = matlab.double(np.real(arr).tolist())
    imag_part = matlab.double(np.imag(arr).tolist())
    return real_part, imag_part


def dict_to_matlab_struct(d: dict) -> dict:
    """
    Convert Python dict to MATLAB-compatible struct dict.

    Converts numpy arrays within the dict to matlab arrays.

    Args:
        d: Python dictionary

    Returns:
        Dictionary with MATLAB-compatible values
    """
    result = {}
    for key, value in d.items():
        if isinstance(value, np.ndarray):
            result[key] = numpy_to_matlab(value)
        elif isinstance(value, dict):
            result[key] = dict_to_matlab_struct(value)
        elif isinstance(value, (list, tuple)):
            result[key] = [
                numpy_to_matlab(v) if isinstance(v, np.ndarray) else v
                for v in value
            ]
        else:
            result[key] = value
    return result
