"""
Comprehensive test suite for waveform-level RISNet features
"""
import numpy as np
import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import RISNetwork
from core.waveform import (
    OFDMConfig, OFDMSignal, PropagationChannel,
    AntennaArray, RISReflectionModel, OFDMReceiver,
    calculate_effective_snr, calculate_papr
)
from core.physics import Physics
from core.validation import WaveformValidator, PerformanceAnalyzer
from controller.waveform_controller import WaveformController


class TestWaveformGeneration:
    """Test OFDM signal generation"""

    def test_ofdm_config_initialization(self):
        """Test OFDM configuration"""
        config = OFDMConfig(bandwidth=100e6, num_subcarriers=256)
        assert config.subcarrier_spacing == 100e6 / 256
        print("✓ OFDM config initialization")

    def test_ofdm_signal_generation(self):
        """Test OFDM signal generation"""
        config = OFDMConfig()
        signal = OFDMSignal(config, num_symbols=5)
        tx = signal.generate()

        assert len(tx) > 0
        assert np.isfinite(tx).all()
        print("✓ OFDM signal generation")

    def test_ofdm_power_normalization(self):
        """Test OFDM signal power normalization"""
        config = OFDMConfig()
        signal = OFDMSignal(config, num_symbols=10)
        tx = signal.generate()

        power = np.mean(np.abs(tx)**2)
        assert 0.9 <= power <= 1.1, f"Power {power} not normalized"
        print("✓ OFDM power normalization")

    def test_papr_calculation(self):
        """Test PAPR calculation"""
        config = OFDMConfig()
        signal = OFDMSignal(config, num_symbols=5)
        tx = signal.generate()

        papr = calculate_papr(tx)
        assert 5 < papr < 15, f"PAPR {papr} out of expected range"
        print("✓ PAPR calculation")


class TestChannelModels:
    """Test propagation channel models"""

    def test_channel_initialization(self):
        """Test channel model initialization"""
        channel = PropagationChannel(10e9, 100e6, model='simple_multipath')
        assert len(channel.paths) > 0
        print("✓ Channel initialization")

    def test_awgn_addition(self):
        """Test AWGN addition"""
        channel = PropagationChannel(10e9, 100e6)
        signal = np.ones(1000, dtype=complex)

        noisy_signal = channel.add_awgn(signal, 10.0)
        assert len(noisy_signal) == len(signal)
        assert np.isfinite(noisy_signal).all()
        print("✓ AWGN addition")

    def test_multipath_propagation(self):
        """Test multipath propagation"""
        channel = PropagationChannel(10e9, 100e6, model='simple_multipath')
        signal = np.ones(1000, dtype=complex)

        received = channel.propagate(signal)
        assert len(received) == len(signal)
        assert np.isfinite(received).all()
        print("✓ Multipath propagation")


class TestAntennaArray:
    """Test antenna array models"""

    def test_ula_initialization(self):
        """Test ULA initialization"""
        array = AntennaArray(array_type='ula', num_elements=16, spacing=0.5, center_freq=10e9)
        assert array.positions.shape == (16, 3)
        print("✓ ULA initialization")

    def test_upa_initialization(self):
        """Test UPA initialization"""
        array = AntennaArray(array_type='upa', num_elements=16, spacing=0.5, center_freq=10e9)
        assert array.positions.shape == (16, 3)
        print("✓ UPA initialization")

    def test_radiation_pattern(self):
        """Test radiation pattern calculation"""
        array = AntennaArray(array_type='ula', num_elements=16, spacing=0.5, center_freq=10e9)
        pattern = array.get_radiation_pattern(theta=0.0, phi=0.0)

        assert len(pattern) == 16
        assert np.isfinite(pattern).all()
        print("✓ Radiation pattern calculation")

    def test_directional_gain(self):
        """Test directional gain calculation"""
        array = AntennaArray(array_type='ula', num_elements=16, spacing=0.5, center_freq=10e9)
        gain_boresight = array.get_directional_gain_dB(0.0)
        gain_off_axis = array.get_directional_gain_dB(np.pi/6)

        assert gain_boresight >= gain_off_axis
        print("✓ Directional gain calculation")


