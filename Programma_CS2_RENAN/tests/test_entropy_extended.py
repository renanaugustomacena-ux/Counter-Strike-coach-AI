"""
Extended tests for entropy_analysis.py — EntropyAnalyzer.

Covers:
  - Non-negativity of position entropy
  - Uniform vs clustered entropy ordering
  - Empty position list edge case
  - Thread safety of shared grid buffer under concurrent access
  - Effectiveness rating upper bound (capped at 1.0)
"""

import pytest

pytestmark = pytest.mark.timeout(5)


class TestPositionEntropyNonnegative:
    """Shannon entropy must never be negative."""

    def test_position_entropy_nonnegative(self):
        """compute_position_entropy() always returns >= 0 for any input."""
        from Programma_CS2_RENAN.backend.analysis.entropy_analysis import EntropyAnalyzer

        analyzer = EntropyAnalyzer(grid_resolution=16)

        cases = [
            # Single point
            [(500.0, 500.0)],
            # Two identical points
            [(100.0, 200.0), (100.0, 200.0)],
            # Collinear points
            [(i * 10.0, 0.0) for i in range(20)],
            # Large spread
            [(i * 1000.0, j * 1000.0) for i in range(5) for j in range(5)],
            # Negative coordinates
            [(-500.0, -300.0), (500.0, 300.0)],
            # Very small deltas (near-identical floating point)
            [(1.0, 1.0), (1.0 + 1e-10, 1.0 + 1e-10)],
        ]

        for positions in cases:
            entropy = analyzer.compute_position_entropy(positions)
            assert entropy >= 0.0, (
                f"Entropy must be non-negative, got {entropy} " f"for {len(positions)} positions"
            )


class TestPositionEntropyUniformVsClustered:
    """Uniform distributions must have higher entropy than clustered ones."""

    def test_position_entropy_uniform_vs_clustered(self):
        """Uniformly distributed positions have higher entropy than tightly clustered ones."""
        from Programma_CS2_RENAN.backend.analysis.entropy_analysis import EntropyAnalyzer

        analyzer = EntropyAnalyzer(grid_resolution=32)

        # Uniform: positions spread across a large area with distinct grid cells
        uniform_positions = [(x * 500.0, y * 500.0) for x in range(8) for y in range(8)]

        # Clustered: all positions within a tiny area (same grid cell)
        clustered_positions = [(100.0 + i * 0.001, 200.0 + i * 0.001) for i in range(64)]

        h_uniform = analyzer.compute_position_entropy(uniform_positions)
        h_clustered = analyzer.compute_position_entropy(clustered_positions)

        assert h_uniform > h_clustered, (
            f"Uniform entropy ({h_uniform:.4f}) must exceed "
            f"clustered entropy ({h_clustered:.4f})"
        )


class TestEntropyEmptyPositions:
    """Empty position list must return 0.0 without raising."""

    def test_entropy_empty_positions(self):
        """Empty position list returns 0.0 as a safe default."""
        from Programma_CS2_RENAN.backend.analysis.entropy_analysis import EntropyAnalyzer

        analyzer = EntropyAnalyzer()
        result = analyzer.compute_position_entropy([])
        assert result == 0.0, f"Expected 0.0 for empty positions, got {result}"


class TestThreadSafetySharedBuffer:
    """Concurrent compute_position_entropy() calls must not corrupt the shared grid buffer."""

    def test_thread_safety_shared_buffer(self):
        """4 concurrent calls using the default grid_resolution share the buffer safely."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from Programma_CS2_RENAN.backend.analysis.entropy_analysis import EntropyAnalyzer

        analyzer = EntropyAnalyzer(grid_resolution=32)

        # Each thread gets distinct positions so we can verify correct results
        position_sets = [
            # Set 0: single cluster -> low entropy
            [(100.0, 100.0)] * 50,
            # Set 1: wide spread -> high entropy
            [(x * 200.0, y * 200.0) for x in range(10) for y in range(10)],
            # Set 2: two clusters
            [(100.0, 100.0)] * 25 + [(3000.0, 3000.0)] * 25,
            # Set 3: diagonal line
            [(i * 100.0, i * 100.0) for i in range(50)],
        ]

        # Compute expected results serially first
        expected = [analyzer.compute_position_entropy(ps) for ps in position_sets]

        # Run concurrently 10 times to stress the lock
        for _ in range(10):
            futures = {}
            with ThreadPoolExecutor(max_workers=4) as pool:
                for idx, ps in enumerate(position_sets):
                    fut = pool.submit(analyzer.compute_position_entropy, ps)
                    futures[fut] = idx

                for fut in as_completed(futures):
                    idx = futures[fut]
                    result = fut.result()
                    assert abs(result - expected[idx]) < 1e-6, (
                        f"Thread-safety violation: set {idx} expected "
                        f"{expected[idx]:.6f}, got {result:.6f}"
                    )


class TestEffectivenessCappedAt1:
    """Effectiveness rating from analyze_utility_throw must never exceed 1.0."""

    def test_effectiveness_capped_at_1(self):
        """Even when entropy delta exceeds max_delta, effectiveness stays <= 1.0."""
        from Programma_CS2_RENAN.backend.analysis.entropy_analysis import EntropyAnalyzer

        analyzer = EntropyAnalyzer(grid_resolution=64)

        # Pre: very high entropy (many spread-out positions)
        pre_positions = [(x * 300.0, y * 300.0) for x in range(20) for y in range(20)]
        # Post: minimal entropy (single point)
        post_positions = [(0.0, 0.0)]

        for utility_type in ["smoke", "flash", "molotov", "he_grenade", "unknown"]:
            impact = analyzer.analyze_utility_throw(pre_positions, post_positions, utility_type)
            assert impact.effectiveness_rating <= 1.0, (
                f"Effectiveness for {utility_type} = " f"{impact.effectiveness_rating}, exceeds 1.0"
            )
            assert impact.effectiveness_rating >= 0.0, (
                f"Effectiveness for {utility_type} = " f"{impact.effectiveness_rating}, is negative"
            )
