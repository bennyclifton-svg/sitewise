"""Regression cases for source-glow artifacts in the cadastral reconstruction."""

import importlib.util
import math
from pathlib import Path
import unittest
import numpy as np


SPEC = importlib.util.spec_from_file_location(
    "cadastral", Path(__file__).with_name("extract-cadastral-vectors.py")
)
cadastral = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cadastral)


class CadastralGeometryTests(unittest.TestCase):
    def test_glowing_triangle_junction_becomes_one_crisp_shared_vertex(self):
        a, b, c = (998, 2000), (1000, 1998), (1002, 2001)
        lines = [
            [(900, 2000), (980, 2000), (990, 2001), a],
            [(1100, 2000), (1020, 2000), (1010, 1999), c],
            [(1000, 1900), (1000, 1980), (1001, 1990), b],
            [a, b], [b, c], [c, a],
        ]
        cleaned, _ = cadastral.reconstruct_boundaries(lines)
        self.assertEqual(len(cleaned), 3)
        self.assertTrue(all(len(line) == 2 for line in cleaned))
        junctions = [point for line in cleaned for point in (line[0], line[-1])
                     if math.dist(point, (1000, 2000)) < 10]
        self.assertEqual(len(junctions), 3)
        self.assertTrue(all(point == junctions[0] for point in junctions))
        self.assertLess(math.dist(junctions[0], (1000, 2000)), 1)

    def test_small_closed_glow_loop_is_removed(self):
        lines = [[(1000, 2000), (1008, 2000), (1008, 2008), (1000, 2008), (1000, 2000)],
                 [(1000, 2000), (1200, 2000)]]
        cleaned, _ = cadastral.reconstruct_boundaries(lines)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(cleaned[0]), 2)

    def test_source_wave_on_an_otherwise_straight_parcel_is_regularized(self):
        line = [(1000 + x, 2000 + 6 * math.sin(x * math.pi / 200)) for x in range(0, 201, 4)]
        cleaned, _ = cadastral.reconstruct_boundaries([line])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(cleaned[0]), 2)

    def test_legitimate_road_curve_remains_curved(self):
        line = [(1000 + 200 * math.cos(t * math.pi / 60),
                 2000 + 200 * math.sin(t * math.pi / 60)) for t in range(31)]
        cleaned, _ = cadastral.reconstruct_boundaries([line])
        self.assertEqual(len(cleaned), 1)
        self.assertGreater(len(cleaned[0]), 5)
        self.assertLess(math.dist(cleaned[0][0], line[0]), 8)
        self.assertLess(math.dist(cleaned[0][-1], line[-1]), 8)

    def test_nearby_separate_parcels_are_not_welded(self):
        lines = [[(1000, 2000), (1200, 2000)], [(1000, 2030), (1200, 2030)]]
        cleaned, _ = cadastral.reconstruct_boundaries(lines)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len({point for line in cleaned for point in line}), 4)

    def test_legitimate_right_angle_is_not_replaced_by_diagonal(self):
        line = [(1000, 2000), (1100, 2000), (1100, 2100)]
        cleaned, _ = cadastral.reconstruct_boundaries([line])
        self.assertGreaterEqual(len(cleaned[0]), 3)
        self.assertTrue(any(math.dist(point, (1100, 2000)) < 4 for point in cleaned[0]))

    def test_boundary_clipping_preserves_straight_run_and_valid_bounds(self):
        lines = [[(-20, 10), (120, 80)], [(20, 20), (30, 30)]]
        clipped = cadastral.clip_to_bounds(lines, 100, 100)
        self.assertEqual(clipped, [[(0, 20), (100, 70)], [(20, 20), (30, 30)]])

    def test_entirely_outside_run_is_removed(self):
        self.assertEqual(cadastral.clip_to_bounds([[(-20, 10), (-10, 80)]], 100, 100), [])

    def test_shared_reversed_segment_is_emitted_once(self):
        lines = [[(0, 0), (1, 0), (1, 1)], [(1, 0), (0, 0)], [(1, 1), (2, 1)]]
        deduplicated = cadastral.deduplicate_segments(lines)
        self.assertEqual(sum(len(line) - 1 for line in deduplicated), 3)

    def test_fitted_join_does_not_return_backwards_to_old_curve_samples(self):
        samples = np.array([(445.02, 2468), (433.21, 2468.49), (421.45, 2478.86)])
        fitted = cadastral.trim_fitted_curve(samples, (427.96, 2471.73), (417.23, 2477.24), 9)
        self.assertTrue(all(point[0] <= 427.96 for point in fitted))
        self.assertTrue(all(point[0] >= 417.23 for point in fitted))

    def test_long_thin_glow_face_becomes_one_shared_boundary(self):
        lines = [[(1000, 2000), (1200, 2000), (1200, 2008)],
                 [(1000, 2000), (1000, 2008), (1200, 2008)],
                 [(1000, 2000), (1000, 1800)], [(1200, 2008), (1200, 2200)]]
        cleaned, metrics = cadastral.reconstruct_boundaries(lines)
        self.assertGreater(metrics["collapsedGlowFaces"], 0)
        self.assertEqual(len(cleaned), 3)
        self.assertTrue(all(len(line) == 2 for line in cleaned))

    def test_real_narrow_road_corridor_is_not_collapsed_as_glow(self):
        for width in (12, 30):
            with self.subTest(width=width):
                lines = [[(1000, 2000), (1200, 2000), (1200, 2000 + width)],
                         [(1000, 2000), (1000, 2000 + width), (1200, 2000 + width)],
                         [(1000, 2000), (1000, 1800)], [(1200, 2000 + width), (1200, 2200)]]
                cleaned, metrics = cadastral.reconstruct_boundaries(lines)
                self.assertEqual(metrics["collapsedGlowFaces"], 0)
                self.assertEqual(len(cleaned), 4)
                self.assertTrue(any(len(line) > 2 for line in cleaned))


if __name__ == "__main__":
    unittest.main()
