"""
Configuration management with YAML support
"""
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration container"""

    def __init__(self, config_dict: Optional[Dict] = None):
        self.config = config_dict or self.default_config()

    @staticmethod
    def default_config() -> Dict[str, Any]:
        """Default configuration"""
        return {
            'controller': {
                'enabled': True,
                'algorithm': 'dijkstra',  # dijkstra, astar, greedy, exhaustive
                'strategy': 'max-snr',    # max-snr, min-hops, min-loss
                'use_beam_sweep': True
            },
            'environment': {
                'frequency_GHz': 5.8,
                'bandwidth_MHz': 20,
                'tx_power_dBm': 20,
                'noise_figure_dB': 10
            },
            'ris': {
                'default_N': 16,  # Grid size (N x N)
                'default_bits': 2,
                'default_max_angle_deg': 60,
                'active_mode': False,
                'amplifier_gain': 1.0
            },
            'visualization': {
                'show_beam_lobes': True,
                'show_deflection_angles': True,
                'show_aoi_annotations': False
            }
        }

    def get(self, key: str, default=None):
        """Get config value by dot-notation key"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set config value by dot-notation key"""
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return self.config.copy()

    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.config, default_flow_style=False)


def load_config(file_path: str) -> Config:
    """Load configuration from YAML file

    Args:
        file_path: Path to YAML config file

    Returns:
        Config object
    """
    path = Path(file_path)

    if not path.exists():
        return Config()

    with open(path, 'r') as f:
        config_dict = yaml.safe_load(f)

    return Config(config_dict)


def save_config(config: Config, file_path: str):
    """Save configuration to YAML file

    Args:
        config: Config object
        file_path: Path to save YAML file
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)
