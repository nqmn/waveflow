"""
RIS Phase Optimization - Iterative algorithms for finding optimal phase configurations

Implements optimization strategies:
- Gradient-based phase optimization
- Exhaustive search over phase states
- Genetic algorithm for phase optimization
- Simulated annealing
"""

import numpy as np
from typing import Dict, Callable, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class PhaseOptimizer:
    """Base class for phase optimization"""

    def __init__(self, ris_node, snr_function: Callable):
        """
        Initialize phase optimizer.

        Args:
            ris_node: RIS node instance
            snr_function: Function that computes SNR given phases
                         Signature: snr = snr_function(phases)
        """
        self.ris = ris_node
        self.snr_function = snr_function
        self.optimization_history = []
        self.best_phases = None
        self.best_snr = -np.inf

    def optimize(self, max_iterations: int = 100) -> Dict:
        """
        Run optimization algorithm.

        Args:
            max_iterations: Maximum number of iterations

        Returns:
            Dictionary with optimization results
        """
        raise NotImplementedError

    def get_history(self) -> List[Dict]:
        """Return optimization history"""
        return self.optimization_history

    def reset(self):
        """Reset optimization state"""
        self.optimization_history = []
        self.best_phases = None
        self.best_snr = -np.inf


class GradientPhaseOptimizer(PhaseOptimizer):
    """
    Gradient-based phase optimization using finite differences.

    Approximates gradient of SNR with respect to phases and updates using gradient ascent.
    """

    def __init__(self, ris_node, snr_function: Callable, learning_rate: float = 0.01):
        """
        Initialize gradient optimizer.

        Args:
            ris_node: RIS node instance
            snr_function: SNR computation function
            learning_rate: Learning rate for gradient updates
        """
        super().__init__(ris_node, snr_function)
        self.learning_rate = learning_rate

    def _compute_gradient(
        self,
        phases: np.ndarray,
        perturbation: float = 0.01
    ) -> np.ndarray:
        """
        Compute gradient of SNR using finite differences.

        Args:
            phases: Current phase array
            perturbation: Perturbation amount for finite difference

        Returns:
            Gradient vector
        """
        gradient = np.zeros_like(phases)
        current_snr = self.snr_function(phases)

        for i in range(len(phases)):
            phases_perturbed = phases.copy()
            phases_perturbed[i] += perturbation

            perturbed_snr = self.snr_function(phases_perturbed)

            # Gradient approximation
            gradient[i] = (perturbed_snr - current_snr) / perturbation

        return gradient

    def optimize(self, max_iterations: int = 100) -> Dict:
        """
        Optimize phases using gradient ascent.

        Args:
            max_iterations: Maximum iterations

        Returns:
            Optimization results
        """
        if self.ris.current_phases is None:
            return {'status': 'failed', 'error': 'No initial phases'}

        phases = self.ris.current_phases.copy()
        num_evaluations = 0

        for iteration in range(max_iterations):
            try:
                # Compute SNR
                snr = self.snr_function(phases)
                num_evaluations += 1

                # Store history
                self.optimization_history.append({
                    'iteration': iteration,
                    'snr_dB': 10 * np.log10(snr) if snr > 0 else -np.inf,
                    'num_evaluations': num_evaluations
                })

                # Update best
                if snr > self.best_snr:
                    self.best_snr = snr
                    self.best_phases = phases.copy()

                # Compute gradient
                gradient = self._compute_gradient(phases)
                gradient_magnitude = np.linalg.norm(gradient)

                # Update phases
                phases = phases + self.learning_rate * gradient

                # Wrap to [0, 2π)
                phases = phases % (2 * np.pi)

                # Check convergence
                if gradient_magnitude < 1e-4:
                    logger.info(f"Gradient optimization converged at iteration {iteration}")
                    break

            except Exception as e:
                logger.error(f"Gradient optimization failed at iteration {iteration}: {e}")
                break

        # Apply best phases to RIS
        self.ris.current_phases = self.best_phases
        self.ris.quantize_phases()

        return {
            'status': 'success',
            'iterations': len(self.optimization_history),
            'best_snr_dB': 10 * np.log10(self.best_snr) if self.best_snr > 0 else -np.inf,
            'num_evaluations': num_evaluations,
            'history': self.optimization_history
        }