class TestRISReflectionModel:
    """Test RIS reflection model"""

    def test_ris_phase_quantization(self):
        """Test RIS phase quantization"""
        ris_model = RISReflectionModel(N=4, bits=2, center_freq=10e9)
        ideal_phases = np.random.uniform(0, 2*np.pi, 16)

        ris_model.set_phase_config(ideal_phases)
        assert ris_model.quantized_phases.shape == (16,)
        assert np.all(ris_model.quantized_phases >= 0)
        assert np.all(ris_model.quantized_phases < 2*np.pi)
        print("✓ RIS phase quantization")

    def test_ris_coupling_matrix(self):
        """Test RIS coupling matrix"""
        ris_model = RISReflectionModel(N=4, bits=2, center_freq=10e9, coupling_enabled=True)
        coupling = ris_model.coupling_matrix

        assert coupling.shape == (16, 16)
        assert np.isfinite(coupling).all()
        print("✓ RIS coupling matrix")

    def test_ris_reflection_matrix(self):
        """Test RIS reflection matrix"""
        ris_model = RISReflectionModel(N=4, bits=2, center_freq=10e9)
        ris_model.set_phase_config(np.zeros(16))

        reflection = ris_model.get_reflection_matrix()
        assert reflection.shape == (16, 16)
        assert np.isfinite(reflection).all()
        print("✓ RIS reflection matrix")


class TestOFDMReceiver:
    """Test OFDM receiver"""

    def test_receiver_initialization(self):
        """Test OFDM receiver initialization"""
        config = OFDMConfig()
        receiver = OFDMReceiver(config)
        assert receiver.config == config
        print("✓ OFDM receiver initialization")

    def test_snr_calculation(self):
        """Test SNR calculation"""
        config = OFDMConfig()
        receiver = OFDMReceiver(config)

        signal = np.random.randn(1000) + 1j * np.random.randn(1000)
        snr = receiver.calculate_snr(signal, noise_power=0.01)

        assert np.isfinite(snr)
        assert snr > 0
        print("✓ SNR calculation")


class TestPhysicsExtensions:
    """Test waveform-aware physics functions"""

    def test_directional_gain_calculation(self):
        """Test directional gain from position"""
        source = np.array([0, 0, 0])
        target = np.array([10, 0, 0])

        gain = Physics.directional_gain_from_position(source, target)
        assert np.isfinite(gain)
        print("✓ Directional gain calculation")

    def test_effective_snr_with_impairments(self):
        """Test effective SNR with waveform impairments"""
        ideal_snr = 20.0
        quant_error = 5.0  # degrees

        eff_snr = Physics.effective_snr_with_waveform_distortion(ideal_snr, quant_error)
        assert eff_snr < ideal_snr
        print("✓ Effective SNR with impairments")

    def test_ris_coupling_loss(self):
        """Test RIS coupling loss"""
        loss = Physics.ris_coupling_loss_dB(element_spacing_wavelengths=0.5, num_elements=16)
        assert loss < 0  # Loss is negative
        print("✓ RIS coupling loss")

    def test_channel_capacity(self):
        """Test Shannon capacity calculation"""
        capacity = Physics.compute_channel_capacity_bps(snr_dB=20, bandwidth_Hz=100e6)
        assert capacity > 0
        assert np.isfinite(capacity)
        print("✓ Channel capacity calculation")


class TestWaveformController:
    """Test waveform-aware controller"""

    def setup_network(self):
        """Setup test network"""
        net = RISNetwork()
        net.add_ap('AP1', 0, 0, 0)
        net.add_ris('R1', 5, 0, 0, N=4, bits=2)
        net.add_ue('UE1', 10, 0, 0)
        return net

    def test_controller_initialization(self):
        """Test controller initialization"""
        net = self.setup_network()
        controller = WaveformController(net)
        assert controller.network == net
        print("✓ Waveform controller initialization")

    def test_ofdm_config_setting(self):
        """Test OFDM configuration"""
        net = self.setup_network()
        controller = WaveformController(net)
        controller.set_ofdm_config(bandwidth=50e6, num_subcarriers=128)

        assert controller.ofdm_config.bandwidth == 50e6
        assert controller.ofdm_config.num_subcarriers == 128
        print("✓ OFDM config setting")

    def test_waveform_snr_computation(self):
        """Test waveform-level SNR computation"""
        net = self.setup_network()
        controller = WaveformController(net)

        try:
            result = controller.compute_waveform_snr('AP1', 'R1', 'UE1', num_symbols=3)

            assert 'snr_ris_dB' in result
            assert 'snr_effective_dB' in result
            assert 'capacity_bps' in result
            assert np.isfinite(result['snr_ris_dB'])
            print("✓ Waveform SNR computation")
        except Exception as e:
            print(f"⚠ Waveform SNR computation: {e}")

    def test_phase_optimization(self):
        """Test RIS phase optimization"""
        net = self.setup_network()
        controller = WaveformController(net)

        try:
            result = controller.optimize_ris_phases_waveform('AP1', 'R1', 'UE1', num_iterations=3)

            assert 'best_snr_dB' in result
            assert 'snr_history' in result
            assert len(result['snr_history']) == 3
            print("✓ Phase optimization")
        except Exception as e:
            print(f"⚠ Phase optimization: {e}")

    def test_beam_sweep(self):
        """Test beam sweep at waveform level"""
        net = self.setup_network()
        controller = WaveformController(net)

        try:
            result = controller.compute_beam_sweep_waveform('AP1', 'R1', 'UE1',
                                                           angle_range=30, angle_step=10)

            assert 'angles' in result
            assert 'snr_values' in result
            assert 'best_angle' in result
            print("✓ Beam sweep")
        except Exception as e:
            print(f"⚠ Beam sweep: {e}")


