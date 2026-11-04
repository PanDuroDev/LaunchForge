"""Behavioral tests for the isolated Phase 2.1 layout prototype."""

import unittest

from launchforge_layout import (
    Alignment,
    Axis,
    AxisSpec,
    Direction,
    Insets,
    LayoutChild,
    MainDistribution,
    OverlayChild,
    Rect,
    layout_overlay,
    layout_stack,
)


class StackLayoutTests(unittest.TestCase):
    """Regression tests for stack sizing, alignment, direction, and overflow."""

    def test_vertical_stack_applies_padding_gap_and_fill_cross_axis(self):
        """Verify vertical placement applies padding, gaps, and cross-axis fill."""
        result = layout_stack(
            Rect(0, 0, 300, 200),
            [
                LayoutChild("title", AxisSpec.fill(), AxisSpec.fixed(20)),
                LayoutChild("play", AxisSpec.fill(), AxisSpec.fixed(40)),
            ],
            axis=Axis.VERTICAL,
            padding=Insets(10, 10, 10, 10),
            gap=8,
        )
        self.assertEqual(result.by_key("title"), Rect(10, 10, 280, 20))
        self.assertEqual(result.by_key("play"), Rect(10, 38, 280, 40))
        self.assertFalse(result.overflow_x)
        self.assertFalse(result.overflow_y)

    def test_fill_weights_distribute_remaining_main_axis_space(self):
        """Verify fill children receive remaining space in proportion to their weights."""
        result = layout_stack(
            Rect(0, 0, 320, 100),
            [
                LayoutChild("icon", AxisSpec.fixed(80), AxisSpec.fill()),
                LayoutChild("primary", AxisSpec.fill(1), AxisSpec.fill()),
                LayoutChild("secondary", AxisSpec.fill(2), AxisSpec.fill()),
            ],
            axis=Axis.HORIZONTAL,
            padding=Insets(left=16, right=16),
            gap=8,
            align_items=Alignment.STRETCH,
        )
        self.assertAlmostEqual(result.by_key("icon").x, 16)
        self.assertAlmostEqual(result.by_key("icon").width, 80)
        self.assertAlmostEqual(result.by_key("primary").x, 104)
        self.assertAlmostEqual(result.by_key("primary").width, 64)
        self.assertAlmostEqual(result.by_key("secondary").x, 176)
        self.assertAlmostEqual(result.by_key("secondary").width, 128)

    def test_mixed_fill_minimum_and_maximum_redistribute_correctly(self):
        """Verify mixed minimum and maximum bounds redistribute space without false overflow."""
        result = layout_stack(
            Rect(0, 0, 100, 40),
            [
                LayoutChild("minimum", AxisSpec.fill(minimum=80), AxisSpec.fill()),
                LayoutChild("maximum", AxisSpec.fill(maximum=30), AxisSpec.fill()),
                LayoutChild("remaining", AxisSpec.fill(), AxisSpec.fill()),
            ],
            axis=Axis.HORIZONTAL,
        )
        self.assertEqual(result.by_key("minimum").width, 80)
        self.assertEqual(result.by_key("maximum").width, 10)
        self.assertEqual(result.by_key("remaining").width, 10)
        self.assertFalse(result.overflow_x)

    def test_fill_maximum_releases_space_to_other_fill_children(self):
        """Verify a capped fill child releases unused space to its siblings."""
        result = layout_stack(
            Rect(0, 0, 300, 50),
            [
                LayoutChild("capped", AxisSpec.fill(maximum=80), AxisSpec.fill()),
                LayoutChild("remaining", AxisSpec.fill(), AxisSpec.fill()),
            ],
            axis=Axis.HORIZONTAL,
        )
        self.assertEqual(result.by_key("capped").width, 80)
        self.assertEqual(result.by_key("remaining").width, 220)

    def test_minimum_fill_constraints_report_overflow(self):
        """Verify unsatisfied minimum sizes are preserved and reported as overflow."""
        result = layout_stack(
            Rect(0, 0, 100, 40),
            [
                LayoutChild("a", AxisSpec.fill(minimum=70), AxisSpec.fill()),
                LayoutChild("b", AxisSpec.fill(minimum=70), AxisSpec.fill()),
            ],
            axis=Axis.HORIZONTAL,
        )
        self.assertEqual(result.by_key("a").width, 70)
        self.assertEqual(result.by_key("b").width, 70)
        self.assertTrue(result.overflow_x)

    def test_center_and_end_distribution_position_fixed_children(self):
        """Verify center and end distribution position fixed children correctly."""
        children = [
            LayoutChild("a", AxisSpec.fixed(50), AxisSpec.fixed(20)),
            LayoutChild("b", AxisSpec.fixed(50), AxisSpec.fixed(20)),
        ]
        centered = layout_stack(
            Rect(0, 0, 300, 40), children, axis=Axis.HORIZONTAL,
            gap=10, justify=MainDistribution.CENTER,
        )
        ended = layout_stack(
            Rect(0, 0, 300, 40), children, axis=Axis.HORIZONTAL,
            gap=10, justify=MainDistribution.END,
        )
        self.assertEqual(centered.by_key("a").x, 95)
        self.assertEqual(ended.by_key("a").x, 190)

    def test_space_between_distributes_only_remaining_space(self):
        """Verify space-between adds only the unused space between children."""
        result = layout_stack(
            Rect(0, 0, 300, 40),
            [
                LayoutChild("a", AxisSpec.fixed(50), AxisSpec.fixed(20)),
                LayoutChild("b", AxisSpec.fixed(50), AxisSpec.fixed(20)),
                LayoutChild("c", AxisSpec.fixed(50), AxisSpec.fixed(20)),
            ],
            axis=Axis.HORIZONTAL,
            gap=10,
            justify=MainDistribution.SPACE_BETWEEN,
        )
        self.assertEqual(result.by_key("a").x, 0)
        self.assertEqual(result.by_key("b").x, 125)
        self.assertEqual(result.by_key("c").x, 250)

    def test_horizontal_rtl_keeps_logical_order_and_starts_at_right(self):
        """Verify RTL keeps logical child order while placing the first child on the right."""
        result = layout_stack(
            Rect(0, 0, 300, 40),
            [
                LayoutChild("first", AxisSpec.fixed(50), AxisSpec.fixed(20)),
                LayoutChild("second", AxisSpec.fixed(50), AxisSpec.fixed(20)),
            ],
            axis=Axis.HORIZONTAL,
            gap=10,
            direction=Direction.RTL,
        )
        self.assertEqual(result.by_key("first").x, 250)
        self.assertEqual(result.by_key("second").x, 190)

    def test_vertical_stack_cross_start_respects_rtl(self):
        """Verify vertical-stack cross-axis start follows RTL direction."""
        result = layout_stack(
            Rect(0, 0, 200, 100),
            [LayoutChild("child", AxisSpec.fixed(50), AxisSpec.fixed(20))],
            axis=Axis.VERTICAL,
            direction=Direction.RTL,
            align_items=Alignment.START,
        )
        self.assertEqual(result.by_key("child").x, 150)

    def test_fit_content_uses_intrinsic_size_and_constraints(self):
        """Verify fit sizing uses intrinsic dimensions and applies size constraints."""
        result = layout_stack(
            Rect(0, 0, 300, 100),
            [LayoutChild("label", AxisSpec.fit(maximum=90), AxisSpec.fit(minimum=24), 120, 18)],
            axis=Axis.HORIZONTAL,
        )
        self.assertEqual(result.by_key("label"), Rect(0, 0, 90, 24))

    def test_overflow_is_reported_for_fixed_children_that_do_not_fit(self):
        """Verify fixed children exceeding the main axis trigger overflow."""
        result = layout_stack(
            Rect(0, 0, 150, 40),
            [
                LayoutChild("a", AxisSpec.fixed(100), AxisSpec.fixed(20)),
                LayoutChild("b", AxisSpec.fixed(100), AxisSpec.fixed(20)),
            ],
            axis=Axis.HORIZONTAL,
            gap=8,
        )
        self.assertTrue(result.overflow_x)
        self.assertEqual(result.by_key("b").x, 108)

    def test_fill_layout_adapts_to_documented_desktop_viewports(self):
        """Verify a fill layout adapts across the documented desktop viewport sizes."""
        for width, height in ((960, 600), (1280, 720), (1600, 900)):
            with self.subTest(viewport=(width, height)):
                result = layout_stack(
                    Rect(0, 0, width, height),
                    [
                        LayoutChild("sidebar", AxisSpec.fixed(120), AxisSpec.fill()),
                        LayoutChild("content", AxisSpec.fill(), AxisSpec.fill()),
                    ],
                    axis=Axis.HORIZONTAL,
                    padding=Insets(16, 16, 16, 16),
                    gap=8,
                )
                sidebar = result.by_key("sidebar")
                content = result.by_key("content")
                self.assertEqual(sidebar.x, 16)
                self.assertEqual(sidebar.width, 120)
                self.assertEqual(content.x, 144)
                self.assertEqual(content.right, width - 16)
                self.assertEqual(content.height, height - 32)
                self.assertFalse(result.overflow_x)
                self.assertFalse(result.overflow_y)

    def test_layout_is_deterministic_for_identical_logical_inputs(self):
        """Verify identical logical inputs produce identical layout results."""
        args = (
            Rect(3, 7, 333, 211),
            [
                LayoutChild("a", AxisSpec.fill(2), AxisSpec.fit(), 40, 17),
                LayoutChild("b", AxisSpec.fill(1), AxisSpec.fixed(30)),
            ],
        )
        first = layout_stack(*args, axis=Axis.HORIZONTAL, gap=7.5)
        second = layout_stack(*args, axis=Axis.HORIZONTAL, gap=7.5)
        self.assertEqual(first, second)

    def test_duplicate_child_keys_are_rejected(self):
        """Verify duplicate child keys are rejected."""
        child = LayoutChild("same", AxisSpec.fill(), AxisSpec.fill())
        with self.assertRaisesRegex(ValueError, "unique"):
            layout_stack(Rect(0, 0, 10, 10), [child, child], axis=Axis.HORIZONTAL)

    def test_negative_gap_is_rejected(self):
        """Verify negative stack gaps are rejected."""
        with self.assertRaisesRegex(ValueError, "gap"):
            layout_stack(
                Rect(0, 0, 10, 10), [], axis=Axis.HORIZONTAL, gap=-1
            )

    def test_fill_allocation_does_not_overflow_when_weights_are_large(self):
        """Verify finite large weights retain their ratios without sum overflow."""
        result = layout_stack(
            Rect(0, 0, 300, 40),
            [
                LayoutChild("a", AxisSpec.fill(1e308), AxisSpec.fixed(20)),
                LayoutChild("b", AxisSpec.fill(1e308), AxisSpec.fixed(20)),
            ],
            axis=Axis.HORIZONTAL,
        )
        self.assertAlmostEqual(result.by_key("a").width, 150)
        self.assertAlmostEqual(result.by_key("b").width, 150)
        self.assertEqual(result.by_key("b").right, 300)
        self.assertFalse(result.overflow_x)

    def test_fill_allocation_preserves_ratios_for_large_weights(self):
        """Verify normalization preserves unequal large finite weight ratios."""
        result = layout_stack(
            Rect(0, 0, 100, 40),
            [
                LayoutChild("heavy", AxisSpec.fill(1e308), AxisSpec.fixed(20)),
                LayoutChild("light", AxisSpec.fill(1e307), AxisSpec.fixed(20)),
            ],
            axis=Axis.HORIZONTAL,
        )
        self.assertAlmostEqual(result.by_key("heavy").width, 100 / 1.1)
        self.assertAlmostEqual(result.by_key("light").width, 10 / 1.1)
        self.assertAlmostEqual(result.by_key("light").right, 100)

    def test_capped_fill_child_honors_center_and_end_cross_alignment(self):
        """Verify capped cross-axis fill honors center and end alignment."""
        for alignment, expected_y in (
            (Alignment.CENTER, 35),
            (Alignment.END, 70),
        ):
            with self.subTest(alignment=alignment):
                result = layout_stack(
                    Rect(0, 0, 200, 100),
                    [LayoutChild(
                        "child",
                        AxisSpec.fixed(40),
                        AxisSpec.fill(maximum=30),
                    )],
                    axis=Axis.HORIZONTAL,
                    align_items=alignment,
                )
                self.assertEqual(result.by_key("child").height, 30)
                self.assertEqual(result.by_key("child").y, expected_y)

    def test_stretch_respects_cross_axis_maximum(self):
        """Verify stretch alignment respects the cross-axis maximum."""
        result = layout_stack(
            Rect(0, 0, 200, 100),
            [LayoutChild("child", AxisSpec.fixed(40), AxisSpec.fill(maximum=30))],
            axis=Axis.HORIZONTAL,
            align_items=Alignment.STRETCH,
        )
        self.assertEqual(result.by_key("child").height, 30)

    def test_cross_axis_overflow_is_reported_on_only_the_cross_axis(self):
        """Verify cross-axis overflow does not set the main-axis overflow flag."""
        result = layout_stack(
            Rect(0, 0, 100, 30),
            [LayoutChild("child", AxisSpec.fixed(20), AxisSpec.fixed(50))],
            axis=Axis.HORIZONTAL,
        )
        self.assertFalse(result.overflow_x)
        self.assertTrue(result.overflow_y)

    def test_invalid_size_constraints_are_rejected(self):
        """Verify invalid min/max bounds and non-positive fill weights are rejected."""
        with self.assertRaisesRegex(ValueError, "maximum"):
            AxisSpec.fixed(10, minimum=20, maximum=15)
        with self.assertRaisesRegex(ValueError, "weight"):
            AxisSpec.fill(0)


