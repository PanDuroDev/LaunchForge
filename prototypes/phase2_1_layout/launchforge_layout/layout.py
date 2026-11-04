"""Small, schema-free layout reference implementation.

All geometry is expressed in logical UI units. DPI conversion belongs to the
renderer/presentation boundary and is intentionally outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import AbstractSet, Sequence

_EPSILON = 1e-9


class Axis(str, Enum):
    """Main layout axis for stack placement."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class SizeMode(str, Enum):
    """Supported dimension sizing strategies."""
    FIXED = "fixed"
    FIT = "fit"
    FILL = "fill"


class Alignment(str, Enum):
    """Logical alignment relative to a component's parent."""
    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"


class MainDistribution(str, Enum):
    """Distribution of unused space along a stack's main axis."""
    START = "start"
    CENTER = "center"
    END = "end"
    SPACE_BETWEEN = "space-between"


class Direction(str, Enum):
    """Inline writing direction used by direction-aware layout."""
    LTR = "ltr"
    RTL = "rtl"


def _finite_non_negative(name: str, value: float) -> None:
    """Reject dimensions and weights that are negative or non-finite."""
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")


def _finite(name: str, value: float) -> None:
    """Reject coordinates that cannot be represented as finite values."""
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class Rect:
    """Immutable rectangle measured in logical UI units."""
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        """Validate all rectangle coordinates and dimensions."""
        _finite("x", self.x)
        _finite("y", self.y)
        _finite_non_negative("width", self.width)
        _finite_non_negative("height", self.height)

    @property
    def right(self) -> float:
        """Return the right edge of this rectangle."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Return the bottom edge of this rectangle."""
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class Insets:
    """Immutable padding values for the four rectangle edges."""
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    def __post_init__(self) -> None:
        """Reject negative or non-finite padding values."""
        for name in ("top", "right", "bottom", "left"):
            _finite_non_negative(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AxisSpec:
    """A dimension request with optional minimum and maximum bounds.

    For FILL, value is the positive flex weight. For FIXED it is the requested
    logical size. FIT measures the child's intrinsic size.
    """

    mode: SizeMode
    value: float = 0.0
    minimum: float = 0.0
    maximum: float | None = None

    def __post_init__(self) -> None:
        """Validate mode, sizing value, and min/max bounds."""
        if not isinstance(self.mode, SizeMode):
            raise ValueError("mode must be a supported SizeMode")
        _finite_non_negative("value", self.value)
        _finite_non_negative("minimum", self.minimum)
        if self.maximum is not None:
            _finite_non_negative("maximum", self.maximum)
            if self.maximum < self.minimum:
                raise ValueError("maximum must be greater than or equal to minimum")
        if self.mode is SizeMode.FILL and self.value <= 0:
            raise ValueError("fill weight must be greater than zero")

    @classmethod
    def fixed(
        cls, value: float, *, minimum: float = 0.0, maximum: float | None = None
    ) -> "AxisSpec":
        """Create a fixed logical size request."""
        return cls(SizeMode.FIXED, value, minimum, maximum)

    @classmethod
    def fit(
        cls, *, minimum: float = 0.0, maximum: float | None = None
    ) -> "AxisSpec":
        """Create a content-measured size request."""
        return cls(SizeMode.FIT, 0.0, minimum, maximum)

    @classmethod
    def fill(
        cls, weight: float = 1.0, *, minimum: float = 0.0, maximum: float | None = None
    ) -> "AxisSpec":
        """Create a weighted fill request with optional bounds."""
        return cls(SizeMode.FILL, weight, minimum, maximum)


@dataclass(frozen=True, slots=True)
class LayoutChild:
    """A keyed layout item with width, height, and intrinsic measurements."""
    key: str
    width: AxisSpec
    height: AxisSpec
    intrinsic_width: float = 0.0
    intrinsic_height: float = 0.0

    def __post_init__(self) -> None:
        """Validate stable local key, sizing specs, and intrinsic dimensions."""
        if not self.key:
            raise ValueError("child key must not be empty")
        if not isinstance(self.width, AxisSpec) or not isinstance(self.height, AxisSpec):
            raise ValueError("width and height must be AxisSpec instances")
        _finite_non_negative("intrinsic_width", self.intrinsic_width)
        _finite_non_negative("intrinsic_height", self.intrinsic_height)


@dataclass(frozen=True, slots=True)
class OverlayChild(LayoutChild):
    """A child independently aligned within an overlay parent."""
    align_x: Alignment = Alignment.CENTER
    align_y: Alignment = Alignment.CENTER


@dataclass(frozen=True, slots=True)
class PlacedItem:
    """A layout child's key and resolved logical bounds."""
    key: str
    bounds: Rect


@dataclass(frozen=True, slots=True)
class LayoutResult:
    """Resolved child placements and per-axis overflow flags."""
    items: tuple[PlacedItem, ...]
    overflow_x: bool = False
    overflow_y: bool = False

    def by_key(self, key: str) -> Rect:
        """Find the resolved bounds for a child key."""
        for item in self.items:
            if item.key == key:
                return item.bounds
        raise KeyError(key)


def _clamp(value: float, spec: AxisSpec) -> float:
    """Constrain a requested size to the spec's minimum and maximum."""
    value = max(value, spec.minimum)
    if spec.maximum is not None:
        value = min(value, spec.maximum)
    return value


def _natural_size(spec: AxisSpec, intrinsic: float) -> float:
    """Resolve fixed or fit-content sizing before flex allocation."""
    if spec.mode is SizeMode.FIXED:
        requested = spec.value
    elif spec.mode is SizeMode.FIT:
        requested = intrinsic
    else:
        raise ValueError("fill dimensions must be resolved against available space")
    return _clamp(requested, spec)


def _allocate_fill(specs: Sequence[AxisSpec], available: float) -> list[float]:
    """Allocate weighted space using aggregate min/max violation.

    Only the bound family that drives the aggregate violation is frozen in an
    iteration. The remaining active children are then redistributed the
    remaining space by weight. When minimum constraints cannot fit, they are
    preserved and the caller reports overflow.
    """

    _finite_non_negative("available", available)
    allocations = [0.0] * len(specs)
    active = set(range(len(specs)))
    remaining = available

    while active:
        # Normalize by the largest active weight before summing. Every weight
        # is finite and positive, but their raw sum can still overflow to
        # infinity (for example, two weights of 1e308). Normalization keeps
        # the denominator bounded by the number of active children and
        # preserves the intended weighted ratios.
        ordered_active = sorted(active)
        max_weight = max(specs[index].value for index in ordered_active)
        normalized_weights = {
            index: specs[index].value / max_weight
            for index in ordered_active
        }
        total_normalized_weight = sum(normalized_weights.values())
        proposed = {
            index: remaining * normalized_weights[index] / total_normalized_weight
            for index in ordered_active
        }
        min_frozen: dict[int, float] = {}
        max_frozen: dict[int, float] = {}
        for index, share in proposed.items():
            spec = specs[index]
            if share < spec.minimum - _EPSILON:
                min_frozen[index] = spec.minimum
            elif spec.maximum is not None and share > spec.maximum + _EPSILON:
                max_frozen[index] = spec.maximum

        if not min_frozen and not max_frozen:
            for index, share in proposed.items():
                allocations[index] = share
            break

        violation = sum(
            value - proposed[index] for index, value in min_frozen.items()
        ) + sum(
            value - proposed[index] for index, value in max_frozen.items()
        )
        if violation > _EPSILON:
            clamped = min_frozen
        elif violation < -_EPSILON:
            clamped = max_frozen
        else:
            clamped = {**min_frozen, **max_frozen}

        for index, value in clamped.items():
            allocations[index] = value
            active.remove(index)
            remaining -= value

        # A negative remainder is possible only when minimums cannot fit.
        # Preserve those minimums; overflow is reported by layout_stack.
        remaining = max(0.0, remaining)

    return allocations


def _inner_rect(bounds: Rect, padding: Insets) -> Rect:
    """Return the parent content box after applying padding."""
    return Rect(
        bounds.x + padding.left,
        bounds.y + padding.top,
        max(0.0, bounds.width - padding.left - padding.right),
        max(0.0, bounds.height - padding.top - padding.bottom),
    )


def _cross_position(
    inner: Rect,
    size: float,
    *,
    axis: Axis,
    alignment: Alignment,
    direction: Direction,
) -> tuple[float, float]:
    """Resolve cross-axis origin while respecting logical start in RTL."""
    if axis is Axis.HORIZONTAL:
        origin, available = inner.y, inner.height
        start_at_end = False
    else:
        origin, available = inner.x, inner.width
        start_at_end = direction is Direction.RTL

    if alignment is Alignment.CENTER:
        offset = (available - size) / 2.0
    elif alignment is Alignment.END:
        offset = 0.0 if start_at_end else available - size
    else:  # START and STRETCH use the logical start edge.
        offset = available - size if start_at_end else 0.0
    return origin + offset, size


def layout_stack(
    bounds: Rect,
    children: Sequence[LayoutChild],
    *,
    axis: Axis,
    padding: Insets = Insets(),
    gap: float = 0.0,
    justify: MainDistribution = MainDistribution.START,
    align_items: Alignment = Alignment.START,
    direction: Direction = Direction.LTR,
) -> LayoutResult:
    """Resolve a stack into logical rectangles without renderer-specific units."""

    _finite_non_negative("gap", gap)
    if not isinstance(axis, Axis):
        raise ValueError("axis must be horizontal or vertical")
    if not isinstance(direction, Direction):
        raise ValueError("direction must be LTR or RTL")
    if not isinstance(justify, MainDistribution) or not isinstance(align_items, Alignment):
        raise ValueError("unsupported stack alignment or distribution")
    keys = [child.key for child in children]
    if len(keys) != len(set(keys)):
        raise ValueError("child keys must be unique within a layout")

    inner = _inner_rect(bounds, padding)
    if axis is Axis.HORIZONTAL:
        available_main, available_cross = inner.width, inner.height
        main_specs = [child.width for child in children]
        cross_specs = [child.height for child in children]
        main_intrinsic = [child.intrinsic_width for child in children]
        cross_intrinsic = [child.intrinsic_height for child in children]
    else:
        available_main, available_cross = inner.height, inner.width
        main_specs = [child.height for child in children]
        cross_specs = [child.width for child in children]
        main_intrinsic = [child.intrinsic_height for child in children]
        cross_intrinsic = [child.intrinsic_width for child in children]

    natural_sizes = [
        _natural_size(spec, intrinsic) if spec.mode is not SizeMode.FILL else None
        for spec, intrinsic in zip(main_specs, main_intrinsic)
    ]
    fill_indices = [i for i, spec in enumerate(main_specs) if spec.mode is SizeMode.FILL]
    base_gaps = gap * max(0, len(children) - 1)
    fixed_total = sum(size for size in natural_sizes if size is not None)
    fill_available = max(0.0, available_main - fixed_total - base_gaps)
    fill_sizes = _allocate_fill([main_specs[i] for i in fill_indices], fill_available)

    main_sizes = list(natural_sizes)
    for index, size in zip(fill_indices, fill_sizes):
        main_sizes[index] = size
    resolved_main = [float(size) for size in main_sizes]

    used_main = sum(resolved_main) + base_gaps
    leftover = max(0.0, available_main - used_main)
    leading = 0.0
    extra_gap = 0.0
    if justify is MainDistribution.CENTER:
        leading = leftover / 2.0
    elif justify is MainDistribution.END:
        leading = leftover
    elif justify is MainDistribution.SPACE_BETWEEN and len(children) > 1:
        extra_gap = leftover / (len(children) - 1)

    rtl_main = axis is Axis.HORIZONTAL and direction is Direction.RTL
    if rtl_main:
        cursor = inner.right - leading
    elif axis is Axis.VERTICAL:
        cursor = inner.y + leading
    else:
        cursor = inner.x + leading

    items: list[PlacedItem] = []
    cross_overflow = False
    for child, main_size, cross_spec, intrinsic_cross in zip(
        children, resolved_main, cross_specs, cross_intrinsic
    ):
        if cross_spec.mode is SizeMode.FILL or align_items is Alignment.STRETCH:
            cross_size = _clamp(available_cross, cross_spec)
        else:
            cross_size = _natural_size(cross_spec, intrinsic_cross)
        # Keep the requested alignment when a FILL child is capped by max.
        cross_alignment = align_items

        cross_origin, final_cross_size = _cross_position(
            inner,
            cross_size,
            axis=axis,
            alignment=cross_alignment,
            direction=direction,
        )
        cross_overflow = cross_overflow or final_cross_size > available_cross + _EPSILON

        if axis is Axis.HORIZONTAL:
            if rtl_main:
                x = cursor - main_size
                cursor = x - gap - extra_gap
            else:
                x = cursor
                cursor = x + main_size + gap + extra_gap
            rect = Rect(x, cross_origin, main_size, final_cross_size)
        else:
            y = cursor
            cursor = y + main_size + gap + extra_gap
            rect = Rect(cross_origin, y, final_cross_size, main_size)
        items.append(PlacedItem(child.key, rect))

    main_overflow = used_main > available_main + _EPSILON
    if axis is Axis.HORIZONTAL:
        return LayoutResult(tuple(items), overflow_x=main_overflow, overflow_y=cross_overflow)
    return LayoutResult(tuple(items), overflow_x=cross_overflow, overflow_y=main_overflow)


def _overlay_axis(
    origin: float,
    available: float,
    spec: AxisSpec,
    intrinsic: float,
    alignment: Alignment,
    *,
    reverse_start: bool,
) -> tuple[float, float]:
    """Resolve one overlay dimension and its aligned origin."""
    if spec.mode is SizeMode.FILL or alignment is Alignment.STRETCH:
        size = _clamp(available, spec)
    else:
        size = _natural_size(spec, intrinsic)

    if alignment is Alignment.CENTER:
        offset = (available - size) / 2.0
    elif alignment is Alignment.END:
        offset = 0.0 if reverse_start else available - size
    else:
        offset = available - size if reverse_start else 0.0
    return origin + offset, size


def layout_overlay(
    bounds: Rect,
    children: Sequence[OverlayChild],
    *,
    padding: Insets = Insets(),
    direction: Direction = Direction.LTR,
) -> LayoutResult:
    """Place each child independently inside the same padded overlay bounds."""

    if not isinstance(direction, Direction):
        raise ValueError("direction must be LTR or RTL")
    keys = [child.key for child in children]
    if len(keys) != len(set(keys)):
        raise ValueError("child keys must be unique within a layout")
    if any(not isinstance(child.align_x, Alignment) or not isinstance(child.align_y, Alignment) for child in children):
        raise ValueError("overlay alignment must be supported Alignment values")

    inner = _inner_rect(bounds, padding)
    items: list[PlacedItem] = []
    overflow_x = False
    overflow_y = False
    for child in children:
        x, width = _overlay_axis(
            inner.x, inner.width, child.width, child.intrinsic_width,
            child.align_x, reverse_start=direction is Direction.RTL,
        )
        y, height = _overlay_axis(
            inner.y, inner.height, child.height, child.intrinsic_height,
            child.align_y, reverse_start=False,
        )
        overflow_x = overflow_x or x < inner.x - _EPSILON or x + width > inner.right + _EPSILON
        overflow_y = overflow_y or y < inner.y - _EPSILON or y + height > inner.bottom + _EPSILON
        items.append(PlacedItem(child.key, Rect(x, y, width, height)))
    return LayoutResult(tuple(items), overflow_x, overflow_y)

def hit_test(
    result: LayoutResult,
    x: float,
    y: float,
    *,
    interactive_keys: AbstractSet[str],
) -> str | None:
    """Return the topmost interactive child containing a logical point.

    Layout results retain logical sibling order, with later siblings painted
    above earlier siblings. Hit testing therefore walks placements in reverse
    order and skips keys that are not interactive. Bounds use half-open edges
    [left, right) and [top, bottom) so adjacent rectangles do not both claim
    their shared boundary.
    """

    _finite("x", x)
    _finite("y", y)
    for item in reversed(result.items):
        if item.key not in interactive_keys:
            continue
        bounds = item.bounds
        if bounds.x <= x < bounds.right and bounds.y <= y < bounds.bottom:
            return item.key
    return None
