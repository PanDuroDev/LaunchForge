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
    def test_vertical_stack_applies_padding_gap_and_fill_cross_axis(self):
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

    def test_fill_maximum_releases_space_to_other_fill_children(self):
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
        result = layout_stack(
            Rect(0, 0, 200, 100),
            [LayoutChild("child", AxisSpec.fixed(50), AxisSpec.fixed(20))],
            axis=Axis.VERTICAL,
            direction=Direction.RTL,
            align_items=Alignment.START,
        )
        self.assertEqual(result.by_key("child").x, 150)

    def test_fit_content_uses_intrinsic_size_and_constraints(self):
        result = layout_stack(
            Rect(0, 0, 300, 100),
            [LayoutChild("label", AxisSpec.fit(maximum=90), AxisSpec.fit(minimum=24), 120, 18)],
            axis=Axis.HORIZONTAL,
        )
        self.assertEqual(result.by_key("label"), Rect(0, 0, 90, 24))

    def test_overflow_is_reported_for_fixed_children_that_do_not_fit(self):
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
        child = LayoutChild("same", AxisSpec.fill(), AxisSpec.fill())
        with self.assertRaisesRegex(ValueError, "unique"):
            layout_stack(Rect(0, 0, 10, 10), [child, child], axis=Axis.HORIZONTAL)

    def test_negative_gap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "gap"):
            layout_stack(
                Rect(0, 0, 10, 10), [], axis=Axis.HORIZONTAL, gap=-1
            )

    def test_stretch_respects_cross_axis_maximum(self):
        result = layout_stack(
            Rect(0, 0, 200, 100),
            [LayoutChild("child", AxisSpec.fixed(40), AxisSpec.fill(maximum=30))],
            axis=Axis.HORIZONTAL,
            align_items=Alignment.STRETCH,
        )
        self.assertEqual(result.by_key("child").height, 30)

    def test_cross_axis_overflow_is_reported_on_only_the_cross_axis(self):
        result = layout_stack(
            Rect(0, 0, 100, 30),
            [LayoutChild("child", AxisSpec.fixed(20), AxisSpec.fixed(50))],
            axis=Axis.HORIZONTAL,
        )
        self.assertFalse(result.overflow_x)
        self.assertTrue(result.overflow_y)

    def test_invalid_size_constraints_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "maximum"):
            AxisSpec.fixed(10, minimum=20, maximum=15)
        with self.assertRaisesRegex(ValueError, "weight"):
            AxisSpec.fill(0)


class OverlayLayoutTests(unittest.TestCase):
    def test_overlay_center_and_directional_edges(self):
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
        result = layout_overlay(
            Rect(0, 0, 100, 80),
            [OverlayChild("background", AxisSpec.fill(), AxisSpec.fill())],
            padding=Insets(5, 10, 15, 20),
        )
        self.assertEqual(result.by_key("background"), Rect(20, 5, 70, 60))

    def test_overlay_reports_overflow(self):
        result = layout_overlay(
            Rect(0, 0, 40, 40),
            [OverlayChild("large", AxisSpec.fixed(60), AxisSpec.fixed(60))],
        )
        self.assertTrue(result.overflow_x)
        self.assertTrue(result.overflow_y)


if __name__ == "__main__":
    unittest.main()