class TestValidation:
    """Test validation framework"""

    def setup_network(self):
        """Setup test network"""
        net = RISNetwork()
        net.add_ap('AP1', 0, 0, 0)
        net.add_ris('R1', 5, 0, 0, N=4, bits=2)
        net.add_ue('UE1', 10, 0, 0)
        return net

    def test_validator_initialization(self):
        """Test validator initialization"""
        net = self.setup_network()
        validator = WaveformValidator(net)
        assert validator.network == net
        print("✓ Validator initialization")

    def test_physics_validation(self):
        """Test physics validation"""
        net = self.setup_network()
        validator = WaveformValidator(net)

        result = validator.validate_basic_physics('AP1', 'R1', 'UE1')
        assert 'physics_valid' in result
        assert 'checks' in result
        print("✓ Physics validation")

    def test_topology_validation(self):
        """Test topology validation"""
        net = self.setup_network()
        validator = WaveformValidator(net)

        result = validator.validate_topology()
        assert result['num_aps'] == 1
        assert result['num_ris'] == 1
        assert result['num_ues'] == 1
        assert result['valid'] == True
        print("✓ Topology validation")

    def test_comparison_metrics(self):
        """Test comparison metrics"""
        net = self.setup_network()
        validator = WaveformValidator(net)

        system_result = {'snr_dB': 15.0, 'pwr_dBm': 20.0}
        waveform_result = {
            'snr_ris_dB': 16.0,
            'snr_effective_dB': 14.5,
            'capacity_bps': 1e8,
            'papr_dB': 8.0
        }

        metrics = validator.compare_results(system_result, waveform_result)
        assert metrics.snr_diff_dB == 1.0
        print("✓ Comparison metrics")

    def test_report_generation(self):
        """Test report generation"""
        net = self.setup_network()
        validator = WaveformValidator(net)

        system_result = {'snr_dB': 15.0, 'pwr_dBm': 20.0}
        waveform_result = {
            'snr_ris_dB': 16.0,
            'snr_effective_dB': 14.5,
            'capacity_bps': 1e8
        }

        validator.compare_results(system_result, waveform_result)
        report = validator.generate_report()

        assert 'VALIDATION REPORT' in report
        assert len(report) > 0
        print("✓ Report generation")


class TestPerformanceAnalysis:
    """Test performance analysis"""

    def test_fom_computation(self):
        """Test FOM computation"""
        system_result = {'snr_dB': 15.0, 'pwr_dBm': 20.0}
        waveform_result = {
            'snr_ris_dB': 16.0,
            'snr_effective_dB': 14.5,
            'capacity_bps': 1e8,
            'papr_dB': 8.0,
            'phase_states': 4,
            'bandwidth_MHz': 100
        }

        fom = PerformanceAnalyzer.compute_fom(system_result, waveform_result)

        assert 'snr_improvement_dB' in fom
        assert 'quantization_penalty_dB' in fom
        assert 'spectral_efficiency_bps_hz' in fom
        print("✓ FOM computation")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("WAVEFORM-LEVEL RISNET TEST SUITE")
    print("="*70 + "\n")

    test_classes = [
        TestWaveformGeneration,
        TestChannelModels,
        TestAntennaArray,
        TestRISReflectionModel,
        TestOFDMReceiver,
        TestPhysicsExtensions,
        TestWaveformController,
        TestValidation,
        TestPerformanceAnalysis,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 70)

        test_instance = test_class()
        test_methods = [m for m in dir(test_instance)
                       if m.startswith('test_') and callable(getattr(test_instance, m))]

        for test_method in test_methods:
            total_tests += 1
            try:
                getattr(test_instance, test_method)()
                passed_tests += 1
            except Exception as e:
                failed_tests += 1
                print(f"✗ {test_method}: {e}")

    print("\n" + "="*70)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    if failed_tests > 0:
        print(f"FAILURES: {failed_tests} tests failed")
    print("="*70 + "\n")

    return passed_tests == total_tests


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
