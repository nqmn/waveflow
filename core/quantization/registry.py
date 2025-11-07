"""
Registry and loader for quantization strategies

This module manages available quantizers and allows loading them from:
1. Built-in quantizers (uniform, legacy)
2. Custom quantizers from plugin folder
"""
import os
import json
import importlib.util
import numpy as np
from pathlib import Path
from .base import BaseQuantizer
from .uniform import UniformQuantizer
from .legacy import LegacyQuantizer


class QuantizerRegistry:
    """Registry for managing quantization strategies

    Supports built-in quantizers and plugin quantizers loaded from folders.
    """

    def __init__(self):
        """Initialize registry with built-in quantizers"""
        self._quantizers = {}
        self._register_builtin()

    def _register_builtin(self):
        """Register built-in quantizers"""
        self.register(UniformQuantizer())
        self.register(LegacyQuantizer())

    def register(self, quantizer):
        """Register a quantizer

        Args:
            quantizer: Instance of BaseQuantizer subclass

        Raises:
            ValueError: If quantizer doesn't inherit from BaseQuantizer
        """
        if not isinstance(quantizer, BaseQuantizer):
            raise ValueError(f"Quantizer must inherit from BaseQuantizer, got {type(quantizer)}")

        self._quantizers[quantizer.name] = quantizer
        print(f"Registered quantizer: {quantizer.name}")

    def get(self, name):
        """Get quantizer by name

        Args:
            name: Quantizer name

        Returns:
            Quantizer instance or None if not found
        """
        return self._quantizers.get(name)

    def list_quantizers(self):
        """List all available quantizers

        Returns:
            List of (name, description) tuples
        """
        return [(q.name, q.description) for q in self._quantizers.values()]

    def load_from_folder(self, folder_path):
        """Load custom quantizers from a folder

        Each quantizer plugin folder should contain:
        - quantizer.py: Module with Quantizer class inheriting from BaseQuantizer
        - config.json: Optional configuration metadata

        Folder structure:
            plugins/
            ├── my_quantizer_1/
            │   ├── quantizer.py
            │   └── config.json
            ├── my_quantizer_2/
            │   ├── quantizer.py
            │   └── config.json
            ...

        Args:
            folder_path: Path to plugins folder
        """
        folder_path = Path(folder_path)

        if not folder_path.exists():
            print(f"Plugin folder not found: {folder_path}")
            return

        if not folder_path.is_dir():
            print(f"Not a directory: {folder_path}")
            return

        loaded_count = 0
        for plugin_dir in folder_path.iterdir():
            if not plugin_dir.is_dir():
                continue

            quantizer_file = plugin_dir / "quantizer.py"
            if not quantizer_file.exists():
                print(f"  Skip {plugin_dir.name}: No quantizer.py found")
                continue

            try:
                # Load quantizer module
                spec = importlib.util.spec_from_file_location(
                    f"quantizer_{plugin_dir.name}",
                    quantizer_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find Quantizer class in module
                quantizer_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseQuantizer) and
                        attr != BaseQuantizer):
                        quantizer_class = attr
                        break

                if quantizer_class is None:
                    print(f"  Skip {plugin_dir.name}: No Quantizer class found")
                    continue

                # Instantiate and register
                quantizer = quantizer_class()
                self.register(quantizer)
                loaded_count += 1

                # Load optional config
                config_file = plugin_dir / "config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        # Store config for reference
                        quantizer.config = config

            except Exception as e:
                print(f"  Error loading {plugin_dir.name}: {e}")

        if loaded_count > 0:
            print(f"Loaded {loaded_count} quantizer plugins from {folder_path}")

    def __repr__(self):
        return f"QuantizerRegistry({len(self._quantizers)} quantizers)"


# Global registry instance
_registry = None


def get_registry():
    """Get or create global quantizer registry

    Returns:
        QuantizerRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = QuantizerRegistry()
    return _registry


def register_quantizer(quantizer):
    """Register a quantizer globally

    Args:
        quantizer: Instance of BaseQuantizer subclass
    """
    get_registry().register(quantizer)


def get_quantizer(name):
    """Get quantizer by name from global registry

    Args:
        name: Quantizer name

    Returns:
        Quantizer instance or None
    """
    return get_registry().get(name)


def list_quantizers():
    """List all available quantizers

    Returns:
        List of (name, description) tuples
    """
    return get_registry().list_quantizers()


def load_quantizers_from_folder(folder_path):
    """Load custom quantizers from folder

    Args:
        folder_path: Path to plugins folder
    """
    get_registry().load_from_folder(folder_path)