class OverlayLayoutTests(unittest.TestCase):
    """Regression tests for overlay sizing, placement, and overflow."""

    def test_overlay_center_and_directional_edges(self):
        """Verify overlay centering and directional edge alignment."""
        result = layout_overlay(
            Rect(0, 0, 200, 100),
            [
                OverlayChild("center", AxisSpec.fixed(40), AxisSpec.fixed(20)),
                OverlayChild(
                    "badge", AxisSpec.fixed(30), AxisSpec.fixed(10),
                    align_x=Alignment.START, align_y=Alignment.END,
                ),
            ],
            direction=Direction.RTL,
        )
        self.assertEqual(result.by_key("center"), Rect(80, 40, 40, 20))
        self.assertEqual(result.by_key("badge"), Rect(170, 90, 30, 10))

    def test_overlay_fill_covers_inner_bounds_and_padding(self):
        """Verify overlay fill covers the padded content bounds."""
        result = layout_overlay(
            Rect(0, 0, 100, 80),
            [OverlayChild("background", AxisSpec.fill(), AxisSpec.fill())],
            padding=Insets(5, 10, 15, 20),
        )
        self.assertEqual(result.by_key("background"), Rect(20, 5, 70, 60))

    def test_overlay_reports_overflow(self):
        """Verify overlay children outside the content bounds trigger overflow."""
        result = layout_overlay(
            Rect(0, 0, 40, 40),
            [OverlayChild("large", AxisSpec.fixed(60), AxisSpec.fixed(60))],
        )
        self.assertTrue(result.overflow_x)
        self.assertTrue(result.overflow_y)


if __name__ == "__main__":
    unittest.main()