class ExhaustivePhaseOptimizer(PhaseOptimizer):
    """Exhaustive search over all phase state combinations"""

    def optimize(self, max_iterations: Optional[int] = None) -> Dict:
        """
        Exhaustively search all phase state combinations.

        Warning: Exponential complexity O(2^(N*bits))

        Args:
            max_iterations: Limit search (not used, all combinations tested)

        Returns:
            Optimization results
        """
        num_elements = len(self.ris.current_phases)
        num_bits = self.ris.bits
        num_states = 2 ** num_bits

        # Only feasible for small arrays
        total_combinations = num_states ** num_elements
        if total_combinations > 1e6:
            logger.warning(f"Exhaustive search has {total_combinations} combinations, may be slow")

        try:
            best_snr = -np.inf
            best_phases = None
            num_evaluations = 0

            # Generate all phase state combinations
            import itertools

            for combination in itertools.product(range(num_states), repeat=num_elements):
                # Convert state combination to phases
                phase_step = 2 * np.pi / num_states
                phases = np.array(combination) * phase_step

                # Evaluate
                snr = self.snr_function(phases)
                num_evaluations += 1

                if snr > best_snr:
                    best_snr = snr
                    best_phases = phases.copy()
                    self.best_snr = best_snr
                    self.best_phases = best_phases

                # Store history (sample for large searches)
                if num_evaluations % max(1, num_evaluations // 100) == 0:
                    self.optimization_history.append({
                        'evaluations': num_evaluations,
                        'best_snr_dB': 10 * np.log10(best_snr) if best_snr > 0 else -np.inf
                    })

        except Exception as e:
            logger.error(f"Exhaustive search failed: {e}")
            return {'status': 'failed', 'error': str(e)}

        # Apply best phases
        self.ris.current_phases = self.best_phases
        self.ris.quantize_phases()

        return {
            'status': 'success',
            'best_snr_dB': 10 * np.log10(self.best_snr) if self.best_snr > 0 else -np.inf,
            'num_evaluations': num_evaluations,
            'total_combinations': total_combinations,
            'history': self.optimization_history
        }


class GeneticAlgorithmOptimizer(PhaseOptimizer):
    """Genetic algorithm for phase optimization"""

    def __init__(
        self,
        ris_node,
        snr_function: Callable,
        population_size: int = 20,
        mutation_rate: float = 0.1
    ):
        """
        Initialize GA optimizer.

        Args:
            ris_node: RIS node instance
            snr_function: SNR function
            population_size: Population size
            mutation_rate: Mutation probability per gene
        """
        super().__init__(ris_node, snr_function)
        self.population_size = population_size
        self.mutation_rate = mutation_rate

    def _initialize_population(self) -> np.ndarray:
        """Generate initial population"""
        num_elements = len(self.ris.current_phases)
        population = np.random.uniform(0, 2*np.pi, (self.population_size, num_elements))
        return population

    def _evaluate_fitness(self, phases: np.ndarray) -> float:
        """Evaluate fitness (SNR) for phase array"""
        snr = self.snr_function(phases)
        return snr

    def _select_parents(self, population: np.ndarray, fitnesses: np.ndarray) -> Tuple:
        """Select two parents using tournament selection"""
        tournament_size = 3
        indices = np.arange(len(population))

        # Tournament 1
        tournament1 = np.random.choice(indices, tournament_size, replace=False)
        parent1_idx = tournament1[np.argmax(fitnesses[tournament1])]

        # Tournament 2
        tournament2 = np.random.choice(indices, tournament_size, replace=False)
        parent2_idx = tournament2[np.argmax(fitnesses[tournament2])]

        return population[parent1_idx], population[parent2_idx]

    def _crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        """Single-point crossover"""
        crossover_point = np.random.randint(0, len(parent1))
        child = np.concatenate([parent1[:crossover_point], parent2[crossover_point:]])
        return child

    def _mutate(self, individual: np.ndarray) -> np.ndarray:
        """Mutate individual"""
        mutated = individual.copy()
        mutation_mask = np.random.rand(len(mutated)) < self.mutation_rate

        # Mutate selected genes
        mutated[mutation_mask] = np.random.uniform(0, 2*np.pi, np.sum(mutation_mask))

        return mutated

    def optimize(self, max_iterations: int = 100) -> Dict:
        """
        Run genetic algorithm optimization.

        Args:
            max_iterations: Number of generations

        Returns:
            Optimization results
        """
        try:
            # Initialize
            population = self._initialize_population()
            num_evaluations = self.population_size

            for generation in range(max_iterations):
                # Evaluate fitness
                fitnesses = np.array([self._evaluate_fitness(phases) for phases in population])
                num_evaluations += len(population)

                # Track best
                best_idx = np.argmax(fitnesses)
                if fitnesses[best_idx] > self.best_snr:
                    self.best_snr = fitnesses[best_idx]
                    self.best_phases = population[best_idx].copy()

                self.optimization_history.append({
                    'generation': generation,
                    'best_snr_dB': 10 * np.log10(self.best_snr) if self.best_snr > 0 else -np.inf,
                    'mean_snr_dB': 10 * np.log10(np.mean(fitnesses)) if np.mean(fitnesses) > 0 else -np.inf
                })

                # Create new population
                new_population = [population[best_idx]]  # Elitism

                while len(new_population) < self.population_size:
                    parent1, parent2 = self._select_parents(population, fitnesses)
                    child = self._crossover(parent1, parent2)
                    child = self._mutate(child)
                    new_population.append(child)

                population = np.array(new_population)

                if (generation + 1) % 10 == 0:
                    logger.info(f"GA Gen {generation+1}: Best SNR = {10*np.log10(self.best_snr):.2f} dB")

        except Exception as e:
            logger.error(f"GA optimization failed: {e}")
            return {'status': 'failed', 'error': str(e)}

        # Apply best phases
        self.ris.current_phases = self.best_phases
        self.ris.quantize_phases()

        return {
            'status': 'success',
            'generations': max_iterations,
            'best_snr_dB': 10 * np.log10(self.best_snr) if self.best_snr > 0 else -np.inf,
            'num_evaluations': num_evaluations,
            'history': self.optimization_history
        }


class SimulatedAnnealingOptimizer(PhaseOptimizer):
    """Simulated annealing for phase optimization"""

    def __init__(
        self,
        ris_node,
        snr_function: Callable,
        initial_temperature: float = 100.0,
        cooling_rate: float = 0.95
    ):
        """
        Initialize SA optimizer.

        Args:
            ris_node: RIS node instance
            snr_function: SNR function
            initial_temperature: Initial temperature
            cooling_rate: Temperature reduction per iteration
        """
        super().__init__(ris_node, snr_function)
        self.temperature = initial_temperature
        self.cooling_rate = cooling_rate

    def optimize(self, max_iterations: int = 100) -> Dict:
        """
        Run simulated annealing optimization.

        Args:
            max_iterations: Number of iterations

        Returns:
            Optimization results
        """
        try:
            # Start from current phases
            current_phases = self.ris.current_phases.copy()
            current_snr = self.snr_function(current_phases)
            num_evaluations = 1

            self.best_snr = current_snr
            self.best_phases = current_phases.copy()

            for iteration in range(max_iterations):
                # Generate neighbor solution (random perturbation)
                neighbor_phases = current_phases + np.random.normal(0, 0.1, len(current_phases))
                neighbor_phases = neighbor_phases % (2 * np.pi)

                neighbor_snr = self.snr_function(neighbor_phases)
                num_evaluations += 1

                # Acceptance criterion
                delta = neighbor_snr - current_snr
                if delta > 0 or np.random.rand() < np.exp(delta / self.temperature):
                    current_phases = neighbor_phases
                    current_snr = neighbor_snr

                # Update best
                if current_snr > self.best_snr:
                    self.best_snr = current_snr
                    self.best_phases = current_phases.copy()

                # Cool down
                self.temperature *= self.cooling_rate

                self.optimization_history.append({
                    'iteration': iteration,
                    'current_snr_dB': 10 * np.log10(current_snr) if current_snr > 0 else -np.inf,
                    'best_snr_dB': 10 * np.log10(self.best_snr) if self.best_snr > 0 else -np.inf,
                    'temperature': self.temperature
                })

        except Exception as e:
            logger.error(f"SA optimization failed: {e}")
            return {'status': 'failed', 'error': str(e)}

        # Apply best phases
        self.ris.current_phases = self.best_phases
        self.ris.quantize_phases()

        return {
            'status': 'success',
            'iterations': max_iterations,
            'best_snr_dB': 10 * np.log10(self.best_snr) if self.best_snr > 0 else -np.inf,
            'num_evaluations': num_evaluations,
            'history': self.optimization_history
        }
